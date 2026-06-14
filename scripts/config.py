"""
配置模块 — 从 JSON 文件加载/保存下载器配置。

TASK_01 — 独立模块，无外部依赖。
"""

from __future__ import annotations

import json
import pathlib
from typing import Any


# ── 自定义异常 ──────────────────────────────────────────────────────────


class ConfigError(Exception):
    """配置操作失败时抛出的异常，附带错误码便于上层处理。"""

    def __init__(self, error_code: str, message: str) -> None:
        self.error_code = error_code
        self.message = message
        super().__init__(f"[{error_code}] {message}")


# ── 默认值 ──────────────────────────────────────────────────────────────

_DEFAULTS: dict[str, Any] = {
    "download_dir": "./downloads",
    "filename_template": "%(title)s.%(ext)s",
    "max_file_size_mb": 4096,
    "proxy": None,
    "cookie_file": None,
    "preferred_container": "mp4",
}

# 字段及其期望的 Python 类型，用于类型校验
_FIELD_TYPES: dict[str, type] = {
    "download_dir": str,
    "filename_template": str,
    "max_file_size_mb": int,
    "proxy": type(None),  # None 也是合法值
    "cookie_file": type(None),
    "preferred_container": str,
}

_NON_NULL_TYPES: dict[str, type] = {
    "download_dir": str,
    "filename_template": str,
    "max_file_size_mb": int,
    "preferred_container": str,
}


# ── Config 类 ───────────────────────────────────────────────────────────


class Config:
    """下载器配置，封装 JSON 文件的读写和字段校验。"""

    def __init__(self) -> None:
        # 用默认值填充所有字段
        self._download_dir: str = _DEFAULTS["download_dir"]
        self._filename_template: str = _DEFAULTS["filename_template"]
        self._max_file_size_mb: int = _DEFAULTS["max_file_size_mb"]
        self._proxy: str | None = _DEFAULTS["proxy"]
        self._cookie_file: str | None = _DEFAULTS["cookie_file"]
        self._preferred_container: str = _DEFAULTS["preferred_container"]

        # 记录加载来源路径，save() 时写回同一文件
        self._path: pathlib.Path | None = None

    # ── 工厂方法 ────────────────────────────────────────────────────────

    @staticmethod
    def load(path: str | None = None) -> "Config":
        """从 JSON 文件加载配置。

        Args:
            path: JSON 文件路径。为 None 时默认取 ``<脚本所在目录>/config.json``。

        Returns:
            填充好数据的 Config 实例。

        Raises:
            ConfigError: JSON 语法错误时抛出。
        """
        if path is not None:
            p = pathlib.Path(path)
        else:
            p = pathlib.Path(__file__).resolve().parent / "config.json"

        config = Config()
        config._path = p

        if not p.exists():
            # 文件不存在 — 纯默认值，不报错
            return config

        try:
            raw = p.read_text(encoding="utf-8")
            data: dict[str, Any] = json.loads(raw)
        except json.JSONDecodeError:
            raise ConfigError(
                "config_parse_error",
                f"{p.name} 格式错误",
            )

        if not isinstance(data, dict):
            # JSON 顶层不是对象 — 当格式错误处理
            raise ConfigError(
                "config_parse_error",
                f"{p.name} 格式错误",
            )

        # 逐字段填充，缺失或类型不匹配则跳过（保持默认值）
        for key, expected in _NON_NULL_TYPES.items():
            if key in data and isinstance(data[key], expected):
                setattr(config, f"_{key}", data[key])

        # 可空字段（proxy / cookie_file）：允许 None 或字符串
        for key in ("proxy", "cookie_file"):
            if key in data:
                val = data[key]
                if val is None or isinstance(val, str):
                    setattr(config, f"_{key}", val)

        return config

    # ── 序列化 ──────────────────────────────────────────────────────────

    def to_dict(self) -> dict[str, Any]:
        """返回可 JSON 序列化的字典。"""
        return {
            "download_dir": self._download_dir,
            "filename_template": self._filename_template,
            "max_file_size_mb": self._max_file_size_mb,
            "proxy": self._proxy,
            "cookie_file": self._cookie_file,
            "preferred_container": self._preferred_container,
        }

    def save(self) -> None:
        """将当前配置写回 JSON 文件。

        Raises:
            ConfigError: 磁盘不可写时抛出。
        """
        path = self._path or (pathlib.Path(__file__).resolve().parent / "config.json")
        self._path = path

        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                json.dumps(self.to_dict(), ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except OSError as exc:
            raise ConfigError(
                "config_write_error",
                f"无法写入 {path.name}：{exc}",
            )

    # ── 属性（含校验 & 路径归一化） ─────────────────────────────────────

    @property
    def download_dir(self) -> str:
        return self._download_dir

    @download_dir.setter
    def download_dir(self, value: str) -> None:
        if not value or not value.strip():
            self._download_dir = _DEFAULTS["download_dir"]
        else:
            self._download_dir = _normalize_path(value)

    @property
    def filename_template(self) -> str:
        return self._filename_template

    @filename_template.setter
    def filename_template(self, value: str) -> None:
        if "%(title)s" not in value or "%(ext)s" not in value:
            value = "%(title)s.%(ext)s"
        self._filename_template = value

    @property
    def max_file_size_mb(self) -> int:
        return self._max_file_size_mb

    @max_file_size_mb.setter
    def max_file_size_mb(self, value: int) -> None:
        self._max_file_size_mb = value

    @property
    def proxy(self) -> str | None:
        return self._proxy

    @proxy.setter
    def proxy(self, value: str | None) -> None:
        self._proxy = value

    @property
    def cookie_file(self) -> str | None:
        return self._cookie_file

    @cookie_file.setter
    def cookie_file(self, value: str | None) -> None:
        self._cookie_file = value

    @property
    def preferred_container(self) -> str:
        return self._preferred_container

    @preferred_container.setter
    def preferred_container(self, value: str) -> None:
        self._preferred_container = value


# ── 工具函数 ────────────────────────────────────────────────────────────


def _normalize_path(path: str) -> str:
    """统一使用正斜杠，Windows 反斜杠自动转换。"""
    return pathlib.Path(path).as_posix()
