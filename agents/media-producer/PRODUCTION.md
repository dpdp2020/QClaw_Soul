# PRODUCTION.md - 阿制制作流程

## 核心工作流程

### Step 1: 检查剧本

查找: `D:\wujm\QClaw\data\workspace-media-operator\memory\script-done-{YYYY-MM-DD}.md`

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
   - 使用 **秋枫体** 字体（`C:\Windows\Fonts\字魂241号-秋枫体.ttf`），fontsize=60（70pt时长标题会撑满屏幕，60pt左右各50px边距，视觉居中）
   - **方案A：半透明黑底条 + 黄色文字 + 黑色描边**（2026-05-07 确认采用）
     - 半透明圆角黑底条（fill=(0,0,0,180)，radius=20，padding=40x30）
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
- 字号：60pt（⚠️ 70pt时最长标题会撑满720px屏幕，改为60pt）
- 颜色：黄色 (255,255,0)
- 描边：黑色 3px
- 底框：半透明黑色圆角矩形（alpha=180，radius=20，padding_x=40，padding_y=30），宽度随最宽行自适应
- 最大行宽：680px
- 行间距：10px
- 垂直位置：屏幕32%处为中心（`int(VIDEO_H * 0.32) - box_h // 2`），避开下半部演播台
- 分行优先级：—— > ， > ！ > ？ > 空格

### Step 2: 生成视频（Seedance）

**所有 Scene 同时并行提交 API，无需等待上一场景完成。**

具体操作：
1. 读取剧本，确认 Scene 数量
2. **使用 PROMPT_TEMPLATE.md 模板构造提示词**（禁止自行添加描述）
3. 运行 `prompt_validator.py` 校验提示词合法性
4. 为每个 Scene 构造独立的 API payload（包含各自的角色参考图）
5. **再次校验**：确认 scene.png 已包含，所有URL有效
6. 所有 Scene 的 API 调用同时发出
7. 监控各 Scene 状态，全部成功后进入 Step 3

参数:
- model: `doubao-seedance-1-5-pro-251215` 或 `doubao-seedance-2-0-fast-260128`
- ratio: 9:16
- duration: 12
- resolution: 720p
- generate_audio: true（默认，必须开启）

**generate_audio 参数说明**:
- `true`（默认）：自动生成配音（旁白+环境音+背景音乐），**视频直接含配音，无需TTS步骤**
- `false`: 只生成无声视频

**提示词格式**：

台词格式：`角色名用[音色描述]说："台词内容"`

音色对照：
- 电闪闪：甜美少女声
- 魏教授：老年男声
- 小零：童声
- 老黑：青年男声

示例：
- 电闪闪用甜美少女声说："今日A股上涨，沪指涨超1%"
- 魏教授用老年男声说："市场机会均等，但系统有缺陷"
- 小零用童声说："我学到了一个新知识"
- 老黑用青年男声说："我来补充一下数据"

禁止Mick出镜。

**全能参考模式（多角色/多素材）**：
使用 content 数组 + 图片URL，角色台词写入 text 字段，格式：`用[音色描述]说：'台词内容'，talking, speaking, lips moving`

**generate_audio=true 时**：
> 配音跟随视频自动生成，直接跳到 Step 3

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

**验证**：确保输出视频和音频时长一致（均为 `总时长` 秒）。

### Step 4: 混 BGM（保留原配音）

1. **复制 BGM**：从本地资产目录复制
   ```powershell
   Copy-Item "D:\wujm\QClaw_data\assets\actors\bgm.mp3" -Destination "output/bgm.mp3"
   ```

2. **BGM 混音命令**（✅ 修复版，禁止用旧版 volume=0.2）：
   ```bash
   # 获取视频总时长（用于 trim BGM）
   # 假设视频总时长 = $total_dur（如 27.1）

   ffmpeg -i merged_video.mp4 -i output/bgm.mp3 \
     -filter_complex "[1:a]atrim=0:$total_dur,asetpts=PTS-STARTPTS,volume=1.2[bgm];[0:a][bgm]amix=inputs=2:duration=first:dropout_transition=2[aout]" \
     -map 0:v -map "[aout]" -c:v copy final_with_bgm.mp4
   ```
   **说明**：
   - `atrim=0:$total_dur`：将 BGM trim 到视频完整时长，防止截断
   - `volume=1.2`：BGM 预增强 120%，amix 平均后约 60%，清晰可闻
   - **禁止**用 `volume=0.2`（太小，BGM几乎听不见）
   - **禁止**用 `volume=1.5` 于 amix 输出端（部分 ffmpeg 版本不支持）
   - 若 ffmpeg 版本支持，可在 amix 后加 `,volume=1.5`

