"""
视频预览模块 — 调用 yt-dlp 解析视频元信息，返回格式列表和存储报告。

TASK_03 — 只读不写，不下载任何文件。
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any


def inspect_video(url: str, output_dir: str) -> dict[str, Any]:
    """解析视频 URL，返回视频元信息 JSON。

    Args:
        url: 视频 URL。
        output_dir: 下载目录路径，用于存储空间报告。

    Returns:
        包含 ``status``、``platform``、``title``、``formats``、
        ``storage_report`` 等字段的 dict。
    """
    # ── 第一步：调用 yt-dlp 获取原始 JSON ──────────────────────────
    try:
        proc = subprocess.run(
            [
                "yt-dlp", "--dump-json", "--no-download", "--no-playlist",
                "--add-header", "User-Agent:Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                url,
            ],
            capture_output=True,
            text=True,
            timeout=120,
        )
    except FileNotFoundError:
        return {
            "status": "error",
            "error_code": "inspect_failed",
            "error_message": "未找到 yt-dlp，请先安装",
        }
    except subprocess.TimeoutExpired:
        return {
            "status": "error",
            "error_code": "inspect_failed",
            "error_message": "yt-dlp 超时",
        }

    if proc.returncode != 0:
        return _handle_yt_dlp_error(proc.stderr)

    # ── 第二步：解析 JSON ───────────────────────────────────────────
    try:
        data: dict[str, Any] = json.loads(proc.stdout)
    except json.JSONDecodeError:
        return {
            "status": "error",
            "error_code": "inspect_failed",
            "error_message": "yt-dlp 输出不是合法 JSON",
        }

    # ── 提取元字段 ───────────────────────────────────────────────────
    platform = _detect_platform(data.get("extractor_key", ""))
    title: str = data.get("title", "未知标题")
    uploader: str = data.get("uploader") or data.get("channel") or "未知"
    duration: int = data.get("duration") or 0

    # ── 播放列表检测 ────────────────────────────────────────────────
    playlist_count: int | None = data.get("playlist_count")
    playlist_index = data.get("playlist_index")
    is_playlist: bool = (
        playlist_index is not None
        and playlist_count is not None
        and playlist_count > 1
    )

    # ── 第三步：生成格式列表 ────────────────────────────────────────
    raw_formats: list[dict[str, Any]] = data.get("formats") or []
    formats = _build_format_list(raw_formats)

    # ── 压缩格式列表（超过 8 项时） ─────────────────────────────────
    if len(formats) > 8:
        formats = _compact_formats(formats)

    # ── 第四步：存储空间报告 ────────────────────────────────────────
    storage = _build_storage_report(output_dir, formats)

    return {
        "status": "ok",
        "platform": platform,
        "title": title,
        "uploader": uploader,
        "duration_seconds": duration,
        "is_playlist": is_playlist,
        "playlist_count": playlist_count if is_playlist else None,
        "formats": formats,
        "storage_report": storage,
    }


# ── 错误处理 ────────────────────────────────────────────────────────────


def _handle_yt_dlp_error(stderr: str) -> dict[str, Any]:
    """根据 yt-dlp 的 stderr 判断错误类型。"""
    stderr_lower = stderr.lower()

    if "unsupported url" in stderr_lower or "no video url" in stderr_lower:
        return {
            "status": "error",
            "error_code": "unsupported_url",
            "error_message": "不支持的 URL 格式",
        }
    if "sign in" in stderr_lower or "login" in stderr_lower or "auth" in stderr_lower:
        return {
            "status": "error",
            "error_code": "auth_required",
            "error_message": "需要登录才能访问此视频",
        }
    if "private video" in stderr_lower:
        return {
            "status": "error",
            "error_code": "auth_required",
            "error_message": "视频未公开或需要登录",
        }

    # 截取前 200 字符作为摘要
    summary = stderr.strip()[:200]
    return {
        "status": "error",
        "error_code": "inspect_failed",
        "error_message": f"yt-dlp 返回错误：{summary}",
    }


# ── 平台检测 ────────────────────────────────────────────────────────────


def _detect_platform(extractor_key: str) -> str:
    """将 extractor_key 转为小写并映射到已知平台。"""
    key = extractor_key.lower()
    if "youtube" in key:
        return "youtube"
    return "unknown"


# ── 格式列表生成 ────────────────────────────────────────────────────────


def _build_format_list(raw_formats: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """从 yt-dlp 的 formats 数组筛选并转换格式。"""
    # 先排除 DRM 格式
    clean = [f for f in raw_formats if not f.get("has_drm", False)]

    # 分离视频轨道、音频轨道、完整轨道
    video_tracks: list[dict[str, Any]] = []
    audio_tracks: list[dict[str, Any]] = []
    complete_tracks: list[dict[str, Any]] = []

    for f in clean:
        vcodec = f.get("vcodec", "none")
        acodec = f.get("acodec", "none")
        vcodec_ok = vcodec != "none"
        acodec_ok = acodec != "none"

        if vcodec_ok and acodec_ok:
            # 同时包含音视频
            complete_tracks.append(f)
        elif vcodec_ok:
            video_tracks.append(f)
        elif acodec_ok:
            audio_tracks.append(f)

    # 为 video-only 轨道匹配最佳音频，生成合并格式
    merged: list[dict[str, Any]] = _merge_video_audio(video_tracks, audio_tracks)

    # 转换完整轨道
    converted_complete = [_convert_format(f, requires_merge=False) for f in complete_tracks]

    # 转换纯音频
    converted_audio = [_convert_format(f, requires_merge=False) for f in audio_tracks]

    # 合并结果：完整轨道优先，然后是合并格式，最后是纯音频
    result = converted_complete + merged + converted_audio

    # 按分辨率降序排列（仅音频排在最后）
    def _sort_key(item: dict[str, Any]) -> tuple[int, int]:
        if item.get("resolution"):
            # 解析分辨率数字做排序
            parts = item["resolution"].split("x")
            if len(parts) == 2:
                try:
                    return (0, -int(parts[1]))
                except ValueError:
                    pass
        return (1, 0)

    result.sort(key=_sort_key)
    return result


def _merge_video_audio(
    video_tracks: list[dict[str, Any]],
    audio_tracks: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """为每个视频轨道匹配最佳音频，生成需要合并的格式项。"""
    if not video_tracks or not audio_tracks:
        return []

    # 找到最佳音频（最高码率）
    best_audio = max(audio_tracks, key=lambda a: a.get("abr", 0) or 0)

    merged_list: list[dict[str, Any]] = []
    for v in video_tracks:
        vid = v.get("format_id", "")
        aid = best_audio.get("format_id", "")
        format_id = f"{vid}+{aid}"

        # 估算大小
        v_size = _get_size_mb(v)
        a_size = _get_size_mb(best_audio)
        estimated = None
        if v_size is not None and a_size is not None:
            estimated = round(v_size + a_size, 1)
        elif v_size is not None:
            estimated = v_size

        width = v.get("width")
        height = v.get("height")
        resolution = f"{width}x{height}" if width and height else None
        fps = v.get("fps")

        label = _build_label(v, best_audio)

        merged_list.append({
            "format_id": format_id,
            "label": label,
            "resolution": resolution,
            "container": "mp4",
            "fps": fps,
            "audio": True,
            "requires_merge": True,
            "estimated_size_mb": estimated,
        })

    return merged_list


def _convert_format(
    f: dict[str, Any],
    requires_merge: bool,
) -> dict[str, Any]:
    """将 yt-dlp 的单条 format 转换为标准输出结构。"""
    format_id: str = f.get("format_id", "")
    vcodec = f.get("vcodec", "none")
    acodec = f.get("acodec", "none")
    is_video = vcodec != "none"
    is_audio_only = vcodec == "none" and acodec != "none"

    width = f.get("width")
    height = f.get("height")
    resolution = f"{width}x{height}" if width and height else None
    container: str = f.get("ext", "mp4")
    fps = f.get("fps")

    has_audio = acodec != "none"
    estimated = _get_size_mb(f)

    label = _label_from_fields(f, is_audio_only, is_video, resolution, container)

    return {
        "format_id": format_id,
        "label": label,
        "resolution": resolution,
        "container": container,
        "fps": fps,
        "audio": has_audio,
        "requires_merge": requires_merge,
        "estimated_size_mb": estimated,
    }


def _get_size_mb(f: dict[str, Any]) -> float | None:
    """从 filesize 或 filesize_approx 获取 MB 值。"""
    size = f.get("filesize") or f.get("filesize_approx")
    if size is not None and size > 0:
        return round(size / (1024 * 1024), 1)
    return None


def _build_label(video: dict[str, Any], audio: dict[str, Any]) -> str:
    """为音视频合并格式生成可读标签。"""
    width = video.get("width")
    height = video.get("height")

    if width and height:
        quality = f"{height}p"
        if height >= 2160:
            quality = f"最高质量 ({height}p, mp4)"
        elif height >= 1080:
            quality = f"最高质量 ({height}p, mp4)"
        else:
            quality = f"{quality} (mp4)"
    else:
        quality = "视频 (mp4)"

    return quality


def _label_from_fields(
    f: dict[str, Any],
    is_audio_only: bool,
    is_video: bool,
    resolution: str | None,
    container: str,
) -> str:
    """根据字段生成格式标签。"""
    if is_audio_only:
        return f"仅音频 ({container})"

    if resolution:
        height_match = re.search(r"x(\d+)", resolution)
        if height_match:
            h = int(height_match.group(1))
            if h >= 2160:
                return f"最高质量 ({h}p, {container})"
            return f"{h}p ({container})"

    return f"视频 ({container})"


# ── 格式压缩 ────────────────────────────────────────────────────────────


def _compact_formats(formats: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """将格式列表压缩到 5 项以内。

    保留策略：
    - 分辨率最高的 3 个
    - 分辨率最低的 1 个
    - 纯音频的 1 个（如果存在）
    - 同类别内取 requires_merge = false 优先，或文件最小优先
    """
    # 分离音频格式
    audio = [f for f in formats if f.get("resolution") is None and f.get("audio")]
    video = [f for f in formats if f.get("resolution") is not None]

    # 按分辨率降序排列
    def _res_height(f: dict[str, Any]) -> int:
        res = f.get("resolution")
        if res:
            m = re.search(r"x(\d+)", res)
            if m:
                return int(m.group(1))
        return 0

    video.sort(key=_res_height, reverse=True)

    selected: list[dict[str, Any]] = []

    # 最高分辨率 3 个（合并优先取 requires_merge=false）
    top3 = video[:3]
    for t in top3:
        selected.append(t)

    # 最低分辨率 1 个（跳过已选的）
    remaining_video = [v for v in video if v not in selected]
    if remaining_video:
        remaining_video.sort(key=_res_height)
        selected.append(remaining_video[0])

    # 纯音频 1 个
    if audio:
        selected.append(audio[0])

    return selected


# ── 存储空间报告 ────────────────────────────────────────────────────────


def _build_storage_report(
    output_dir: str,
    formats: list[dict[str, Any]],
) -> dict[str, Any]:
    """生成存储空间报告。"""
    p = Path(output_dir).resolve()
    path_str = p.as_posix()

    report: dict[str, Any] = {
        "output_dir": path_str,
        "free_gb": None,
        "required_gb": None,
        "safe_to_download": False,
    }

    if not p.exists():
        report["safe_to_download"] = False
        return report

    # 剩余空间
    try:
        usage = shutil.disk_usage(p)
        report["free_gb"] = round(usage.free / (1024 ** 3), 1)
    except OSError:
        pass

    # 所需空间 = formats 中最大的 estimated_size_mb
    sizes = [f["estimated_size_mb"] for f in formats if f["estimated_size_mb"] is not None]
    if sizes:
        max_mb = max(sizes)
        report["required_gb"] = round(max_mb / 1024, 3)
    else:
        report["required_gb"] = None

    # 安全性判断
    if report["free_gb"] is not None and report["required_gb"] is not None:
        report["safe_to_download"] = report["free_gb"] >= report["required_gb"]
    elif report["free_gb"] is not None:
        # 有剩余空间但大小未知
        report["safe_to_download"] = "unknown"
    else:
        report["safe_to_download"] = False

    return report
