from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import tempfile
from typing import Callable
import uuid
import zipfile


SHA256_PATTERN = re.compile(r"^[0-9A-F]{64}$")
CONSOLE_SECTION = "Logging.Console"
CONSOLE_KEY = "Enabled"


class RuntimeSetupError(RuntimeError):
    """Raised when the managed game runtime cannot be installed safely."""


class RuntimeSetupConflict(RuntimeSetupError):
    """Raised when an existing runtime file differs from the pinned bundle."""


class RuntimeSetupGameRunning(RuntimeSetupError):
    """Raised when setup is attempted while this game executable is running."""


@dataclass(frozen=True)
class RuntimeFileSpec:
    path: str
    size_bytes: int
    sha256: str


@dataclass(frozen=True)
class RuntimeSetupStatus:
    state: str
    detail: str

    @property
    def ready(self) -> bool:
        return self.state == "ready"


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def normalized_relative_path(value: str) -> str:
    normalized = value.replace("\\", "/")
    path = PurePosixPath(normalized)
    if (
        not normalized
        or path.is_absolute()
        or ".." in path.parts
        or ":" in normalized
        or normalized.endswith("/")
    ):
        raise RuntimeSetupError("运行环境清单包含不安全路径。")
    return path.as_posix()


def console_is_enabled(text: str) -> bool:
    current_section = ""
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("[") and stripped.endswith("]"):
            current_section = stripped[1:-1].strip()
            continue
        if current_section.casefold() != CONSOLE_SECTION.casefold():
            continue
        match = re.match(r"^\s*Enabled\s*=\s*(.*?)\s*$", line, re.IGNORECASE)
        if match:
            return match.group(1).casefold() in {"true", "1", "yes", "on"}
    return True


def disable_console(text: str) -> str:
    lines = text.splitlines()
    current_section = ""
    section_index: int | None = None
    for index, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("[") and stripped.endswith("]"):
            current_section = stripped[1:-1].strip()
            if current_section.casefold() == CONSOLE_SECTION.casefold():
                section_index = index
            continue
        if current_section.casefold() != CONSOLE_SECTION.casefold():
            continue
        match = re.match(r"^(\s*Enabled\s*=\s*).*$", line, re.IGNORECASE)
        if match:
            lines[index] = f"{match.group(1)}false"
            return "\n".join(lines) + "\n"
    if section_index is not None:
        lines.insert(section_index + 1, f"{CONSOLE_KEY} = false")
    else:
        if lines and lines[-1]:
            lines.append("")
        lines.extend((f"[{CONSOLE_SECTION}]", f"{CONSOLE_KEY} = false"))
    return "\n".join(lines) + "\n"