3. **输出**：`final_with_bgm.mp4`

### Step 5: 烧录字幕

**从剧本提取字幕时间轴**：
- 格式：`>> [字幕文本]` → 对应一句台词
- Scene 内按顺序分配时间（片头3秒后开始）

**生成 SRT**：
```python
# 时间轴 = 片头时长(3s) + 正片内偏移
# 每个 Scene 的台词均分正片时长
import datetime
def ts(seconds):
    td = datetime.timedelta(seconds=seconds)
    return f"{td.seconds//3600:02d}:{(td.seconds%3600)//60:02d}:{td.seconds%60:02d},{int((seconds-int(seconds))*1000):03d}"
```

**ASS 字幕样式**：
- Fontsize=28
- PrimaryColour=&H00FFFFFF (白字)
- OutlineColour=&H00000000 (黑边)
- BackColour=透明
- BorderStyle=1, Outline=2
- Alignment=2 (居中底部)
- MarginV=300（距底部300像素，2026-05-07 更新）
- PlayResX=720, PlayResY=1280

**字幕烧录参数**:
- Fontsize=28（ASS），白字黑边，居中底部
- MarginV=300（距底部300像素）
- 视频尺寸：720x1280

**烧录**（⚠️ 从 C:\tmp 执行规避 Windows 路径 bug）：
```python
import shutil, subprocess, os
tmp = r"C:\tmp"
os.makedirs(tmp, exist_ok=True)
shutil.copy2("final_with_bgm.mp4", os.path.join(tmp, "final_with_bgm.mp4"))
# 生成 ASS 后保存到 tmp/subs.ass
cmd = ["ffmpeg", "-y", "-i", "final_with_bgm.mp4", "-vf", "ass=subs.ass",
       "-c:v", "libx264", "-preset", "fast", "-crf", "23", "-c:a", "copy", "final_with_subtitle.mp4"]
subprocess.run(cmd, cwd=tmp)
shutil.copy2(os.path.join(tmp, "final_with_subtitle.mp4"), "final_with_subtitle.mp4")
```

### Step 5: 验证

期望: 720x1280, H264+AAC, 视频时长=音频时长

**新增：角色外观验证**
- 提取视频关键帧（每秒1帧）
- 与参考图对比，确认角色外观一致
- 发现不符立即标记为事故，停止发布

### Step 7: 标记完成

`D:\wujm\QClaw\data\workspace-media-producer\memory\production-done-{YYYY-MM-DD}.md`

## 音色映射表

| 角色ID | 音色ID |
|--------|--------|
| sparky_base | zh_female_tianmeitaozi_uranus_bigtts |
| wei_base | zh_male_ruyaqingnian_uranus_bigtts |
| zero_base | zh_female_yingtaowanzi_uranus_bigtts |
| blackie_base | zh_male_aojiaobazong_uranus_bigtts |
| mick_base | zh_male_huolixiaoge_uranus_bigtts |

## 视觉资产管理

**资产根目录 (本地备份)**: `D:\wujm\QClaw\data\actors\`

**API 引用路径 (公网 CDN)**: `https://raw.githubusercontent.com/dpdp2020/QClaw_Soul/main/assets/`

| 角色/素材 | 资产ID | 文件名 | API URL |
|------------|--------|--------|---------|
| 电闪闪 | sparky_base | actors/sparky_base.png | `https://raw.githubusercontent.com/dpdp2020/QClaw_Soul/main/assets/actors/sparky_base.png` |
| 魏教授 | wei_base | actors/wei_base.png | `https://raw.githubusercontent.com/dpdp2020/QClaw_Soul/main/assets/actors/wei_base.png` |
| 老黑 | blackie_base | actors/blackie_base.png | `https://raw.githubusercontent.com/dpdp2020/QClaw_Soul/main/assets/actors/blackie_base.png` |
| 小零 | zero_base | actors/zero_base.png | `https://raw.githubusercontent.com/dpdp2020/QClaw_Soul/main/assets/actors/zero_base.png` |
| 场景参考图 | scene_base | scene.png | `https://raw.githubusercontent.com/dpdp2020/QClaw_Soul/main/assets/actors/scene.png` |

## 工具路径

- Seedance: `skills/seedance-video-generation/seedance.py`
- FFmpeg: `ffmpeg`（系统已安装）
- TTS工具: 已废弃，Seedance 自动配音

