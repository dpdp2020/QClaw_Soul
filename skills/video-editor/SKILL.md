---
name: video-editor
description: "视频剪辑合成技能。将片头+标题+多个场景视频+BGM合成为最终成品视频。触发词：剪辑、合成视频、视频合成、assemble video、片头、标题字幕、加BGM、混音、最终输出。适用于豆包视频生成后的后期合成环节。"
---

# Video Editor - 视频剪辑合成

用 ffmpeg 将多个视频片段合成为最终成品：**片头 → 标题 → 场景视频 → BGM**。

## 视频规范

| 项目 | 规范 |
|------|------|
| 分辨率 | 720×1280（9:16竖屏） |
| 帧率 | 30fps |
| 编码 | H.264 + AAC |
| 标题字体 | 字魂241号-秋枫体（已安装于系统） |
| 标题字号 | 70 |
| 标题颜色 | 黄色（yellow） |
| 标题背景 | 黑色半透明（black@0.5） |
| BGM音量 | 35% |
| BGM淡出 | 结束前2秒 |

## 合成结构

```
[片头视频 3s] → [标题 3s] → [Scene1] → [Scene2] → ... → [BGM 35%]
```

- **片头**：默认使用 `intro_3s.mp4`（可自定义路径），不指定则生成黑屏
- **标题时长**：自动匹配片头视频时长（`title_duration=0` 时）
- **场景切换**：硬切（无 xfade 过渡），确保不同帧率素材拼接不丢帧

## 使用方法

### 1. 准备素材

- 场景视频放在 workspace（从豆包下载的 mp4）
- BGM 音乐文件（mp3/wav）
- 标题文字（由 Franco 提供，或从剧本提取）

### 2. 生成配置文件

基于模板创建 config JSON：

```powershell
Copy-Item "D:\wujm\QClaw_data\skills\video-editor\config_template.json" ".\video_config.json"
```

编辑 `video_config.json`，填入实际文件路径和标题：

```json
{
  "scenes": ["D:\\wujm\\QClaw_data\\workspace-doubao-video\\doubao-video-scene1.mp4"],
  "bgm": "D:\\wujm\\QClaw_data\\assets\\bgm\\chill.mp3",
  "title": "今日A股复盘",
  "intro_duration": 3,
  "title_duration": 4,
  "scene_transition": 0.5,
  "bgm_volume": 0.35,
  "output": "final_output.mp4"
}
```

### 3. 执行合成

```powershell
python "D:\wujm\QClaw_data\skills\video-editor\scripts\assemble_video.py" --config ".\video_config.json"
```

### 4. 验证输出

脚本自动输出文件大小和时长。用 ffprobe 详细验证：

```powershell
ffprobe -v error -show_format -show_streams "final_output.mp4"
```

## 参数说明

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `scenes` | 必填 | 场景视频路径数组，按播放顺序排列 |
| `bgm` | 可选 | BGM 文件路径（mp3/wav） |
| `title` | 可选 | 标题文字（留空则跳过标题画面） |
| `intro_video` | 可选 | 片头视频文件路径（mp4），默认用黑屏 |
| `intro_duration` | 3 | 无片头视频时的黑屏时长（秒） |
| `title_duration` | 0(=跟随片头) | 标题展示时长，0=自动匹配片头时长 |
| `scene_transition` | 0.5 | 保留参数（暂无效果，场景切换固定为硬切）|
| `bgm_volume` | 0.35 | BGM 音量（0.0~1.0） |
| `output` | final.mp4 | 输出文件名 |
| `font_size` | 70 | 标题字号 |
| `resolution` | 720x1280 | 输出分辨率 |

## 脚本路径

```
D:\wujm\QClaw_data\skills\video-editor\scripts\assemble_video.py
D:\wujm\QClaw_data\skills\video-editor\config_template.json
```

## 依赖

- **ffmpeg**（PATH 中可用）
- **字魂241号-秋枫体.ttf**（已安装在 `C:\Windows\Fonts\`）
- **Python 3**

## 注意事项

- **帧率统一**：每个视频在拼接前会统一重编码为 30fps，避免混合帧率拼接丢帧（如片头30fps + 场景24fps）
- **关键帧**：每30帧1个关键帧，确保播放器顺畅 seek
- 场景视频可能没有音轨（豆包生成的视频通常是静音），脚本会自动检测并处理
- BGM 会在视频结束前 2 秒淡出，避免突兀截断
- 多个场景间使用硬切（无过渡），确保不同帧率素材拼接不丢帧
- 如果场景视频分辨率不一致，ffmpeg 会自动缩放（建议统一为 720×1280）
- 临时文件会自动清理

## 单步操作（手动 ffmpeg）

如需手动操作，以下是核心 ffmpeg 命令：

- **2026-05-22 修复**：
  1. `concat_videos()`：移除 xfade，改为 fps-normalized 滤镜拼接（`[i:v]fps=30,format=yuv420p` + `concat`），解决混合帧率视频拼接丢帧问题
  2. `add_bgm()`：BGM 加 `atrim=0:video_dur` 限制时长，解决视频时长被截断问题
  3. `generate_title_overlay()`：修复未定义变量 `idx` 的 Bug

### 生成标题画面
```powershell
ffmpeg -y -f lavfi -i "color=c=black:s=720x1280:d=4:r=30" `
  -vf "drawbox=x=0:y=0:w=iw:h=ih:color=black@0.5:t=fill,drawtext=text='标题':fontfile='C\:/Windows/Fonts/字魂241号-秋枫体.ttf':fontsize=70:fontcolor=yellow:x=(w-text_w)/2:y=(h-text_h)/2" `
  -c:v libx264 -pix_fmt yuv420p -r 30 title.mp4
```

### 合并视频 + 加BGM
```powershell
ffmpeg -y -i concat.mp4 -i bgm.mp3 `
  -filter_complex "[1:a]volume=0.35,afade=t=out:st=28:d=2[bgm];[0:a][bgm]amix=inputs=2:duration=first[aout]" `
  -map 0:v -map "[aout]" -c:v copy -c:a aac -b:a 192k -shortest final.mp4
```
