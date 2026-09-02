from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import logging
from pathlib import Path, PurePosixPath
import re
import subprocess
from typing import Callable, Iterable

import dnfile

from .windows_input import WindowsInputError, parse_hotkey_chord


SUPPORTED_ARCHIVES = {".zip", ".7z", ".rar"}
DOCUMENT_EXTENSIONS = {".txt", ".md"}
PAYLOAD_EXTENSIONS = {
    ".dll",
    ".json",
    ".cfg",
    ".ini",
    ".xml",
    ".bytes",
    ".bundle",
    ".assets",
    ".dat",
    ".png",
    ".jpg",
    ".jpeg",
}
SOURCE_EXTENSIONS = {".cs", ".csproj", ".sln", ".pdb", ".deps.json"}
FRAMEWORK_MARKERS = {
    "doorstop_config.ini",
    "winhttp.dll",
    "bepinex/core",
    "bepinex/patchers",
    "bepinex/unhollowed",
}
MAX_ARCHIVE_MEMBERS = 512
MAX_PAYLOAD_FILES = 64
MAX_MEMBER_BYTES = 64 * 1024 * 1024
MAX_TOTAL_PAYLOAD_BYTES = 128 * 1024 * 1024
MOD_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")


class ModInspectionError(ValueError):
    pass


@dataclass(frozen=True)
class PackageMember:
    path: str
    size_bytes: int
    is_directory: bool = False

    @property
    def suffix(self) -> str:
        return Path(self.path).suffix.casefold()


@dataclass(frozen=True)
class PayloadFile:
    source_path: str
    target_path: str
    size_bytes: int
    sha256: str


@dataclass(frozen=True)
class ModDraft:
    source: Path
    source_kind: str
    suggested_id: str
    name: str
    version: str
    author: str
    summary: str
    usage_hint: str
    hotkeys: tuple[str, ...]
    panel_hotkey: str | None
    payload: tuple[PayloadFile, ...]
    manifest: dict[str, object] | None
    evidence: tuple[str, ...]
    warnings: tuple[str, ...]


def normalize_member_path(value: str) -> str:
    normalized = value.replace("\\", "/").strip("/")
    if not normalized or "\x00" in normalized:
        raise ModInspectionError("MOD 包含空路径或无效路径。")
    path = PurePosixPath(normalized)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise ModInspectionError("MOD 包含越界路径。")
    if any(":" in part for part in path.parts):
        raise ModInspectionError("MOD 包含绝对路径或驱动器路径。")
    return path.as_posix()


def slugify(value: str) -> str:
    folded = value.casefold()
    folded = re.sub(r"[^a-z0-9]+", "-", folded).strip("-")
    if folded:
        return folded[:48]
    digest = hashlib.sha256(value.encode("utf-8")).hexdigest()[:12]
    return f"community-mod-{digest}"


def normalize_panel_hotkey(value: str) -> str:
    try:
        return "+".join(parse_hotkey_chord(value))
    except WindowsInputError as exception:
        raise ModInspectionError(
            "lc2-mod.json interaction.panel_hotkey 不受支持。"
        ) from exception


def split_versioned_dll_stem(value: str) -> tuple[str, tuple[int, ...], str] | None:
    match = re.fullmatch(
        r"(?i)(?P<base>.+?)(?:[._ -]*v?)(?P<version>\d+(?:\.\d+){1,3})",
        value.strip(),
    )
    if match is None:
        return None
    base = match.group("base").rstrip(" ._-")
    if not base:
        return None
    version_text = match.group("version")
    return base, tuple(int(part) for part in version_text.split(".")), version_text


def prefer_latest_versioned_dlls(
    candidates: Iterable[PackageMember],
) -> tuple[PackageMember, ...]:
    """Collapse an obvious same-plugin version series to its newest DLL."""

    items = tuple(candidates)
    dlls = tuple(item for item in items if item.suffix == ".dll")
    if len(dlls) < 2:
        return items
    parsed = tuple(split_versioned_dll_stem(Path(item.path).stem) for item in dlls)
    if any(item is None for item in parsed):
        return items
    resolved = tuple(item for item in parsed if item is not None)
    if len({item[0].casefold() for item in resolved}) != 1:
        return items
    latest_index = max(range(len(dlls)), key=lambda index: resolved[index][1])
    latest = dlls[latest_index]
    return tuple(item for item in items if item.suffix != ".dll" or item == latest)


