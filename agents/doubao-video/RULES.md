# RULES.md - 视频生成纪律（最高优先级）

_违反以下任何一条 = 生产事故_

---

## 🔴 绝对禁令（违反即事故）

### 1. 禁止擅自修改剧本
- **只能**使用剧本原文中的台词
- **禁止**添加剧本外的角色描述、服装描述、特征描述
- **禁止**修改角色性格、语气、行为方式
- **唯一例外**：经麦导书面确认的修改

### 2. 禁止参考图与提示词冲突
- 提示词中**不得**包含参考图中不存在的元素
- 提示词中**不得**与参考图的外观特征矛盾
- 角色服装、发型、配饰**必须**与参考图一致
- 不确定时，**删除描述**，让AI完全跟随参考图

### 3. 禁止漏传场景参考图
- **每个Scene必须**包含 scene.png 作为场景环境参考
- scene.png URL无效时，**立即上报麦导**，禁止自行移除
- 禁止以"URL无效"为由跳过场景参考

### 4. 禁止添加"创意发挥"
- **禁止**添加"sexy"、"cute"、"beautiful"等主观描述
- **禁止**添加参考图没有的表情、动作、道具
- **禁止**添加剧本没有的剧情元素

### 4.1 禁止UI/界面元素烧录到画面（2026-05-05 新增，05-06 更新）
- **禁止**在提示词中包含任何UI元素描述：进度条、加载条、百分比数字、状态指示器、HUD等
- **禁止**在角色头部/面部区域叠加任何图形覆盖层（进度条、血条、电量条等）
- 剧本中如果出现此类描述（如`头顶进度条跳动`），**制作时必须过滤掉**，不传给Seedance
- 这类元素会被Seedance忠实渲染进画面，导致最终视频看起来像播放器UI残留，严重影响观感
- **处理方式**：从画面描述中删除UI相关文字，保留角色动作和表情描述

### 4.2 禁止Seedance自行添加画面元素（2026-05-06 新增）
Seedance会根据"财经演播厅"等场景关键词，自行"创作"它认为应该有的画面元素，导致：
- 日期水印（如左上角"2025"文字）
- 底部跑马灯/滚动字幕条
- 股票代码滚动条
- 新闻标题栏/Lower Third
- 频道Logo水印

**必须在每个Scene提示词末尾添加反创作指令**：
```
No text overlays, No date stamp, No scrolling ticker, No news lower third, No channel logo, No on-screen text except character dialogue, Clean frame
```

**原因**：这些元素在不同Scene间无法保持一致（内容、位置、样式都不同），严重破坏场景连贯性。

### 5. 禁止英文配音（强制）
- **提示词必须使用中文**（与剧本语言一致）
- **必须在提示词中强制指定中文配音**：如 `用中文甜美少女声说：'台词'`
- **禁止**使用英文提示词导致生成英文配音
- **禁止**出现英文字符（标点、中文引号内除外）
- 例外：仅当麦导明确要求英文配音时

---

## 🟡 强制校验清单（每条必须打勾）

### 提交API前必须检查：

- [ ] **剧本核对**：提示词中的台词与剧本原文完全一致
- [ ] **参考图核对**：所有角色参考图已包含，且URL有效
- [ ] **场景核对**：scene.png 已包含，URL有效
- [ ] **冲突检查**：提示词中没有与参考图矛盾的描述
- [ ] **多余内容检查**：提示词中没有剧本外的角色/服装/特征描述
- [ ] **UI元素过滤**：剧本中的进度条/数字/UI描述已过滤掉（RULES 4.1）
- [ ] **反创作指令**：每个Scene提示词末尾已附加反创作指令（RULES 4.2）
- [ ] **角色数量核对**：Scene中的角色与剧本一致
- [ ] **语言核对**：提示词全部使用中文，配音指定为中文（如`用中文XX声说`）

### 生成后必须检查：

- [ ] **角色外观验证**：视频角色与参考图对比，确认一致
- [ ] **场景一致性验证**：所有Scene场景风格一致
- [ ] **台词准确性验证**：字幕与剧本原文一致

---

## 🟢 安全提示词模板

### 角色描述安全写法
```
# ✅ 正确：让AI跟随参考图
"Sparky appearance reference @image1, talking, speaking, lips moving"

# ❌ 错误：与参考图冲突
"Sparky appearance reference @image1, chestnut short hair, super short body-con dress, sexy and sharp"
```

### 场景描述安全写法
```
# ✅ 正确：引用场景参考图
"Professional financial news studio, scene reference @image3, static camera"

# ❌ 错误：自行描述场景
"Professional financial news studio, large curved LED screen..."（无场景参考）
```

