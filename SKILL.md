---
name: video-download-agent-skill
description: >
  Downloads videos from YouTube given a URL. Before downloading,
  inspects the video to list available quality options and estimated file sizes,
  checks disk space, and asks the user to confirm. Use when the user provides a
  video URL and wants to download it.
---

# 视频下载 Agent Skill

## 触发场景

- 用户提供了一个 YouTube URL，并表达了下载意图。
- 用户说"下载这个视频""保存这个视频""把这个视频存下来"等。
- 注意：不要对非视频 URL 误触发。

## 交互流程

1. **识别任务**：判断 URL 是否属于 YouTube 或其他支持平台。如果不支持，直接告知用户。
2. **调用 helper inspect**：运行 `python scripts/video_fetch.py inspect <url>`，获取 JSON 格式的视频元信息。
3. **展示下载计划**：用可读的方式向用户展示以下信息：
   - 视频标题
   - 平台
   - 时长（格式化为 HH:MM:SS 或 MM:SS）
   - 目标保存目录
   - 磁盘剩余空间
   - 候选质量列表（最多 5 个选项：最高质量 / 1080p / 720p / 省空间 / 仅音频）
   - 每个质量的：分辨率、容器、预计大小
4. **询问确认**：提供质量选项让用户选择，或取消下载。选项必须清晰标注每个选择的代价（文件大小、是否需要合并）。
5. **调用 helper download**：用户确认后，运行 `python scripts/video_fetch.py download <url> --format <format_id> --output-dir <path>`。
6. **展示结果**：下载完成后，告知用户保存路径和实际文件大小。

## 关键规则

- **绝不能静默下载**。任何下载动作前都必须展示信息并等待用户确认。
- **绝不能批量下载播放列表**。如果检测到多 P 或播放列表，先询问用户是下载单集、整个列表，还是取消。
- **磁盘空间不足时不能继续**。如果 helper 返回 `status: storage_insufficient`，必须告知用户并建议换目录或选更低质量。
- **辅助文件只输出 JSON**。千万不要试图解析辅助文件的人类可读输出。所有结构化数据都通过 JSON 返回。
- **不要透露 cookie**。cookie 配置只由用户主动提供。

## 错误处理

- 如果辅助返回 `unsupported_url`：告知用户该 URL 不在支持范围内。
- 如果辅助返回 `dependency_missing`：告知用户缺少哪些依赖，给出安装命令示例。
- 如果辅助返回 `auth_required`：告知用户此视频需要登录，当前版本不支持。
- 如果辅助返回 `download_failed`：展示错误摘要，不自动重试。

## 示例

```
用户: 帮我下载这个视频 https://www.youtube.com/watch?v=dQw4w9WgXcQ
Agent: 正在解析视频信息...

标题: Rick Astley - Never Gonna Give You Up
平台: YouTube
时长: 03:32
保存到: C:/Users/icos/Downloads/videos
磁盘剩余: 120 GB

可选质量:
  [1] 最高质量 (1080p, mp4, 约 52 MB)  *推荐
  [2] 720p (mp4, 约 31 MB)
  [3] 省空间 (360p, mp4, 约 10 MB)
  [4] 仅音频 (m4a, 约 4 MB)
  [5] 取消

请选择质量 (1-5):
```