def _sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest().upper()


def _decode_text(content: bytes) -> str:
    for encoding in ("utf-8-sig", "gb18030", "utf-16"):
        try:
            return content.decode(encoding)
        except (UnicodeDecodeError, LookupError):
            continue
    return content.decode("utf-8", errors="replace")


def _binary_strings(content: bytes) -> str:
    chunks: list[str] = []
    chunks.extend(
        match.decode("utf-8", errors="ignore")
        for match in re.findall(rb"[\x20-\x7e\x80-\xff]{4,}", content)
    )
    for encoding in ("utf-16le", "utf-16be"):
        decoded = content.decode(encoding, errors="ignore")
        chunks.extend(re.findall(r"[\w\u3400-\u9fff .:+_\-/]{4,}", decoded))
    return "\n".join(chunks)


def _dotnet_user_strings(content: bytes) -> str:
    """Read managed #US strings without loading or executing the assembly."""

    logger = logging.getLogger("dnfile.stream")
    previous_level = logger.level
    logger.setLevel(logging.ERROR)
    try:
        image = dnfile.dnPE(data=content)
        if image.net is None:
            return ""
        heap = image.net.metadata.streams.get(b"#US")
        if heap is None:
            return ""
        offset = 1
        limit = heap.sizeof()
        values: list[str] = []
        while offset < limit:
            item = heap.get(offset)
            if item is None or item.raw_size <= 0:
                break
            value = item.value_bytes().decode("utf-16-le", errors="replace").rstrip("\x00")
            if value:
                values.append(value)
            offset += item.raw_size
        return "\n".join(values)
    except Exception:
        return ""
    finally:
        logger.setLevel(previous_level)


def _read_compressed_uint(data: bytes, offset: int) -> tuple[int, int]:
    if offset >= len(data):
        raise ValueError("compressed integer is truncated")
    first = data[offset]
    if first & 0x80 == 0:
        return first, offset + 1
    if first & 0xC0 == 0x80:
        if offset + 1 >= len(data):
            raise ValueError("compressed integer is truncated")
        return ((first & 0x3F) << 8) | data[offset + 1], offset + 2
    if first & 0xE0 == 0xC0:
        if offset + 3 >= len(data):
            raise ValueError("compressed integer is truncated")
        return (
            ((first & 0x1F) << 24)
            | (data[offset + 1] << 16)
            | (data[offset + 2] << 8)
            | data[offset + 3],
            offset + 4,
        )
    raise ValueError("compressed integer prefix is invalid")


def _read_serialized_string(data: bytes, offset: int) -> tuple[str | None, int]:
    if offset >= len(data):
        raise ValueError("serialized string is truncated")
    if data[offset] == 0xFF:
        return None, offset + 1
    length, start = _read_compressed_uint(data, offset)
    end = start + length
    if end > len(data):
        raise ValueError("serialized string is truncated")
    return data[start:end].decode("utf-8"), end


def _bepin_plugin_metadata(content: bytes) -> tuple[str, str, str] | None:
    """Read BepInPlugin(guid, name, version) without loading the assembly."""

    logger = logging.getLogger("dnfile.stream")
    previous_level = logger.level
    logger.setLevel(logging.ERROR)
    try:
        image = dnfile.dnPE(data=content)
        table = image.net.mdtables.CustomAttribute if image.net is not None else None
        if table is None:
            return None
        for attribute in table.rows:
            constructor = getattr(attribute.Type, "row", None)
            owner = getattr(getattr(constructor, "Class", None), "row", None)
            if (
                str(getattr(owner, "TypeNamespace", "")) != "BepInEx"
                or str(getattr(owner, "TypeName", "")) != "BepInPlugin"
                or str(getattr(constructor, "Name", "")) != ".ctor"
            ):
                continue
            data = attribute.Value.value_bytes()
            if not data.startswith(b"\x01\x00"):
                continue
            offset = 2
            values: list[str] = []
            for _index in range(3):
                value, offset = _read_serialized_string(data, offset)
                if not value:
                    raise ValueError("BepInPlugin contains an empty fixed argument")
                values.append(value)
            return values[0], values[1], values[2]
    except Exception:
        return None
    finally:
        logger.setLevel(previous_level)
    return None


