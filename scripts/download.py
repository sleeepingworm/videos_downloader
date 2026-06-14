"""
下载执行模块 — 调用 yt-dlp 执行真实下载。

TASK_04 — 依赖 yt-dlp、ffmpeg 外部工具。
"""

from __future__ import annotations

import os
import pathlib
import shutil
import subprocess
from typing import Any


def download_video(
    url: str,
    format_id: str,
    output_dir: str,
    filename_template: str = "{title}.{ext}",
    duration_seconds: int | None = None,
) -> dict[str, Any]:
    """执行视频下载，返回下载结果 JSON。

    Args:
        url: 视频 URL。
        format_id: yt-dlp 格式标识符，如 ``"137+140"``。
        output_dir: 输出目录路径。
        filename_template: 文件名模板，默认 ``"{title}.{ext}"``。
        duration_seconds: 可选的视频时长，来自 inspect 结果。

    Returns:
        包含 ``status``、``file_path``、``actual_size_mb`` 等的 dict。
    """
    # ── 第一步：前置检查 ────────────────────────────────────────────
    out_path = pathlib.Path(output_dir).resolve()

    # 自动创建目录
    try:
        out_path.mkdir(parents=True, exist_ok=True)
    except OSError:
        return {
            "status": "error",
            "error_code": "storage_insufficient",
            "error_message": "输出目录不可写",
            "details": {},
        }

    # 检查目录是否可写
    if not os.access(str(out_path), os.W_OK):
        return {
            "status": "error",
            "error_code": "storage_insufficient",
            "error_message": "输出目录不可写",
            "details": {},
        }

    # 检查磁盘剩余空间
    try:
        usage = shutil.disk_usage(out_path)
        free_bytes = usage.free
        free_mb = free_bytes / (1024 * 1024)
        if free_mb < 50:
            return {
                "status": "error",
                "error_code": "storage_insufficient",
                "error_message": f"磁盘剩余空间不足（{free_mb:.1f} MB），需要至少 50 MB",
                "details": {},
            }
    except OSError:
        pass  # 无法获取磁盘信息时放行，让 yt-dlp 自己报错

    # 如果 format_id 包含 "+"（需要合并），检查 ffmpeg
    if "+" in format_id:
        if not _check_ffmpeg_available():
            return {
                "status": "error",
                "error_code": "dependency_missing",
                "error_message": "所选格式需要 ffmpeg 合并音视频，但本机未安装 ffmpeg",
                "details": {},
            }

    # ── 第二步：执行下载 ────────────────────────────────────────────
    output_template = str(out_path / filename_template)

    cmd = [
        "yt-dlp",
        "-f", format_id,
        "-o", output_template,
        "--no-playlist",
        "--no-overwrites",
        "--merge-output-format", "mp4",
        "--add-header", "User-Agent:Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        url,
    ]

    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=3600,  # 1 小时超时
        )
    except FileNotFoundError:
        return {
            "status": "error",
            "error_code": "download_failed",
            "error_message": "未找到 yt-dlp，请先安装",
            "details": {},
        }
    except subprocess.TimeoutExpired:
        return {
            "status": "error",
            "error_code": "download_failed",
            "error_message": "下载超时（超过 1 小时）",
            "details": {},
        }

    if proc.returncode != 0:
        error_summary = proc.stderr.strip()[:200]
        return {
            "status": "error",
            "error_code": "download_failed",
            "error_message": f"yt-dlp 返回错误：{error_summary}",
            "details": {"stderr": proc.stderr.strip()},
        }

    # ── 第三步：解析结果 ────────────────────────────────────────────
    # 扫描输出目录，按修改时间排序，取最新文件
    try:
        files = sorted(out_path.iterdir(), key=lambda f: f.stat().st_mtime, reverse=True)
        if not files:
            return {
                "status": "error",
                "error_code": "download_failed",
                "error_message": "下载完成后未找到文件",
                "details": {},
            }
        file_path_clean = files[0]
    except OSError:
        return {
            "status": "error",
            "error_code": "download_failed",
            "error_message": "无法读取输出目录",
            "details": {},
        }

    if not file_path_clean.is_file():
        return {
            "status": "error",
            "error_code": "download_failed",
            "error_message": "下载完成后未找到文件",
            "details": {},
        }

    actual_bytes = file_path_clean.stat().st_size
    if actual_bytes == 0:
        return {
            "status": "error",
            "error_code": "download_failed",
            "error_message": "下载文件为空",
            "details": {},
        }

    actual_size_mb = round(actual_bytes / (1024 * 1024), 1)

    return {
        "status": "ok",
        "file_path": file_path_clean.as_posix(),
        "actual_size_mb": actual_size_mb,
        "duration_seconds": duration_seconds,
        "warnings": [],
    }


# ── 工具函数 ────────────────────────────────────────────────────────────


def _check_ffmpeg_available() -> bool:
    """检查本机是否安装了 ffmpeg。"""
    try:
        result = subprocess.run(
            ["ffmpeg", "-version"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.SubprocessError):
        return False
