# PRODUCTION.md - 豆子制作流程

## 核心工作流程

### Step 1: 检查剧本

查找: `D:\wujm\QClaw_data\workspace-media-operator\memory\script-done-{YYYY-MM-DD}.md`

不存在则等待10分钟后重试（最多3次）

存在则读取标记文件，从中获取关联剧本路径（通常在 `memory/` 目录下）

### Step 1.5: 片头标题合成

片头视频下载后，需要叠加当天剧本的标题：

1. **读取剧本标题**：从 `video-script-*-{日期}.md` 中提取 `<视频标题>` 字段
2. **复制片头视频**：从本地资产目录复制 `intro_3s.mp4`
   ```
   D:\wujm\QClaw_data\assets\actors\intro_3s.mp4
   ```
3. **PIL 渲染标题叠加图**（绕过 FFmpeg drawtext 的字体度量问题）：
   - 使用 **秋枫体** 字体（`C:\Windows\Fonts\字魂241号-秋枫体.ttf`），fontsize=60
   - **方案A：半透明黑底条 + 黄色文字 + 黑色描边**（2026-05-07 确认采用）
     - 半透明圆角黑底条（fill=(0,0,0,180)，radius=20，padding_x=40，padding_y=30，width=720）
     - 黄色文字 (RGB 255,255,0) + 黑色描边 (3px)
   - **智能分行**：超过 680px 自动拆分，优先在标点处分割
   - **垂直居中**：标题整体在屏幕中央 (Y≈640)
   - 生成透明 PNG overlay
4. **FFmpeg overlay 合成**：
   ```bash
   ffmpeg -i intro_3s.mp4 -i title_overlay.png -filter_complex "[0:v][1:v]overlay=0:0" -c:a copy intro_with_title.mp4
   ```
5. **输出**：`intro_with_title.mp4` 作为最终合成的片头

**标题渲染参数**：
- 视频尺寸：720x1280
- 字体：秋枫体 (字魂241号-秋枫体.ttf)
- 字号：60pt
- 颜色：黄色 (255,255,0)
- 描边：黑色 3px
- 底框：半透明黑色圆角矩形（alpha=180，radius=20，padding_x=40，padding_y=30，width=720）
- 最大行宽：680px
- 行间距：10px
- 垂直位置：屏幕32%处为中心
- 分行优先级：—— > ， > ！ > ？ > 空格

### Step 2: 生成视频

使用 **doubao-video-generator 技能** 通过豆包网页生成视频。

**具体操作：**
1. 读取剧本，确认 Scene 数量
2. 为每个 Scene 执行技能的 6 步流程：
   - Step 0: 读取剧本 .md 文件
   - Step 1: 点击"视频生成"按钮
   - Step 2: 填写脚本（Slate.js API）
   - Step 3: 上传参考图片（按顺序）
   - Step 4: 设置比例 9:16 + 模型 Seedance 2.0 Fast
   - Step 5: 提交生成
   - Step 6: 下载视频
3. 监控各 Scene 生成状态，全部成功后进入 Step 3

**注意事项：**
- 豆包网页生成的视频**已包含配音和字幕**，无需后续 TTS 和字幕烧录步骤
- 参考图按上传顺序自动编号（第1张=参考图1，第2张=参考图2...）
- 每个提示词末尾必须附加反创作指令（见 RULES.md）

### Step 3: 合成完整视频（含片头+正片）

片头视频 `intro_with_title.mp4` 已有静音音轨（intro_3s.mp4 源文件内置 AAC），可直接 concat。

**拼接片头 + 正片**（使用 concat demuxer）：
```bash
# concat_list.txt 内容：
# file 'intro_with_title.mp4'
# file 'main_video.mp4'
ffmpeg -f concat -safe 0 -i concat_list.txt -c copy merged_video.mp4
```
输出：`merged_video.mp4`（片头3s + 正片 = 总时长）

**验证**：确保输出视频和音频时长一致。

### Step 4: 混 BGM（保留原配音）

1. **复制 BGM**：从本地资产目录复制
   ```powershell
   Copy-Item "D:\wujm\QClaw_data\assets\actors\bgm.mp3" -Destination "output/bgm.mp3"
   ```

2. **BGM 混音命令**：
   ```bash
   ffmpeg -i merged_video.mp4 -i output/bgm.mp3 \
     -filter_complex "[1:a]atrim=0:$total_dur,asetpts=PTS-STARTPTS,volume=1.2[bgm];[0:a][bgm]amix=inputs=2:duration=first:dropout_transition=2[aout]" \
     -map 0:v -map "[aout]" -c:v copy final_with_bgm.mp4
   ```
   **说明**：
   - `atrim=0:$total_dur`：将 BGM trim 到视频完整时长
   - `volume=1.2`：BGM 预增强 120%，amix 平均后约 60%

3. **输出**：`final_with_bgm.mp4`

### Step 5: 验证

期望: 720x1280, H264+AAC, 视频时长=音频时长

**角色外观验证**
- 提取视频关键帧（每秒1帧）
- 与参考图对比，确认角色外观一致
- 发现不符立即标记为事故，停止发布

### Step 6: 标记完成

`D:\wujm\QClaw_data\workspace-doubao-video\memory\production-done-{YYYY-MM-DD}.md`

## 音色映射表

| 角色ID | 音色描述 |
|--------|---------|
| sparky_base | 甜美少女声 |
| wei_base | 老年男声 |
| zero_base | 童声 |
| blackie_base | 青年男声 |

## 视觉资产管理

**资产根目录 (本地备份)**: `D:\wujm\QClaw_data\assets\actors\`

| 角色/素材 | 资产ID | 文件名 |
|------------|--------|--------|
| 电闪闪 | sparky_base | sparky_base.png |
| 魏教授 | wei_base | wei_base.png |
| 老黑 | blackie_base | blackie_base.png |
| 小零 | zero_base | zero_base.png |
| 场景参考图 | scene_base | scene.png |

## 工具路径

- doubao-video-generator 技能: `C:\Users\adigle\.qclaw\skills\doubao-video-generator\SKILL.md`
- FFmpeg: `ffmpeg`（系统已安装）
- **统一填入脚本**: `node _fill_doubao.cjs <script-file>`（Slate API + execCommand fallback）
- **清空编辑器**: `node _clear_editor.cjs`
- **标题渲染**: `python _render_title.py`

---
_最后更新：2026-05-14 by 豆子 🫘_
