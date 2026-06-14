"""
环境诊断模块 — 检查 yt-dlp / ffmpeg / 下载目录状态。

TASK_02 — 独立可测模块，依赖 scripts/config.py。
"""

from __future__ import annotations

import os
import pathlib
import platform
import re
import shutil
import subprocess
from typing import Any


def run_doctor(output_dir: str) -> dict[str, Any]:
    """检查环境依赖和磁盘空间，返回诊断结果 dict。

    Args:
        output_dir: 下载目录路径，用于检查目录状态和磁盘空间。

    Returns:
        包含 ``status``、``checks`` 的 dict。status 为 ``"ok"`` /
        ``"warning"`` / ``"error"`` 之一。
    """
    checks: dict[str, Any] = {}
    errors: list[str] = []
    warnings: list[str] = []

    # ── yt-dlp 检查 ─────────────────────────────────────────────────
    yt_info = _check_yt_dlp()
    checks["yt_dlp"] = yt_info

    # ── ffmpeg 检查 ─────────────────────────────────────────────────
    ff_info = _check_ffmpeg()
    checks["ffmpeg"] = ff_info

    # ── 下载目录检查 ─────────────────────────────────────────────────
    dir_info = _check_download_dir(output_dir)
    checks["download_dir"] = dir_info

    # ── 状态判断 ─────────────────────────────────────────────────────
    if not yt_info["available"] or not ff_info["available"]:
        status = "error"
        errors.append("dependency_missing")
    elif not dir_info.get("exists", False) or not dir_info.get("writable", False):
        status = "warning"
    else:
        status = "ok"

    result: dict[str, Any] = {
        "status": status,
        "checks": checks,
    }

    if status != "ok":
        msgs = []
        if not yt_info["available"]:
            msgs.append("缺少 yt-dlp")
        if yt_info["available"] and not ff_info["available"]:
            msgs.append("缺少 ffmpeg，高清视频可能无法合并")
        if not dir_info.get("exists", False):
            msgs.append("下载目录不存在")
        if not dir_info.get("writable", False):
            msgs.append("下载目录不可写，请检查路径权限")
        result["error_code"] = errors[0] if errors else "environment_issue"
        result["error_message"] = "；".join(msgs)

    return result


# ── 内部检查函数 ────────────────────────────────────────────────────────


def _check_yt_dlp() -> dict[str, Any]:
    """检查 yt-dlp 是否可用并获取版本号。"""
    info: dict[str, Any] = {"available": False, "version": None}
    try:
        result = subprocess.run(
            ["yt-dlp", "--version"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode == 0:
            ver = result.stdout.strip()
            if ver:
                info["available"] = True
                info["version"] = ver
    except (FileNotFoundError, subprocess.SubprocessError):
        pass
    return info


def _check_ffmpeg() -> dict[str, Any]:
    """检查 ffmpeg 是否可用并提取版本号。"""
    info: dict[str, Any] = {"available": False, "version": None}
    try:
        result = subprocess.run(
            ["ffmpeg", "-version"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode == 0:
            info["available"] = True
            ver = _extract_ffmpeg_version(result.stdout)
            info["version"] = ver
    except (FileNotFoundError, subprocess.SubprocessError):
        pass
    return info


def _extract_ffmpeg_version(output: str) -> str:
    """从 ffmpeg -version 输出中提取版本号。

    匹配 ``ffmpeg version x.y``、``N-xxxxx`` 或 ``ffmpeg version x`` 格式。
    """
    # 优先匹配 "ffmpeg version x.y.z"
    m = re.search(r"ffmpeg version (\S+)", output)
    if m:
        return m.group(1)
    # 其次匹配编译版号 N-xxxxx
    m = re.search(r"(N-\d+)", output)
    if m:
        return m.group(1)
    return "unknown"


def _check_download_dir(output_dir: str) -> dict[str, Any]:
    """检查下载目录是否存在、可写、剩余空间。"""
    p = pathlib.Path(output_dir).resolve()
    path_str = p.as_posix()

    info: dict[str, Any] = {
        "exists": False,
        "writable": False,
        "path": path_str,
        "free_gb": None,
    }

    if not p.exists():
        return info

    info["exists"] = True

    # 可写性检测：创建临时文件
    test_file = p / ".doctor_write_test"
    try:
        test_file.touch()
        test_file.unlink()
        info["writable"] = True
    except OSError:
        info["writable"] = False
        return info

    # 磁盘剩余空间
    try:
        usage = shutil.disk_usage(p)
        info["free_gb"] = round(usage.free / (1024 ** 3), 1)
    except OSError:
        info["free_gb"] = None

    return info
