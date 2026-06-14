@echo off
chcp 65001 >nul
title 视频下载 Agent Skill 安装脚本
echo ============================================
echo  视频下载 Agent Skill — 环境安装
echo ============================================
echo.

REM ---- 1. 安装 yt-dlp ----
echo [1/3] 检查 yt-dlp ...
python -c "import yt_dlp" 2>nul
if %errorlevel% neq 0 (
    echo 正在安装 yt-dlp ...
    pip install yt-dlp
    if %errorlevel% neq 0 (
        echo 安装 yt-dlp 失败，请确认 Python 和 pip 已安装。
        pause
        exit /b 1
    )
) else (
    echo yt-dlp 已安装。
)
echo.

REM ---- 2. 安装 ffmpeg ----
echo [2/3] 检查 ffmpeg ...
ffmpeg -version >nul 2>nul
if %errorlevel% neq 0 (
    echo ffmpeg 未安装，正在下载 ...
    set FFMPEG_URL=https://github.com/GyanD/codexffmpeg/releases/download/8.1.1/ffmpeg-8.1.1-essentials_build.zip
    set FFMPEG_ZIP=%TEMP%\ffmpeg.zip
    set FFMPEG_DIR=%LOCALAPPDATA%\ffmpeg

    curl.exe -L -o "%FFMPEG_ZIP%" "%FFMPEG_URL%"
    if %errorlevel% neq 0 (
        echo 下载 ffmpeg 失败，请检查网络连接或代理设置。
        pause
        exit /b 1
    )

    powershell -Command "Expand-Archive -Path '%FFMPEG_ZIP%' -DestinationPath '%FFMPEG_DIR%\temp' -Force"
    del "%FFMPEG_ZIP%"

    set BIN_PATH=%FFMPEG_DIR%\temp\ffmpeg-8.1.1-essentials_build\bin
    for /f "skip=2 tokens=3*" %%a in ('reg query "HKCU\Environment" /v Path 2^>nul') do set USER_PATH=%%a %%b
    if "%USER_PATH%"=="" set USER_PATH=%PATH%
    echo %USER_PATH% | findstr /C:"%BIN_PATH%" >nul
    if %errorlevel% neq 0 (
        setx PATH "%USER_PATH%;%BIN_PATH%"
        echo ffmpeg 已安装，请重启终端让路径生效。
    )
) else (
    echo ffmpeg 已安装。
)
echo.

REM ---- 3. 配置 Cursor Skill ----
echo [3/3] 配置 Cursor Skill ...
if exist ".cursor\skills\video-download-agent-skill" (
    copy /Y "SKILL.md" ".cursor\skills\video-download-agent-skill\SKILL.md" >nul
    echo Cursor Skill 已更新。
) else (
    mkdir ".cursor\skills\video-download-agent-skill" 2>nul
    copy /Y "SKILL.md" ".cursor\skills\video-download-agent-skill\SKILL.md" >nul
    echo Cursor Skill 已安装。
)
echo.

echo ============================================
echo  安装完成！
echo.
echo  现在你可以：
echo  1. 在 Cursor 中给 Agent 一个视频 URL
echo  2. 或者手动运行：
echo     python -m scripts.video_fetch inspect ^<URL^>
echo     python -m scripts.video_fetch download ^<URL^> --format ^<format_id^>
echo ============================================
pause