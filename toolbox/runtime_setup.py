from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import tempfile
from typing import Callable
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
    if lines and lines[-1]:
        lines.append("")
    if section_index is None:
        lines.append(f"[{CONSOLE_SECTION}]")
    lines.append(f"{CONSOLE_KEY} = false")
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
            if relative.casefold().endswith("bepinex.cfg"):
                try:
                    if console_is_enabled(target.read_text(encoding="utf-8-sig")):
                        return RuntimeSetupStatus("needs_configuration", "需关闭调试控制台")
                except (OSError, UnicodeError):
                    return RuntimeSetupStatus("conflict", "现有 BepInEx 配置无法安全读取")
                continue
            if not self._matches(target, spec):
                return RuntimeSetupStatus("conflict", f"现有运行环境文件不同：{relative}")
        bridge_target = self._target(game_root, self.bridge.path)
        if not bridge_target.exists():
            return RuntimeSetupStatus("missing", "战斗 HUD Bridge 尚未安装")
        if not self._matches(bridge_target, self.bridge):
            return RuntimeSetupStatus("bridge_update", "战斗 HUD Bridge 需要更新")
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

    def install(self) -> RuntimeSetupStatus:
        game_exe = self._game_exe()
        if game_exe is None:
            raise RuntimeSetupError("请先在设置中定位 LostCastle2.exe。")
        if self.game_running_provider(game_exe):
            raise RuntimeSetupGameRunning("请先完全关闭游戏，再初始化运行环境。")
        archive_path = self._bundle_file(self.runtime_archive)
        bridge_source = self._bundle_file(self._bridge_bundle_spec())
        game_root = game_exe.parent
        contents = self._read_runtime_contents(archive_path)

        config_relative = "BepInEx/config/BepInEx.cfg"
        for spec in self.runtime_files:
            if spec.path.casefold() == config_relative.casefold():
                continue
            target = self._target(game_root, spec.path)
            if target.exists() and not self._matches(target, spec):
                raise RuntimeSetupConflict(f"现有 BepInEx 文件不同，未覆盖：{spec.path}")

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

        bridge_target = self._target(game_root, self.bridge.path)
        if bridge_target.exists() and not self._matches(bridge_target, self.bridge):
            self._backup(bridge_target, "LC2CombatBridge.dll")
        if not self._matches(bridge_target, self.bridge):
            self._write_atomic(bridge_target, bridge_source.read_bytes())

        result = self.status()
        if not result.ready:
            raise RuntimeSetupError(f"运行环境安装后未达到就绪状态：{result.detail}")
        return result