def _unique_matches(pattern: str, text: str, *, flags: int = 0) -> tuple[str, ...]:
    values: list[str] = []
    for match in re.finditer(pattern, text, flags):
        value = (match.group(1) if match.lastindex else match.group(0)).strip()
        if value and value.casefold() not in {item.casefold() for item in values}:
            values.append(value)
    return tuple(values)


def _parse_manifest(content: bytes) -> dict[str, object]:
    try:
        payload = json.loads(_decode_text(content))
    except (json.JSONDecodeError, UnicodeDecodeError) as exception:
        raise ModInspectionError("lc2-mod.json 不是有效 JSON。") from exception
    if not isinstance(payload, dict) or payload.get("schema_version") != 1:
        raise ModInspectionError("lc2-mod.json schema_version 必须为 1。")
    return payload


class ModPackageInspector:
    def __init__(self, seven_zip: Path) -> None:
        self.seven_zip = seven_zip.resolve()
        if not self.seven_zip.is_file():
            raise ModInspectionError("未找到可用的 7-Zip 命令行组件。")

    def inspect(self, source: Path) -> ModDraft:
        source = source.resolve()
        members, reader, source_kind = self._open_source(source)
        files = tuple(member for member in members if not member.is_directory)
        if len(files) > MAX_ARCHIVE_MEMBERS:
            raise ModInspectionError("MOD 文件过多，不能自动添加；请提供 lc2-mod.json。")
        framework_hits = self._framework_hits(files)
        if framework_hits:
            raise ModInspectionError("检测到 BepInEx 框架或覆盖文件，不能按普通 MOD 自动添加。")

        manifest_member = next(
            (member for member in files if Path(member.path).name.casefold() == "lc2-mod.json"),
            None,
        )
        manifest = _parse_manifest(reader(manifest_member.path)) if manifest_member else None
        payload_members = self._select_payload(files, reader, manifest)
        payload = self._materialize_specs(payload_members, reader)
        documents = tuple(
            member
            for member in files
            if member.suffix in DOCUMENT_EXTENSIONS and member.size_bytes <= 1024 * 1024
        )
        document_text = "\n".join(_decode_text(reader(member.path)) for member in documents)
        binary_chunks: list[str] = []
        plugin_metadata: list[tuple[str, str, str]] = []
        for member in payload_members:
            if member.suffix != ".dll" or member.size_bytes > 8 * 1024 * 1024:
                continue
            content = reader(member.path)
            binary_chunks.extend((_binary_strings(content), _dotnet_user_strings(content)))
            metadata = _bepin_plugin_metadata(content)
            if metadata is not None and metadata not in plugin_metadata:
                plugin_metadata.append(metadata)
        binary_text = "\n".join(binary_chunks)
        contextual_binary = "\n".join(
            line
            for line in binary_text.splitlines()
            if re.search(
                r"(?i)(?:作者(?:\s*[:：]|\s+)|author\s*[:：=]|快捷键|hotkey|toggle|panel|面板|按\s*(?:F\d|INS))",
                line,
            )
        )
        combined_text = f"{source.name}\n{document_text}\n{contextual_binary}"
        return self._build_draft(
            source,
            source_kind,
            payload,
            manifest,
            combined_text,
            bool(documents),
            tuple(plugin_metadata),
        )

    def read_payload(self, draft: ModDraft) -> dict[str, bytes]:
        _members, reader, _kind = self._open_source(draft.source)
        return {item.target_path: reader(item.source_path) for item in draft.payload}

    def _open_source(
        self, source: Path
    ) -> tuple[tuple[PackageMember, ...], Callable[[str], bytes], str]:
        if source.is_dir():
            root = source
            members = tuple(
                PackageMember(
                    path=item.relative_to(root).as_posix(),
                    size_bytes=item.stat().st_size,
                )
                for item in sorted(root.rglob("*"))
                if item.is_file()
            )

            def read_folder(member: str) -> bytes:
                normalized = normalize_member_path(member)
                candidate = (root / Path(*PurePosixPath(normalized).parts)).resolve()
                try:
                    candidate.relative_to(root)
                except ValueError as exception:
                    raise ModInspectionError("MOD 文件夹成员越界。") from exception
                return candidate.read_bytes()

            return members, read_folder, "folder"
        if not source.is_file():
            raise ModInspectionError("MOD 来源不存在。")
        if source.suffix.casefold() == ".dll":
            member = PackageMember(source.name, source.stat().st_size)
            return (member,), lambda _member: source.read_bytes(), "dll"
        if source.suffix.casefold() not in SUPPORTED_ARCHIVES:
            raise ModInspectionError("只支持 DLL、ZIP、7Z、RAR 或文件夹。")
        members = self._list_archive(source)

        def read_archive(member: str) -> bytes:
            normalized = normalize_member_path(member)
            result = subprocess.run(
                [str(self.seven_zip), "x", "-so", "-bd", "--", str(source), normalized],
                check=False,
                capture_output=True,
                timeout=30,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            if result.returncode != 0:
                raise ModInspectionError("无法读取 MOD 压缩包成员。")
            return result.stdout

        return members, read_archive, "archive"

    def _list_archive(self, source: Path) -> tuple[PackageMember, ...]:
        result = subprocess.run(
            [str(self.seven_zip), "l", "-slt", "-sccUTF-8", "-ba", "--", str(source)],
            check=False,
            capture_output=True,
            timeout=30,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        if result.returncode != 0:
            raise ModInspectionError("无法列出 MOD 压缩包。")
        text = result.stdout.decode("utf-8", errors="strict")
        members: list[PackageMember] = []
        for block in re.split(r"\r?\n\s*\r?\n", text.strip()):
            values: dict[str, str] = {}
            for line in block.splitlines():
                if " = " in line:
                    key, value = line.split(" = ", 1)
                    values[key] = value
            if "Path" not in values:
                continue
            attributes = values.get("Attributes", "")
            is_directory = values.get("Folder") == "+" or attributes.startswith("D")
            path = normalize_member_path(values["Path"])
            size = int(values.get("Size", "0") or "0")
            if size < 0 or size > MAX_MEMBER_BYTES:
                raise ModInspectionError("MOD 包含过大的单个文件。")
            members.append(PackageMember(path, size, is_directory))
        return tuple(members)

    @staticmethod
    def _framework_hits(members: Iterable[PackageMember]) -> tuple[str, ...]:
        hits: list[str] = []
        for member in members:
            folded = member.path.casefold()
            if any(marker in folded for marker in FRAMEWORK_MARKERS):
                hits.append(member.path)
        return tuple(hits)

    def _select_payload(
        self,
        members: tuple[PackageMember, ...],
        reader: Callable[[str], bytes],
        manifest: dict[str, object] | None,
    ) -> tuple[PackageMember, ...]:
        if manifest is not None:
            install = manifest.get("install")
            if not isinstance(install, dict):
                raise ModInspectionError("lc2-mod.json 缺少 install。")
            include = install.get("files")
            if not isinstance(include, list) or not include:
                raise ModInspectionError("lc2-mod.json install.files 必须是非空数组。")
            by_path = {member.path.casefold(): member for member in members}
            selected: list[PackageMember] = []
            for raw in include:
                if not isinstance(raw, str):
                    raise ModInspectionError("lc2-mod.json install.files 只能包含路径。")
                normalized = normalize_member_path(raw)
                member = by_path.get(normalized.casefold())
                if member is None or member.is_directory:
                    raise ModInspectionError(f"清单文件不存在：{normalized}")
                selected.append(member)
            candidates = selected
        else:
            candidates = [
                member
                for member in members
                if member.suffix in PAYLOAD_EXTENSIONS
                and "/obj/" not in f"/{member.path.casefold()}/"
                and "/ref/" not in f"/{member.path.casefold()}/"
                and "/refint/" not in f"/{member.path.casefold()}/"
            ]
            release_dlls = [
                member
                for member in candidates
                if member.suffix == ".dll"
                and "/bin/release/" in f"/{member.path.casefold()}"
            ]
            if release_dlls:
                release_hashes = {_sha256(reader(member.path)) for member in release_dlls}
                candidates = [
                    member
                    for member in candidates
                    if member.suffix != ".dll"
                    or "/bin/release/" in f"/{member.path.casefold()}"
                    or _sha256(reader(member.path)) not in release_hashes
                ]
            candidates = list(prefer_latest_versioned_dlls(candidates))
        dlls = [member for member in candidates if member.suffix == ".dll"]
        if not dlls:
            raise ModInspectionError("未检测到可安装的 DLL。")
        if len(candidates) > MAX_PAYLOAD_FILES:
            raise ModInspectionError("可安装文件过多，请提供精确 lc2-mod.json。")
        if sum(member.size_bytes for member in candidates) > MAX_TOTAL_PAYLOAD_BYTES:
            raise ModInspectionError("MOD 载荷过大，请提供精确 lc2-mod.json。")
        return tuple(candidates)

    @staticmethod
    def _materialize_specs(
        members: tuple[PackageMember, ...], reader: Callable[[str], bytes]
    ) -> tuple[PayloadFile, ...]:
        raw_paths = [PurePosixPath(member.path) for member in members]
        common_prefix: tuple[str, ...] = ()
        if raw_paths:
            first = raw_paths[0].parts
            length = 0
            for index, part in enumerate(first[:-1]):
                if all(len(path.parts) > index and path.parts[index] == part for path in raw_paths):
                    length += 1
                else:
                    break
            common_prefix = first[:length]
        files: list[PayloadFile] = []
        targets: set[str] = set()
        hashes: set[tuple[str, int]] = set()
        for member, source_path in zip(members, raw_paths, strict=True):
            parts = source_path.parts[len(common_prefix) :]
            if not parts:
                parts = (source_path.name,)
            target = normalize_member_path(PurePosixPath(*parts).as_posix())
            content = reader(member.path)
            if len(content) != member.size_bytes:
                raise ModInspectionError("MOD 成员大小与压缩包目录不一致。")
            digest = _sha256(content)
            identity = (digest, len(content))
            if identity in hashes:
                continue
            if target.casefold() in targets:
                raise ModInspectionError("MOD 包含目标路径冲突。")
            targets.add(target.casefold())
            hashes.add(identity)
            files.append(PayloadFile(member.path, target, len(content), digest))
        return tuple(files)

    @staticmethod
    def _build_draft(
        source: Path,
        source_kind: str,
        payload: tuple[PayloadFile, ...],
        manifest: dict[str, object] | None,
        combined_text: str,
        has_documents: bool,
        plugin_metadata: tuple[tuple[str, str, str], ...],
    ) -> ModDraft:
        display = manifest.get("display") if manifest else None
        if display is not None and not isinstance(display, dict):
            raise ModInspectionError("lc2-mod.json display 必须是对象。")
        display = display if isinstance(display, dict) else {}
        dll_names = [Path(item.target_path).stem for item in payload if item.target_path.casefold().endswith(".dll")]
        source_name = source.stem
        version_matches = tuple(
            value[1:] if value.casefold().startswith("v") else value
            for value in _unique_matches(
                r"(?i)(?:^|[^A-Za-z0-9])(v\d+(?:\.\d+){0,3}|\d+\.\d+(?:\.\d+){0,2})(?:[^0-9]|$)",
                source_name,
            )
        )
        payload_version = (
            split_versioned_dll_stem(dll_names[0]) if len(dll_names) == 1 else None
        )
        hotkey_text = f"{combined_text}\n{display.get('usage_hint', '')}"
        hotkeys = _unique_matches(
            r"(?i)(?<![A-Za-z0-9])((?:(?:Ctrl|Alt|Shift)\s*\+\s*)*(?:F(?:1[0-2]|[1-9])|INS|INSERT))(?![A-Za-z0-9])",
            hotkey_text,
        )
        interaction = manifest.get("interaction") if manifest else None
        if interaction is not None and not isinstance(interaction, dict):
            raise ModInspectionError("lc2-mod.json interaction 必须是对象。")
        manifest_panel_hotkey = (
            interaction.get("panel_hotkey") if isinstance(interaction, dict) else None
        )
        if manifest_panel_hotkey is not None and (
            not isinstance(manifest_panel_hotkey, str) or not manifest_panel_hotkey.strip()
        ):
            raise ModInspectionError("lc2-mod.json interaction.panel_hotkey 必须是快捷键字符串。")
        panel_hotkey = (
            normalize_panel_hotkey(manifest_panel_hotkey)
            if isinstance(manifest_panel_hotkey, str)
            else None
        )
        if panel_hotkey is None:
            panel_matches = _unique_matches(
                r"(?i)((?:(?:Ctrl|Alt|Shift)\s*\+\s*)*(?:F(?:1[0-2]|[1-9])|INS|INSERT))\s*(?:键)?\s*(?:打开|显示|切换|唤出)[^\n。；]{0,16}(?:面板|界面|窗口|设置)",
                hotkey_text,
            )
            if len(panel_matches) == 1:
                panel_hotkey = normalize_panel_hotkey(panel_matches[0])
        if panel_hotkey is not None:
            normalized_hotkeys = tuple(normalize_panel_hotkey(item) for item in hotkeys)
            if panel_hotkey not in normalized_hotkeys:
                hotkeys = (*hotkeys, panel_hotkey)
        authors = _unique_matches(
            r"(?im)(?:作者(?:\s*[:：]\s*|\s+)|author\s*[:：=]\s*|(?:^|\s)by\s+)([\w\u3400-\u9fff.\-]{1,30})",
            combined_text,
        )
        manifest_id = manifest.get("id") if manifest else None
        if isinstance(manifest_id, str) and manifest_id:
            suggested_id = manifest_id.strip()
            if not MOD_ID_PATTERN.fullmatch(suggested_id):
                raise ModInspectionError("lc2-mod.json id 只能使用小写字母、数字和连字符。")
        else:
            id_seed = payload_version[0] if payload_version else (dll_names[0] if dll_names else source_name)
            suggested_id = slugify(id_seed)
        name = str(display.get("name") or source_name).strip()
        detected_version = (
            version_matches[0]
            if version_matches
            else plugin_metadata[0][2]
            if len({item[2] for item in plugin_metadata}) == 1
            else payload_version[2]
            if payload_version
            else "1.0"
        )
        version = str(display.get("version") or detected_version).strip()
        author = str(display.get("author") or (authors[0] if authors else "社区未署名")).strip()
        summary = str(display.get("summary") or f"{name} 的游戏功能扩展").strip()
        manifest_usage = display.get("usage_hint")
        if manifest_usage:
            usage_hint = str(manifest_usage).strip()
        elif hotkeys:
            usage_hint = f"安装后启动游戏，使用 {' / '.join(hotkeys)} 操作；详细功能请查看原说明。"
        else:
            usage_hint = "安装后重启游戏生效；如有配置项，请查看 MOD 原说明。"
        evidence = ["文件名", "DLL 载荷"]
        if has_documents:
            evidence.append("随包说明")
        if manifest:
            evidence.append("lc2-mod.json")
        if plugin_metadata:
            evidence.append("BepInPlugin 元数据")
        warnings: list[str] = []
        folded_name = source.name.casefold()
        for marker, message in (
            ("未完成", "来源标记为未完成"),
            ("半成品", "来源标记为半成品"),
            ("测试", "来源标记为测试版本"),
            ("有bug", "来源明确标记存在 bug"),
            ("有 bug", "来源明确标记存在 bug"),
        ):
            if marker in folded_name:
                warnings.append(message)
        return ModDraft(
            source=source,
            source_kind=source_kind,
            suggested_id=suggested_id,
            name=name,
            version=version,
            author=author,
            summary=summary,
            usage_hint=usage_hint,
            hotkeys=hotkeys,
            panel_hotkey=panel_hotkey,
            payload=payload,
            manifest=manifest,
            evidence=tuple(evidence),
            warnings=tuple(warnings),
        )
