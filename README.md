# 视频下载 Agent Skill

通过 Cursor Agent 下载 YouTube 上公开视频的工具集。

## 快速开始

### 方式一：让 Agent 自动安装（推荐）

把项目 GitHub 链接发给你的 Agent：

```
帮我下载这个项目并安装 https://github.com/sleeepingworm/videos_downloader
然后下载这个视频 https://www.youtube.com/watch?v=xxxxx
```

Agent 会自动 clone 项目、安装依赖、下载视频。

### 方式二：手动安装后使用

```bash
# 1. git clone https://github.com/sleeepingworm/videos_downloader
# 2. 双击 install.bat — 自动安装 yt-dlp 和 ffmpeg
# 3. 重启终端
# 4. 在 Cursor 中给 Agent 一个视频 URL
```

详细步骤见下方 [安装](#安装) 和 [使用](#使用)。

## 功能

- 给定一个视频 URL，解析出标题、时长、可用清晰度和预计文件大小。
- 展示磁盘剩余空间，询问用户选择质量。
- 用户确认后执行下载，返回保存路径和实际大小。

## 安装

### 依赖（只需安装一次）

- Python 3.10+
- yt-dlp（视频解析和下载）
- ffmpeg（音视频合并）

ffmpeg 和 yt-dlp 都是装到你电脑系统里的。换用 Cursor / Claude Code / Roo Code 等任何 agent 都不需要重新安装。

### Windows 一键安装

1. 下载本项目（`git clone https://github.com/sleeepingworm/videos_downloader`）
2. 进入项目目录，**双击 `install.bat`**
3. 脚本会自动完成：安装 yt-dlp、下载 ffmpeg 并加入 PATH、配置 Cursor Skill
4. **重启终端**让 ffmpeg 路径生效

### 手动安装

```bash
pip install yt-dlp
```

ffmpeg 从 https://ffmpeg.org/download.html 下载，把 `bin/` 目录加入系统 PATH。

### 代理

如果无法直接访问外网，需要设置 HTTP 代理环境变量（具体地址和端口请咨询你的网络管理员）。

## 使用

### 方式一：通过 Cursor Agent（推荐）

在 Cursor 中给 Agent 一个视频 URL：

```
帮我下载这个视频 https://www.youtube.com/watch?v=xxxxx
```

Agent 会自动：
1. 解析视频信息（标题、时长、可选质量、预计大小）
2. 展示磁盘剩余空间
3. 询问你选择质量
4. 你确认后开始下载

### 方式二：手动命令行

```bash
cd 项目目录
python -m scripts.video_fetch inspect <视频URL>
python -m scripts.video_fetch download <视频URL> --format <format_id>
```

先用 `inspect` 查看可选质量，从返回的列表里选一个 `format_id`，再传给 `download`。

## 下载目录

- 默认保存在项目下的 `downloads/` 文件夹
- 想换目录时对 Agent 说：**"保存到 D:/videos"** 或 **"换个目录"**

## 限制

- 只支持公开视频，不支持需要登录的内容。
- 大小估算是近似值，最终以下载后实际大小为准。
- 当前不支持播放列表自动下载（必须先询问用户）。