class RuntimeSetupManager:
    def __init__(
        self,
        manifest_path: Path,
        bundle_root: Path,
        game_exe_provider: Callable[[], Path | None],
        *,
        game_running_provider: Callable[[Path], bool] | None = None,
        backup_root: Path | None = None,
    ) -> None:
        self.manifest_path = manifest_path.resolve()
        self.bundle_root = bundle_root.resolve()
        self.game_exe_provider = game_exe_provider
        self.game_running_provider = game_running_provider or (lambda _path: False)
        self.backup_root = backup_root.resolve() if backup_root is not None else None
        self.last_backup_path: Path | None = None
        payload = json.loads(self.manifest_path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict) or payload.get("schema_version") != 1:
            raise RuntimeSetupError("不支持的游戏运行环境清单。")
        self.runtime_archive = self._parse_file_identity(payload.get("runtime_archive"))
        raw_files = payload.get("runtime_files")
        if not isinstance(raw_files, list) or not raw_files:
            raise RuntimeSetupError("游戏运行环境清单缺少文件。")
        self.runtime_files = tuple(self._parse_spec(raw) for raw in raw_files)
        if len({spec.path.casefold() for spec in self.runtime_files}) != len(
            self.runtime_files
        ):
            raise RuntimeSetupError("游戏运行环境清单路径重复。")
        raw_required = payload.get("required_paths")
        if not isinstance(raw_required, list) or not all(
            isinstance(item, str) for item in raw_required
        ):
            raise RuntimeSetupError("游戏运行环境清单缺少就绪标记。")
        self.required_paths = tuple(normalized_relative_path(item) for item in raw_required)
        self._spec_by_path = {spec.path.casefold(): spec for spec in self.runtime_files}
        if any(path.casefold() not in self._spec_by_path for path in self.required_paths):
            raise RuntimeSetupError("游戏运行环境就绪标记未绑定文件身份。")
        self.bridge = self._parse_spec(payload.get("bridge"), target_key="target")
        self.features = (
            self._parse_spec(payload["features"], target_key="target")
            if "features" in payload else None
        )
        if self.features is not None and self.features.path != "BepInEx/plugins/LC2ToolboxFeatures/LC2ToolboxFeatures.dll":
            raise RuntimeSetupError("工具箱功能组件目标目录无效。")
        self.generated_config: tuple[str, str] | None = None
        if "configuration" in payload:
            configuration = payload["configuration"]
            if not isinstance(configuration, dict):
                raise RuntimeSetupError("运行环境配置声明无效。")
            path = configuration.get("path")
            source = configuration.get("fresh_unity_base_libraries_source")
            if (
                path != "BepInEx/config/BepInEx.cfg"
                or configuration.get("fresh_console_enabled") is not False
                or not isinstance(source, str)
                or not source.startswith("https://")
                or any(char in source for char in "\r\n")
                or path.casefold() in self._spec_by_path
            ):
                raise RuntimeSetupError("运行环境配置声明无效。")
            self.generated_config = (path, f"[Logging.Console]\nEnabled = false\n\n[IL2CPP]\nUnityBaseLibrariesSource = {source}\n")

    @staticmethod
    def _parse_file_identity(raw: object) -> RuntimeFileSpec:
        return RuntimeSetupManager._parse_spec(raw, target_key="filename")

    @staticmethod
    def _parse_spec(raw: object, *, target_key: str = "path") -> RuntimeFileSpec:
        if not isinstance(raw, dict):
            raise RuntimeSetupError("游戏运行环境文件身份无效。")
        raw_path = raw.get(target_key)
        raw_size = raw.get("size_bytes")
        raw_sha = raw.get("sha256")
        if not isinstance(raw_path, str):
            raise RuntimeSetupError("游戏运行环境文件路径无效。")
        path = normalized_relative_path(raw_path)
        if type(raw_size) is not int or raw_size <= 0:
            raise RuntimeSetupError("游戏运行环境文件大小无效。")
        if not isinstance(raw_sha, str) or not SHA256_PATTERN.fullmatch(raw_sha.upper()):
            raise RuntimeSetupError("游戏运行环境文件哈希无效。")
        return RuntimeFileSpec(path, raw_size, raw_sha.upper())

    def _game_exe(self) -> Path | None:
        value = self.game_exe_provider()
        if value is None:
            return None
        path = Path(value).resolve()
        if path.name.casefold() != "lostcastle2.exe" or not path.is_file():
            return None
        return path

    @staticmethod
    def _target(game_root: Path, relative: str) -> Path:
        target = game_root.joinpath(*PurePosixPath(relative).parts).resolve()
        try:
            target.relative_to(game_root.resolve())
        except ValueError as exception:
            raise RuntimeSetupError("游戏运行环境目标越界。") from exception
        return target

    @staticmethod
    def _matches(path: Path, spec: RuntimeFileSpec) -> bool:
        return (
            path.is_file()
            and path.stat().st_size == spec.size_bytes
            and file_sha256(path) == spec.sha256
        )

    def needs_framework_update(self) -> bool:
        game = self._game_exe()
        if game is None:
            return False
        for spec in self.runtime_files:
            if spec.path.casefold().endswith("bepinex.cfg"):
                continue
            target = self._checked_target(game.parent, spec.path)
            if self._is_generated_unity_library(spec):
                continue
            if target.exists() and not self._matches(target, spec):
                return True
        return False

    @staticmethod
    def _is_generated_unity_library(spec: RuntimeFileSpec) -> bool:
        # BepInEx unstrips these DLLs in place at startup. The pinned ZIP and
        # bootstrap/core/.NET files remain immutable installation identities.
        return spec.path.casefold().startswith("bepinex/unity-libs/") and spec.path.casefold().endswith(".dll")

    def status(self) -> RuntimeSetupStatus:
        game_exe = self._game_exe()
        if game_exe is None:
            return RuntimeSetupStatus("game_not_configured", "未定位 LostCastle2.exe")
        game_root = game_exe.parent
        for relative in self.required_paths:
            spec = self._spec_by_path[relative.casefold()]
            target = self._target(game_root, relative)
            if not target.exists():
                return RuntimeSetupStatus("missing", "HUD / MOD 运行环境尚未初始化")
            if self._is_generated_unity_library(spec) and target.is_file():
                self._checked_target(game_root, relative)
                continue
            if relative.casefold().endswith("bepinex.cfg"):
                try:
                    if console_is_enabled(target.read_text(encoding="utf-8-sig")):
                        return RuntimeSetupStatus("needs_configuration", "需关闭调试控制台")
                except (OSError, UnicodeError):
                    return RuntimeSetupStatus("conflict", "现有 BepInEx 配置无法安全读取")
                continue
            if not self._matches(target, spec):
                return RuntimeSetupStatus("conflict", f"现有运行环境文件不同：{relative}")
        if self.needs_framework_update():
            return RuntimeSetupStatus("conflict", "现有运行库需要更新为工具箱配套版本")
        if self.generated_config is not None:
            config = self._target(game_root, self.generated_config[0])
            if not config.exists():
                return RuntimeSetupStatus("needs_configuration", "需生成 HUD / MOD 运行环境配置")
            try:
                if console_is_enabled(config.read_text(encoding="utf-8-sig")):
                    return RuntimeSetupStatus("needs_configuration", "需关闭调试控制台")
            except (OSError, UnicodeError):
                return RuntimeSetupStatus("conflict", "现有 BepInEx 配置无法安全读取")
        bridge_target = self._target(game_root, self.bridge.path)
        if not bridge_target.exists():
            return RuntimeSetupStatus("missing", "战斗 HUD Bridge 尚未安装")
        if not self._matches(bridge_target, self.bridge):
            return RuntimeSetupStatus("bridge_update", "战斗 HUD Bridge 需要更新")
        if self.features is not None:
            if not self._matches(self._target(game_root, self.features.path), self.features):
                return RuntimeSetupStatus("features_update", "工具箱功能组件需要更新")
        return RuntimeSetupStatus("ready", "HUD / MOD 运行环境已就绪")

    def _bundle_file(self, spec: RuntimeFileSpec) -> Path:
        source = self.bundle_root.joinpath(*PurePosixPath(spec.path).parts).resolve()
        try:
            source.relative_to(self.bundle_root)
        except ValueError as exception:
            raise RuntimeSetupError("随包运行环境路径越界。") from exception
        if not self._matches(source, spec):
            raise RuntimeSetupError("随包运行环境文件校验失败。")
        return source

    def _bridge_bundle_spec(self) -> RuntimeFileSpec:
        return RuntimeFileSpec(
            self.bridge.path.split("/")[-1],
            self.bridge.size_bytes,
            self.bridge.sha256,
        )

    def _read_runtime_contents(self, archive_path: Path) -> dict[str, bytes]:
        contents: dict[str, bytes] = {}
        with zipfile.ZipFile(archive_path) as archive:
            by_name = {
                normalized_relative_path(info.filename).casefold(): info
                for info in archive.infolist()
                if not info.is_dir()
            }
            if set(by_name) != set(self._spec_by_path):
                raise RuntimeSetupError("随包运行环境成员清单不一致。")
            for spec in self.runtime_files:
                content = archive.read(by_name[spec.path.casefold()])
                if (
                    len(content) != spec.size_bytes
                    or hashlib.sha256(content).hexdigest().upper() != spec.sha256
                ):
                    raise RuntimeSetupError("随包运行环境成员校验失败。")
                contents[spec.path] = content
        return contents

    def verify_bundle(self) -> None:
        archive_path = self._bundle_file(self.runtime_archive)
        self._bundle_file(self._bridge_bundle_spec())
        self._read_runtime_contents(archive_path)
        if self.features is not None:
            self._bundle_file(RuntimeFileSpec(self.features.path.split("/")[-1], self.features.size_bytes, self.features.sha256))

    @staticmethod
    def _write_atomic(target: Path, content: bytes) -> None:
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                prefix=f".{target.name}.", suffix=".tmp", dir=target.parent, delete=False
            ) as stream:
                stream.write(content)
                temporary = Path(stream.name)
            os.replace(temporary, target)
        finally:
            if temporary is not None and temporary.exists():
                temporary.unlink()

    def _backup(self, source: Path, label: str) -> None:
        if self.backup_root is None or not source.is_file():
            return
        digest = file_sha256(source)
        destination = self.backup_root / f"{label}.{digest[:12]}.bak"
        destination.parent.mkdir(parents=True, exist_ok=True)
        if not destination.exists():
            shutil.copy2(source, destination)

    @staticmethod
    def _checked_target(game_root: Path, relative: str) -> Path:
        """Reject linked runtime paths before planning, backup or replacement."""
        target = game_root.joinpath(*PurePosixPath(normalized_relative_path(relative)).parts)
        for candidate in (target, *target.parents):
            if candidate.exists() or candidate.is_symlink():
                attributes = getattr(candidate.lstat(), "st_file_attributes", 0)
                if candidate.is_symlink() or attributes & stat.FILE_ATTRIBUTE_REPARSE_POINT:
                    raise RuntimeSetupConflict(f"运行环境路径是链接，请先恢复普通目录：{relative}")
            if candidate == game_root:
                break
        RuntimeSetupManager._target(game_root, relative)
        return target

    def _check_game_stopped(self, game_exe: Path) -> None:
        # An exact-process query treats unavailable executable identity as running.
        for _observation in range(2):
            if self.game_running_provider(game_exe) is not False:
                raise RuntimeSetupGameRunning("请先完全关闭游戏，再更新运行环境。")

    def _replace_runtime(
        self, game_exe: Path, contents: dict[str, bytes], bridge_content: bytes
    ) -> RuntimeSetupStatus:
        """Update the framework transactionally, leaving plugins/configuration intact."""
        game_root = game_exe.parent
        desired = dict(contents)
        desired[self.bridge.path] = bridge_content
        if self.features is not None:
            feature_source = self._bundle_file(RuntimeFileSpec(self.features.path.split("/")[-1], self.features.size_bytes, self.features.sha256))
            desired[self.features.path] = feature_source.read_bytes()
        config_relative = "BepInEx/config/BepInEx.cfg"
        config_target = self._checked_target(game_root, config_relative)
        if config_target.exists():
            try:
                current_config = config_target.read_text(encoding="utf-8-sig")
            except (OSError, UnicodeError) as exception:
                raise RuntimeSetupConflict("现有 BepInEx 配置无法安全读取。") from exception
            desired[config_relative] = disable_console(current_config).encode("utf-8")
        elif self.generated_config is not None:
            desired[config_relative] = self.generated_config[1].encode("utf-8")

        clean_roots = ("BepInEx/core", "dotnet", "BepInEx/interop", "BepInEx/cache", "BepInEx/unhollowed")
        stale: set[str] = set()
        desired_folded = {relative.casefold() for relative in desired}
        for relative_root in clean_roots:
            root = self._checked_target(game_root, relative_root)
            if not root.exists():
                continue
            if not root.is_dir():
                raise RuntimeSetupConflict(f"运行环境目录被文件占用：{relative_root}")
            for directory, directories, filenames in os.walk(root, followlinks=False):
                base = Path(directory)
                for name in (*directories, *filenames):
                    self._checked_target(game_root, (base / name).relative_to(game_root).as_posix())
                for name in filenames:
                    relative = (base / name).relative_to(game_root).as_posix()
                    if relative.casefold() not in desired_folded:
                        stale.add(relative)
                if len(stale) > 20000:
                    raise RuntimeSetupError("运行环境缓存文件过多，请先导出诊断。")

        changes: dict[str, bytes | None] = {}
        originals: dict[str, dict[str, object] | None] = {}
        for relative in sorted(set(desired) | stale):
            target = self._checked_target(game_root, relative)
            if target.exists() and not target.is_file():
                raise RuntimeSetupConflict(f"运行环境文件被目录占用：{relative}")
            replacement = desired.get(relative)
            old_identity = None
            if target.is_file():
                old_identity = {"size_bytes": target.stat().st_size, "sha256": file_sha256(target)}
                if replacement is not None and old_identity == {
                    "size_bytes": len(replacement), "sha256": hashlib.sha256(replacement).hexdigest().upper()
                }:
                    continue
            elif replacement is None:
                continue
            originals[relative] = old_identity
            changes[relative] = replacement
        backup_base = self.backup_root or game_root / "LC2ToolboxBackups" / "runtime"
        backup = backup_base / (datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:12])
        for relative_root in clean_roots:
            if backup.resolve().is_relative_to(game_root / relative_root):
                raise RuntimeSetupError("运行环境备份目录不能位于待更新目录。")
        backup.mkdir(parents=True, exist_ok=False)
        self.last_backup_path = backup
        receipt = {
            "schema_version": 1, "game_exe": str(game_exe), "state": "preparing",
            "originals": originals,
            "replacements": {relative: None if content is None else {
                "size_bytes": len(content), "sha256": hashlib.sha256(content).hexdigest().upper()
            } for relative, content in changes.items()},
        }
        receipt_path = backup / "manifest.json"
        self._write_atomic(receipt_path, json.dumps(receipt, ensure_ascii=False, indent=2).encode("utf-8"))
        for relative, identity in originals.items():
            if identity is None:
                continue
            source = self._checked_target(game_root, relative)
            saved = backup / "original" / relative
            saved.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, saved)
            if saved.stat().st_size != identity["size_bytes"] or file_sha256(saved) != identity["sha256"]:
                raise RuntimeSetupError(f"运行环境备份回读失败：{relative}")
        receipt["state"] = "prepared"
        self._write_atomic(receipt_path, json.dumps(receipt, ensure_ascii=False, indent=2).encode("utf-8"))
        self._check_game_stopped(game_exe)
        touched: list[str] = []
        try:
            for relative, content in changes.items():
                target = self._checked_target(game_root, relative)
                original = originals[relative]
                if original is None:
                    if target.exists():
                        raise RuntimeSetupConflict(f"更新前文件已发生变化：{relative}")
                elif not target.is_file() or target.stat().st_size != original["size_bytes"] or file_sha256(target) != original["sha256"]:
                    raise RuntimeSetupConflict(f"更新前文件已发生变化：{relative}")
                touched.append(relative)
                if content is None:
                    target.unlink()
                else:
                    self._write_atomic(target, content)
            for relative, content in desired.items():
                target = self._checked_target(game_root, relative)
                if not target.is_file() or target.stat().st_size != len(content) or file_sha256(target) != hashlib.sha256(content).hexdigest().upper():
                    raise RuntimeSetupError(f"更新文件回读失败：{relative}")
            result = self.status()
            if not result.ready:
                raise RuntimeSetupError(f"运行环境更新后未就绪：{result.detail}")
        except Exception as exception:
            rollback_errors: list[str] = []
            for relative in reversed(touched):
                try:
                    target = self._checked_target(game_root, relative)
                    if originals[relative] is None:
                        if target.is_file():
                            target.unlink()
                    else:
                        saved = backup / "original" / relative
                        self._write_atomic(target, saved.read_bytes())
                        if file_sha256(target) != originals[relative]["sha256"]:
                            raise RuntimeSetupError("恢复文件回读失败")
                except Exception as error:
                    rollback_errors.append(f"{relative}: {error}")
            receipt.update(state="rollback_failed" if rollback_errors else "rolled_back", error=str(exception), rollback_errors=rollback_errors)
            self._write_atomic(receipt_path, json.dumps(receipt, ensure_ascii=False, indent=2).encode("utf-8"))
            if rollback_errors:
                raise RuntimeSetupError(f"更新未完成；部分文件需从备份恢复：{backup}") from exception
            raise RuntimeSetupError(f"运行环境更新失败，已恢复原文件。备份：{backup}") from exception
        receipt["state"] = "complete"
        self._write_atomic(receipt_path, json.dumps(receipt, ensure_ascii=False, indent=2).encode("utf-8"))
        return result

    def install(self, *, replace_existing: bool = False) -> RuntimeSetupStatus:
        game_exe = self._game_exe()
        if game_exe is None:
            raise RuntimeSetupError("请先在设置中定位 LostCastle2.exe。")
        self._check_game_stopped(game_exe)
        archive_path = self._bundle_file(self.runtime_archive)
        bridge_source = self._bundle_file(self._bridge_bundle_spec())
        feature_source = (
            self._bundle_file(RuntimeFileSpec(self.features.path.split("/")[-1], self.features.size_bytes, self.features.sha256))
            if self.features is not None else None
        )
        game_root = game_exe.parent
        contents = self._read_runtime_contents(archive_path)
        if replace_existing:
            return self._replace_runtime(game_exe, contents, bridge_source.read_bytes())

        for spec in (*self.runtime_files, self.bridge, *((self.features,) if self.features is not None else ())):
            self._checked_target(game_root, spec.path)
        if self.generated_config is not None:
            self._checked_target(game_root, self.generated_config[0])

        config_update: tuple[Path, str | None, str] | None = None
        if self.generated_config is not None:
            config = self._target(game_root, self.generated_config[0])
            if config.exists():
                try:
                    current = config.read_text(encoding="utf-8-sig")
                except (OSError, UnicodeError) as exception:
                    raise RuntimeSetupConflict("现有 BepInEx 配置无法安全读取。") from exception
                config_update = (config, current, disable_console(current))
            else:
                config_update = (config, None, self.generated_config[1])

        config_relative = "BepInEx/config/BepInEx.cfg"
        for spec in self.runtime_files:
            if spec.path.casefold() == config_relative.casefold():
                continue
            target = self._target(game_root, spec.path)
            if self._is_generated_unity_library(spec) and target.is_file():
                continue
            if target.exists() and not self._matches(target, spec):
                raise RuntimeSetupConflict(f"现有 BepInEx 文件不同，未覆盖：{spec.path}")

        self._check_game_stopped(game_exe)
        for spec in self.runtime_files:
            target = self._target(game_root, spec.path)
            if spec.path.casefold() == config_relative.casefold():
                if target.is_file():
                    try:
                        current = target.read_text(encoding="utf-8-sig")
                    except (OSError, UnicodeError) as exception:
                        raise RuntimeSetupConflict("现有 BepInEx 配置无法安全读取。") from exception
                    updated = disable_console(current)
                    if updated != current:
                        self._backup(target, "BepInEx.cfg")
                        self._write_atomic(target, updated.encode("utf-8"))
                else:
                    self._write_atomic(target, contents[spec.path])
                continue
            if not target.exists():
                self._write_atomic(target, contents[spec.path])

        if config_update is not None:
            config, current, updated = config_update
            if current != updated:
                if current is not None:
                    self._backup(config, "BepInEx.cfg")
                self._write_atomic(config, updated.encode("utf-8"))

        bridge_target = self._target(game_root, self.bridge.path)
        if bridge_target.exists() and not self._matches(bridge_target, self.bridge):
            self._backup(bridge_target, "LC2CombatBridge.dll")
        if not self._matches(bridge_target, self.bridge):
            self._write_atomic(bridge_target, bridge_source.read_bytes())
        if self.features is not None:
            feature_target = self._target(game_root, self.features.path)
            if feature_target.exists() and not self._matches(feature_target, self.features):
                self._backup(feature_target, "LC2ToolboxFeatures.dll")
            if not self._matches(feature_target, self.features):
                self._write_atomic(feature_target, feature_source.read_bytes())

        result = self.status()
        if not result.ready:
            raise RuntimeSetupError(f"运行环境安装后未达到就绪状态：{result.detail}")
        return result