---

## 📋 事故处理流程

### 发现事故后：
1. **立即停止**当前工作
2. **保留证据**（API payload、视频文件、参考图）
3. **上报麦导**，说明事故原因
4. **等待指示**，禁止自行决定返工方案
5. **记录教训**，更新本文件防止再犯

---

## 🎯 节哥自检口诀

> **"三不原则"**：
> - 剧本没有的不加
> - 参考图没有的不写
> - 麦导没确认的不改

> **"三必核对"**：
> - 必对剧本原文
> - 必对参考图片
> - 必对场景一致

> **"反创作三禁"**（2026-05-06 新增）：
> - 禁UI元素进画面（进度条、HUD）
> - 禁Seedance自由发挥（日期、跑马灯、Logo）
> - 禁省略反创作指令（每个Scene必加）

---

## 🔧 技术教训（ffmpeg/Windows 专项）

### T1. 片头视频无音轨导致 concat 后音频丢失（2026-05-06 新增/已修复）
**现象**：intro_3s.mp4 原版无音轨，直接 concat 后整个输出无音轨。

**根因**：concat demuxer 要求所有文件流类型一致，intro 无音轨则整个输出丢失音轨。

**✅ 已从源头修复**（2026-05-06）：
- 给 `assets/actors/intro_3s.mp4` 追加了内置静音 AAC 音轨（-f lavfi anullsrc + -c:a aac）
- 已推送到 GitHub：`dc6465b..47267fc`
- 后续制作直接 concat 即可，无需再手动补音轨

**若未来重新下载新片头**：需重新追加音轨，参考命令：
```bash
ffmpeg -i intro.mp4 -f lavfi -i anullsrc=channel_layout=stereo:sample_rate=44100 \
  -map 0:v -map 1:a -t 3 -c:v copy -shortest intro_with_audio.mp4
```

### T2. BGM 混音截断和音量过小（2026-05-06 新增，已修复）
**现象**：BGM 在 24 秒处停止，音量几乎听不见。

**根因**：
1. `amix=inputs=2:duration=first`：以第一个输入（视频原音频）的时长为输出时长，BGM 被截断
2. `volume=0.2`：只给 20% 音量，经 amix 平均后约 10%，几乎无声

**修复命令**（✅ 已更新到 cron）：
```bash
ffmpeg -i merged_video.mp4 -i bgm.mp3 \
  -filter_complex "[1:a]atrim=0:{total_dur},volume=1.2[bgm];[0:a][bgm]amix=inputs=2:duration=first:dropout_transition=2[aout]" \
  -map 0:v -map "[aout]" -c:v copy final_with_bgm.mp4
```
关键点：`atrim=0:{total_dur}` trim BGM 到视频完整时长；`volume=1.2` amix 后约 60%。

### T3. ffmpeg ASS filter Windows 绝对路径解析 bug（2026-05-06 新增）
**现象**：`ffmpeg -vf "ass=C:\path\to\file.ass"` 失败，错误：`Error setting option original_size to value wujmxxx`

**根因**：Windows 路径中的 `:` 被 ffmpeg 误识别为选项分隔符，导致路径被截断。

**修复**：从 `C:\tmp` 目录执行 ffmpeg，使用相对路径：
```python
import subprocess, shutil, os
tmp = r"C:\tmp"
os.makedirs(tmp, exist_ok=True)
shutil.copy2("video.mp4", os.path.join(tmp, "video.mp4"))
shutil.copy2("subs.ass", os.path.join(tmp, "subs.ass"))
subprocess.run(["ffmpeg", "-i", "video.mp4", "-vf", "ass=subs.ass",
                 "-c:v", "libx264", "-preset", "fast", "-crf", "23",
                 "-c:a", "copy", "output.mp4"], cwd=tmp)
shutil.copy2(os.path.join(tmp, "output.mp4"), "output.mp4")
```

### T4. Python subprocess 优于 PowerShell 执行 ffmpeg（2026-05-06 新增）
**原因**：
- PowerShell 对双引号 `"` 的转义处理复杂（`"` vs `"` vs `` ` ``）
- `-filter_complex "[1:a]volume=0.5,..."` 在 PowerShell 中经常失败
- Python subprocess 直接传列表，无转义问题

**建议**：涉及复杂 ffmpeg filter_complex 时，写 Python 脚本执行。

---
_最后更新：2026-05-06 by 节哥（片头+BGM+字幕技术修复）_