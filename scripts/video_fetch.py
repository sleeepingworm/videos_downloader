"""
CLI 入口 — 视频下载工具的命令行界面。

TASK_05 — 串联 config / doctor / inspect / download 模块。

用法:
    python scripts/video_fetch.py doctor [--output-dir <path>]
    python scripts/video_fetch.py inspect <url> [--output-dir <path>]
    python scripts/video_fetch.py download <url> --format <format_id> [options]
    python scripts/video_fetch.py version
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

# 本项目模块
from scripts.config import Config, ConfigError
from scripts.doctor import run_doctor
from scripts.inspect import inspect_video
from scripts.download import download_video


def main() -> None:
    """CLI 入口。解析参数并派发到对应模块。"""
    parser = _build_parser()
    args = parser.parse_args()

    if not hasattr(args, "command"):
        parser.print_usage(sys.stderr)
        sys.exit(1)

    try:
        result: dict[str, Any] = _dispatch(args)
        sys.stdout.write(json.dumps(result, ensure_ascii=False) + "\n")
        if result.get("status") != "ok":
            sys.exit(1)
    except ConfigError as e:
        err = {
            "status": "error",
            "error_code": e.error_code,
            "error_message": e.message,
        }
        sys.stdout.write(json.dumps(err, ensure_ascii=False) + "\n")
        sys.exit(1)
    except Exception as e:
        err = {
            "status": "error",
            "error_code": "internal_error",
            "error_message": str(e),
        }
        sys.stdout.write(json.dumps(err, ensure_ascii=False) + "\n")
        sys.exit(1)


# ── 参数解析 ────────────────────────────────────────────────────────────


def _build_parser() -> argparse.ArgumentParser:
    """构建 ArgumentParser 及子命令。"""
    parser = argparse.ArgumentParser(
        prog="video_fetch.py",
        description="视频下载工具 — 支持 inspect / download / doctor / version",
    )
    sub = parser.add_subparsers(dest="command")

    # doctor
    doctor_parser = sub.add_parser("doctor", help="检查环境依赖")
    doctor_parser.add_argument(
        "--output-dir",
        help="下载目录（可选，默认从 config 读取）",
    )

    # inspect
    inspect_parser = sub.add_parser("inspect", help="预览视频信息（不下载）")
    inspect_parser.add_argument("url", help="视频 URL")
    inspect_parser.add_argument(
        "--output-dir",
        help="下载目录（可选，默认从 config 读取）",
    )

    # download
    download_parser = sub.add_parser("download", help="下载视频")
    download_parser.add_argument("url", help="视频 URL")
    download_parser.add_argument(
        "--format",
        required=True,
        help="格式 ID（必需），如 137+140",
    )
    download_parser.add_argument(
        "--output-dir",
        help="下载目录（可选，默认从 config 读取）",
    )
    download_parser.add_argument(
        "--filename-template",
        help="文件名模板（可选，默认从 config 读取）",
    )

    # version
    sub.add_parser("version", help="显示版本信息")

    return parser


# ── 派发 ────────────────────────────────────────────────────────────────


def _dispatch(args: argparse.Namespace) -> dict[str, Any]:
    """根据命令派发到对应模块。"""
    # 加载配置
    config = Config.load()

    # 确定 output_dir（命令行优先，否则用 config 的）
    output_dir = _resolve_output_dir(args, config)

    if args.command == "doctor":
        return run_doctor(output_dir)

    if args.command == "inspect":
        return inspect_video(args.url, output_dir)

    if args.command == "download":
        filename_template = args.filename_template or config.filename_template
        return download_video(
            url=args.url,
            format_id=args.format,
            output_dir=output_dir,
            filename_template=filename_template,
        )

    if args.command == "version":
        return _get_version_info()

    # 理论上不会执行到这里
    return {
        "status": "error",
        "error_code": "internal_error",
        "error_message": f"未知命令：{args.command}",
    }


def _resolve_output_dir(args: argparse.Namespace, config: Config) -> str:
    """解析 output_dir：命令行参数优先，否则用配置值。"""
    dir_arg = getattr(args, "output_dir", None)
    if dir_arg:
        return str(Path(dir_arg).resolve().as_posix())
    return str(Path(config.download_dir).resolve().as_posix())


# ── 版本信息 ────────────────────────────────────────────────────────────


def _get_version_info() -> dict[str, Any]:
    """获取版本信息。"""
    yt_ver = _get_yt_dlp_version()
    ff_ver = _get_ffmpeg_version()
    py_ver = sys.version.split()[0]

    return {
        "status": "ok",
        "version": "1.0.0",
        "yt_dlp_version": yt_ver,
        "ffmpeg_version": ff_ver,
        "python_version": py_ver,
    }


def _get_yt_dlp_version() -> str | None:
    """运行 yt-dlp --version 获取版本号。"""
    try:
        result = subprocess.run(
            ["yt-dlp", "--version"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except (FileNotFoundError, subprocess.SubprocessError):
        pass
    return None


def _get_ffmpeg_version() -> str | None:
    """运行 ffmpeg -version 并提取版本号。"""
    try:
        result = subprocess.run(
            ["ffmpeg", "-version"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            m = re.search(r"ffmpeg version (\S+)", result.stdout)
            if m:
                return m.group(1)
            m2 = re.search(r"(N-\d+)", result.stdout)
            if m2:
                return m2.group(1)
            return "unknown"
    except (FileNotFoundError, subprocess.SubprocessError):
        pass
    return None


if __name__ == "__main__":
    main()