## 全能参考模式 (Seedance 2.0)

当需要精确控制角色形象、动作、运镜或音频节奏时，使用 content 数组 + URL 上传素材。

### 素材要求

| 类型 | 格式 | 数量上限 | 单个限制 | 用途 |
|------|------|---------|---------|------|------|
| 图片 | JPG, PNG | 9张 | ≤30MB/张 | 角色外貌、场景参考 |
| 视频 | MP4, MOV (H.264) | 3个 | 2~15秒, ≤50MB | 运镜风格、动作参考 |
| 音频 | MP3 (≥44.1kHz) | 3个 | 总时长≤15秒, ≤15MB | 背景音乐、鼓点节奏控制动作 |

### API 使用方式（全能参考模式）

```json
{
  "model": "doubao-seedance-2-0-fast-260128",
  "content": [
    {
      "type": "text",
      "text": "场景描述。电闪闪外貌参考@image1，用甜美少女声说：'台词'，talking, speaking, lips moving。9:16竖屏，固定机位，static camera。"
    },
    {
      "type": "image_url",
      "image_url": {"url": "https://raw.githubusercontent.com/dpdp2020/QClaw_Soul/main/assets/actors/sparky_base.png"},
      "role": "reference_image"
    },
    {
      "type": "image_url",
      "image_url": {"url": "https://raw.githubusercontent.com/dpdp2020/QClaw_Soul/main/assets/actors/zero_base.png"},
      "role": "reference_image"
    }
  ],
  "duration": 12,
  "resolution": "720p",
  "ratio": "9:16",
  "generate_audio": true
}
```

### 关键规则

1. **台词写在 text 字段**：用 `说：'台词'` 驱动自动配音，多段台词连续写
2. **generate_audio 必为 true**：配音自动生成，无需独立TTS步骤
3. **角色说话需加口型提示**：提示词包含 `talking, speaking, lips moving`
4. **固定机位提示**：提示词包含 `static camera, fixed shot`
5. **URL 是硬性要求**：必须用公网链接，不能用本地路径
6. **content 顺序**：text → image → video → audio
7. **@ 引用编号**：从 1 开始（@image1, @video1, @audio1）
8. **提示词要明确用途**：注明"外表参考"、"运镜模仿"、"节拍同步"等
9. **image_url 必须带 role**：每张图片传入时必须标注 `"role": "reference_image"`，禁止省略
10. **禁用 first_frame**：禁止传 `role: first_frame`，禁止使用 `last_frame_url`，禁止任何形式的场景间串行依赖
11. **禁止添加剧本外���述**：禁止添加服装、外貌、性格等剧本未明确的描述（详见 RULES.md）
12. **必须使用安全模板**：角色描述使用 PROMPT_TEMPLATE.md 中的标准写法
13. **反创作指令（必须）**：每个Scene提示词末尾**必须**附加以下指令，防止Seedance自行添加画面元素：
    ```
    No text overlays, No date stamp, No scrolling ticker, No news lower third, No channel logo, No on-screen text except character dialogue, Clean frame
    ```
    这条规则优先级最高，违反即事故（详见 RULES.md 4.2）

### 场景布局规范（scene.png 固定布局）

scene.png 场景固定提供财经演播室空间，布局不得修改。

| 规则 | 说明 |
|------|------|
| **主播位** | 左下角已有办公桌区域，主角坐/站在此处 |
| **评论员位** | 从侧面进出，不占用主播位 |
| **禁止行为** | ⛔ 不得添加/移动陈设<br>⛔ 不得改变空间布局<br>⛔ 不得坐在弧形台 |
| **主角分配** | 主角由剧情决定，不预设电闪闪站主播位 |
| **首帧参考图** | ⚠️ 已禁用，不得使用 scene.png 作为首帧参考图，纯由 prompt 控制背景生成 |

### 场景应用

- 角色一致性：上传角色定妆照作为 @imageN（台词角色的 reference_image）
- 场景环境参考：上传 scene.png 作为 @imageN���作为场景空间背景参考（财经演播室布局，左下角主播位，评论员从侧面进出，不得坐在弧形台）
- 动作参考：上传动作视频作为 @video1
- 音频驱动动作：音频鼓点可作为动作时间轴参考

**scene.png 使用规则**：
- 每个 Scene 的 content 数组中，除了台词角色的 reference_image，还应包含 scene.png 作为场景环境参考
- scene.png **不得**用作首帧引导（禁用 `role: first_frame`）
- 提示词中注明：`场景参考@imageN`