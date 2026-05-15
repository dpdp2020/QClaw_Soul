---
name: doubao-video-generator
description: "Generate short videos using Doubao (豆包) web platform. Triggered when: user asks to generate video with Doubao, task involves video generation from script, or user says generate video. This skill automates the complete Doubao video generation workflow: reading script file, entering video generation mode, filling script text with Chinese support, uploading reference images, and submitting the generation request."
---

# Doubao Video Generator

Automated video generation using Doubao web platform (doubao.com/chat). Handles Chinese text encoding and multi-step workflow.

## Workflow (6 Steps)

**Critical: Always follow this exact order.**

0. **Read script file** → loads video script from .md file, extracts scene content
1. **Click "视频生成" button** → enters video generation mode
2. **Fill script** → writes script text to input box (verified base64+TextDecoder+JSON.stringify method)
3. **Upload reference images** → uploads 3-5 reference images via hidden file input
4. **Set ratio & model** → select 9:16 aspect ratio, Seedance 2.0 Fast
5. **Click send/submit** → submits to Doubao for processing
6. **Download video** → extract video URL via JS + download to workspace

## Step 0 — Find & Read Script File

**Multiple scripts may exist.** Use the most recent one unless Franco specifies otherwise.

**Script locations:**
```
# Primary (media-operator workspace)
D:\wujm\QClaw_data\workspace-media-operator\memory\video-script-*.md
```

**To list all available scripts:**
```powershell
Get-ChildItem "D:\wujm\QClaw_data\workspace-media-operator\memory\video-script*"
```

**Selection rules:**
- If Franco names a script (by title or scene): use that one
- If Franco says "latest" or doesn't specify: use the most recently modified
- Read the file fully; extract scene numbers, characters, dialogue lines, reference image order, `>>` 画面指令, and `【情绪】`标签

**Script parsing — MUST preserve complete format:**

Each dialogue line in the .md script has this structure:
```
角色[动作描述]用XX音说："台词内容" >> [字幕/画面指令]
【情绪：XXX】
```

> ⚠️ **注意：原始剧本中通常没有 `（参考图N）` 标记！这个标记需要你在构建 fill 文本时添加。**

When building the fill text for Doubao, you MUST include ALL parts:

**Header (前置描述) — 必须动态生成，根据脚本实际出镜人物填写座位：**

**座位布局规则（CRITICAL）：**
- 电闪闪 → 始终固定坐在左下角主播位
- 其余出镜人物按剧本出场顺序，从左到右依次分配评论员席位
- 第一个非电闪闪角色 → 评论员左边位
- 第二个非电闪闪角色 → 评论员右边位
- 如果有3+个非电闪闪角色 → 按出场顺序继续往后排
- 全过程人物座位严禁互换

**Header 模板（根据实际出镜人物填充）：**
```
按照下面剧本台词配音，需要字幕，生成9:16格式视频；场景布局：[根据出镜人数描述]。角色固定：[每个角色的具体座位]。全过程人物座位严禁互换。场景约束：严禁增删改场景参考图中的任何家具、设备及其位置，必须完全保持原样。（参考图1）
```

**示例（3人出镜 — 电闪闪、小零、花花）：**
```
按照下面剧本台词配音，需要字幕，生成9:16格式视频；场景布局：画面左下角为专属主播位，右边为两个并排的评论员席位。角色固定：电闪闪始终固定坐在左下角主播位；小零坐在评论员左边位，花花坐在评论员右边位。全过程人物座位严禁互换。场景约束：严禁增删改场景参考图中的任何家具、设备及其位置，必须完全保持原样。（参考图1）
```

**示例（2人出镜 — 电闪闪、牛牛）：**
```
按照下面剧本台词配音，需要字幕，生成9:16格式视频；场景布局：画面左下角为专属主播位，右边为单个评论员席位。角色固定：电闪闪始终固定坐在左下角主播位；牛牛坐在评论员位。全过程人物座位严禁互换。场景约束：严禁增删改场景参考图中的任何家具、设备及其位置，必须完全保持原样。（参考图1）
```

**示例（4人出镜 — 电闪闪、魏教授、老黑、节哥）：**
```
按照下面剧本台词配音，需要字幕，生成9:16格式视频；场景布局：画面左下角为专属主播位，右边为三个并排的评论员席位。角色固定：电闪闪始终固定坐在左下角主播位；魏教授坐在评论员最左侧位，老黑坐在评论员中间位，节哥坐在评论员最右侧位。全过程人物座位严禁互换。场景约束：严禁增删改场景参考图中的任何家具、设备及其位置，必须完全保持原样。（参考图1）
```

- **场景约束 CRITICAL**: 必须包含"严禁增删改场景参考图中的任何家具、设备及其位置，必须完全保持原样"，防止AI添加/删除家具或改变场景布局
- **⚠️ 禁止使用泛泛描述如"其他人物坐在评论员位"！必须逐个列出每个出镜角色的具体座位！**

**Dialogue lines:**
1. ✅ 角色名 + [动作] + **（参考图N）** + 用XX音说：+ "台词内容"
2. ✅ `>> [字幕/画面指令]` — tells Doubao AI what text/elements to show on screen
3. ✅ `【情绪：XXX】` — guides character expression/performance style

**Do NOT strip or truncate any of these parts.** The header constraints, `>>` and `【情绪】` sections are critical for video quality.

### 🚨 参考图序号规则（CRITICAL — 每次必须遵守）⚠️

**参考图序号 = 上传顺序 = 从 1 开始连续编号。** 豆包按上传顺序自动给图片分配参考图编号。

#### 错误做法 ❌
```
// 原始剧本没有参考图标记，你自作主张加了全局编号
小零[眼珠快速转动]（参考图5）用冷静机械音说："..."   ← 编号5？但只传了4张图！
电闪闪[自信微笑]（参考图4）用甜美少女声说："..."   ← 编号4？跳过了3！
魏教授[微微颔首]（参考图2）用冷静学术腔说："..."    ← 编号2？那1和3是谁？
```
上传4张图但脚本出现

## Step 1 — Enter Video Generation Mode

```bash
node "D:\wujm\QClaw\resources\openclaw\config\skills\xbrowser\scripts\xb.cjs" run --browser cft snapshot
```

Find the "视频生成" button ref from snapshot, then click it:
```bash
node "D:\wujm\QClaw\resources\openclaw\config\skills\xbrowser\scripts\xb.cjs" run --browser cft click "<ref>"
```

The page will switch to video generation mode (new input area appears).

## Step 2 — Fill Script (Slate Editor API Method) ⭐⭐

**CRITICAL: Doubao uses Slate.js rich-text editor (NOT a standard input/textarea).**

### Why this matters?

The input box is a `contenteditable div` powered by **Slate.js** (`data-slate-editor`, `data-slate-node`).
Slate maintains its own internal state (`editor.children`) separate from DOM innerText.

| Method | DOM Visual | Slate State (`editor.children`) | Submit Button |
|:---|:---|:---|:---|
| `execCommand('insertText')` ❌ | ✅ Shows text | ❌ Empty | ❌ Disabled |
| **`slateEditor.insertText()`** ✅ | ✅ Shows text | ✅ Updated | **✅ Activated!** |
| `xb type` (char-by-char) | ✅ | ✅ | ✅ But slow for long scripts |

**Only `slateEditor.insertText()` or real keyboard input can activate the submit button.**

### How to find the Slate Editor instance

The Slate editor lives in React's fiber tree at depth=6 from the contenteditable element:
```
DOM element [contenteditable][role="textbox"]
  → __reactFiber$xxx (React Fiber node, tag=5, type="div")
    → return ×1 (tag=0)
    → return ×2 (tag=10, has value.editor)
    → return ×3 (tag=10, value=false)
    → return ×4 (tag=0, type="ty")
    → return ×5 (tag=10, value=false)
    → return ×6 (tag=10, value={ v:5, editor: <SlateEditor> })  ← TARGET!
```
The editor object has **89 methods** including `insertText()`, `apply()`, `onChange()`.

### Procedure (3-step, fully automated)

#### Step 2a — Generate the fill JS + eval command

Write a generator script (`_gen_fill.js`) that uses `JSON.stringify()` to safely embed the full script text:

```javascript
// _gen_fill.js — generates Slate insertText fill JS for Doubao
const fs = require('fs');

// === PASTE YOUR FULL SCRIPT HERE (from .md, COMPLETE format) ===
const fullScript = `<PASTE_COMPLETE_SCRIPT_HERE>`;
// ================================================================

console.log('Script length:', fullScript.length, 'chars');
console.log('Has quotes:', fullScript.includes('"'));
console.log('Has >>:', fullScript.includes('>>'));
console.log('Has 情绪:', fullScript.includes('【情绪'));

// Generate browser-fill JS using Slate Editor API (NOT execCommand!)
const jsCode = `
var _text = ${JSON.stringify(fullScript)};
var _el = document.querySelector('[contenteditable][role="textbox"]');
if (!_el) { 'ERROR: no textbox'; } else {
  var _fk = Object.keys(_el).find(function(k){return k.includes('Fiber');});
  var _fiber = _fk ? _el[_fk] : null;
  var _p = _fiber ? _fiber.return : null;
  var _se = null;
  for (var i = 0; i < 7 && _p; i++) {
    var _pp = _p.pendingProps || {};
    if (_pp.value && typeof _pp.value === 'object' && _pp.value.editor && typeof _pp.value.editor.insertText === 'function') {
      _se = _pp.value.editor; break;
    }
    _p = _p.return;
  }
  if (!_se) { 'ERROR: Slate editor not found in fiber tree'; }
  else {
    try {
      _se.insertText(_text);
      'OK: inserted ' + _text.length + ' chars via Slate API, children=' + JSON.stringify(_se.children).substring(0,100);
    } catch(e) { 'ERROR: ' + e.message; }
  }
}`;

fs.writeFileSync('D:\\wujm\\QClaw_data\\workspace-doubao-video\\_fill_script.js', jsCode, 'utf8');

// Generate base64 eval command
const b64 = Buffer.from(jsCode).toString('base64');
const evalCmd = `var _fx=new Uint8Array(atob("${b64}").split("").map(function(c){return c.charCodeAt(0)}));var _fy=new TextDecoder("utf-8").decode(_fx);eval(_fy)`;
fs.writeFileSync('D:\\wujm\\QClaw_data\\workspace-doubao-video\\_eval_cmd.txt', evalCmd, 'utf8');

console.log('Fill JS written:', jsCode.length, 'bytes');
console.log('Base64 length:', b64.length);
console.log('Ready: run _run_fill.js to execute.');
```

Run it:
```bash
node D:\wujm\QClaw_data\workspace-doubao-video\_gen_fill.js
```

#### Step 2b — Execute the fill via xb eval

Write a runner script (`_run_fill.js`) to avoid PowerShell quote issues:

```javascript
// _run_fill.js — executes the eval command via xbrowser
const { execSync } = require('child_process');
const evalCmd = require('fs').readFileSync(
  'D:\\wujm\\QClaw_data\\workspace-doubao-video\\_eval_cmd.txt', 'utf8'
).trim();

console.log('Running eval, cmd length:', evalCmd.length);
const result = execSync(
  'node "D:\\wujm\\QClaw\\resources\\openclaw\\config\\skills\\xbrowser\\scripts\\xb.cjs" run --browser cft eval ' + JSON.stringify(evalCmd),
  { encoding: 'utf8', timeout: 15000 }
);
console.log(result);
```

Run it:
```bash
node D:\wujm\QClaw_data\workspace-doubao-video\_run_fill.js
```

#### Step 2c — Verify with screenshot

```bash
node "D:\wujm\QClaw\resources\openclaw\config\skills\xbrowser\scripts\xb.cjs" run --browser cft screenshot
```

Check that the input box shows the complete script AND the submit button (blue arrow) is **enabled/active**.

### Key Technical Details

**Why `JSON.stringify(fullScript)` is critical:**
- It automatically escapes embedded double quotes `"` → `\"` in the generated JS
- It handles newlines, backslashes, and all special characters correctly
- Without it, the `"` inside dialogue lines would break the JS string literal

**Why `_fx`/`_fy` variable names:**
- Browser eval scope may have pre-existing variables (`bytes`, `code`, `_b`, `_c`)
- Use unique prefixed names to avoid `Identifier already declared` errors

**Why we walk up 6 levels in the fiber tree:**
- The contenteditable div's fiber (depth 0) is just the raw DOM element
- The Slate `<Editable>` component wraps it at depth 1-4
- The `<Slate>` provider component holds the `editor` instance at depth 6
- We look for `pendingProps.value.editor.insertText` (a function) as the signature

**Selector `[contenteditable][role="textbox"]`:**
- More specific than `[contenteditable="true"]` — targets only the main input
- Works reliably in Doubao's video generation mode

### Script Format Rules ⭐ CRITICAL

**MUST preserve the COMPLETE line format from the .md script. Every part matters:**

| Part | Example | Purpose | Must Include? |
|------|---------|---------|:---:|
| Header | `按照下面脚本台词配音，需要字幕，生成9:16格式视频；场景（参考图1）...` | Global instructions | ✅ |
| Dialogue line | `小零[眼珠快速转动]（参考图4）用冷静机械音说："..."` | Character + action + voice + speech | ✅ |
| **>> 指令** | `>> [过热信号失效，需新增例外]` | On-screen text / visual cue for Doubao AI | ✅ **REQUIRED** |
| **【情绪】** | `【情绪：困惑+思考】` | Performance emotion direction for Doubao AI | ✅ **REQUIRED** |

**Rules:**
- Use `（参考图n）` format for character references (not `图n`)
- Scene description header must include `（参考图1）` for the scene image + seat layout + **scene constraints**
- **Scene constraint CRITICAL**: Must include "场景约束：严禁增删改场景参考图中的任何家具、设备及其位置，必须完全保持原样" to prevent AI from adding/removing furniture or changing the set layout
- Keep original double quotes `"` in dialogue lines — they WILL be preserved by JSON.stringify + base64 method
- Keep `>> [指令]` on the same line as the dialogue (it's part of the line)
- Keep `【情绪：XXX】` on its own line immediately after each dialogue line
- **NEVER truncate at `>>`** — everything after `>>` is meaningful to Doubao AI
- **NEVER omit `【情绪】` tags** — they guide character performance

**Example formatted script (Scene 1, COMPLETE with >> and 【情绪】, 4 images → 参考图1-4):**
```
按照下面剧本台词配音，需要字幕，生成9:16格式视频；场景布局：画面左下角为专属主播位，右边为两个并排的评论员席位。角色固定：电闪闪始终固定坐在左下角主播位；魏教授坐在评论员左边位，老黑坐在评论员右边位。全过程人物座位严禁互换。场景约束：严禁增删改场景参考图中的任何家具、设备及其位置，必须完全保持原样。（参考图1）
魏教授[推眼镜]（参考图2）用冷静学术腔说："上周设了过热等回调，今天半导体直接起飞。" >> [过热信号等回调，今天直接起飞]
【情绪：遗憾+自省】
老黑[冷哼一声]（参考图3）用低沉磁音说："过热等回调，今天等来了什么？" >> [等回调等来了踏空]
【情绪：不满+讽刺】
电闪闪[歪头疑惑]（参考图4）用甜美少女声说："科创50涨了4.65%，魏教授你的策略呢？" >> [科创50涨4.65%，策略呢]
【情绪：疑惑+轻微调侃】
```

上传顺序: scene.png(图1) → wei_base.png(图2) → blackie_base.png(图3) → sparky_base.png(图4)

## Step 3 — Upload Reference Images

### 🚨 上传前必须解析脚本中的（参考图n）标记（CRITICAL）⚠️

**这是最容易出错的一步！** 必须在上传前先读取脚本，解析出每个角色的（参考图n）序号，然后按序号顺序上传。

#### 正确工作流程：

1. **读取脚本 .md 文件** → 找到所有对话行中的 `（参考图n）` 标记
2. **建立映射表** → 参考图2=哪个角色，参考图3=哪个角色，参考图4=哪个角色...
3. **确定上传顺序** → 参考图1（场景图）→ 参考图2（角色A）→ 参考图3（角色B）→ 参考图4（角色C）
4. **按映射表上传** → 第1张上传 scene.png，第2张上传参考图2对应的角色图片，第3张上传参考图3对应的角色图片...
5. **验证** → 上传完成后，检查脚本中的（参考图n）与实际上传顺序是否一致

#### ❌ 错误示例（2026-05-14 真实事故）：

脚本中写的是：
```
节哥[痞笑]（参考图2）用痞气男中音说：...
魏教授[微微颔首]（参考图3）用冷静学术腔说：...
电闪闪[眉开眼笑]（参考图4）用甜美少女声说：...
```

**正确的上传顺序应该是：**
- 第1张：scene.png（参考图1）
- 第2张：jge_base.png（参考图2 = 节哥）
- 第3张：wei_base.png（参考图3 = 魏教授）← 必须先传魏教授
- 第4张：sparky_base.png（参考图4 = 电闪闪）← 最后传电闪闪

**但实际错误操作：**
- 第3张上传了 sparky_base.png（电闪闪）← 错！
- 第4张上传了 wei_base.png（魏教授）← 错！

**结果：** 豆包AI认为参考图3=电闪闪，参考图4=魏教授，导致角色脸用反了！

---

```bash
node "D:\wujm\QClaw\resources\openclaw\config\skills\xbrowser\scripts\xb.cjs" run --browser cft upload "input[type=file]" "<image-path>"
```

Upload one image at a time. After each upload, the page shows a thumbnail confirmation.

**Reference image paths (from workspace `assets/actors/`):**
| Image | Path | Role |
|-------|------|------|
| scene.png | `D:\wujm\QClaw_data\assets\actors\scene.png` | 场景背景 |
| wei_base.png | `D:\wujm\QClaw_data\assets\actors\wei_base.png` | 魏教授 |
| blackie_base.png | `D:\wujm\QClaw_data\assets\actors\blackie_base.png` | 老黑 |
| sparky_base.png | `D:\wujm\QClaw_data\assets\actors\sparky_base.png` | 电闪闪 |
| zero_base.png | `D:\wujm\QClaw_data\assets\actors\zero_base.png` | 小零 |

### 🚨 上传顺序 = 参考图序号（CRITICAL）⚠️

**豆包按上传顺序自动编号：第1张上传的=参考图1，第2张=参考图2，以此类推。**

脚本中写的 `（参考图N）` 的 N 必须与该角色图片的上传顺序一致！

#### 正确做法 ✅ — Scene 2 示例

Scene 2 出场角色：小零、电闪闪、魏教授 + 场景背景 = 4张图

| 上传顺序 | 图片文件 | 脚本中写 | 对应角色 |
|:---:|:---|:---|:---|
| 第1张 | scene.png | （参考图1） | 场景背景 |
| 第2张 | zero_base.png | （参考图2） | 小零 |
| 第3张 | sparky_base.png | （参考图3） | 电闪闪 |
| 第4张 | wei_base.png | （参考图4） | 魏教授 |

生成的 fill 文本中应为：
```
小零[眼珠快速转动]（参考图2）用冷静机械音说："..."
电闪闪[自信微笑]（参考图3）用甜美少女声说："..."
魏教授[微微颔首]（参考图4）用冷静学术腔说："..."
```

#### 正确做法 ✅ — Scene 1 示例

Scene 1 出场角色：魏教授、老黑、电闪闪 + 场景背景 = 4张图

| 上传顺序 | 图片文件 | 脚本中写 | 对应角色 |
|:---:|:---|:---|:---|
| 第1张 | scene.png | （参考图1） | 场景背景 |
| 第2张 | wei_base.png | （参考图2） | 魏教授 |
| 第3张 | blackie_base.png | （参考图3） | 老黑 |
| 第4张 | sparky_base.png | （参考图4） | 电闪闪 |

### 操作流程（必须严格遵守）

1. **先确定本 Scene 出场了哪些角色** → 从剧本 .md 中读取
2. **决定上传顺序** → 场景图放第1位，其余按台词出场顺序排列
3. **按上传顺序给每个角色分配参考图序号** → 第1张=参考图1, 第2张=参考图2...
4. **构建 fill 脚本文本时** → 在每个角色的 `[动作]` 后面插入 `（参考图N）`，N = 该角色图片的上传序号
5. **实际上传时** → 严格按第2步决定的顺序逐张上传

**绝不能使用全局固定编号（如永远 魏教授=2、老黑=3、电闪闪=4、小零=5），因为不同 Scene 出场角色不同，会导致序号不连续或超出实际上传数量！**

## Step 4 — Verify Model

After entering video generation mode, verify the model setting:

- **Model**: Verify Seedance 2.0 Fast is selected (default is usually correct)

> **Note**: Aspect ratio is specified in the script text (e.g., "生成9:16格式视频"), so no manual ratio selection is needed.

## Step 5 — Submit

```bash
node "D:\wujm\QClaw\resources\openclaw\config\skills\xbrowser\scripts\xb.cjs" run --browser cft click "<send-button-ref>"
```

Find the send button (blue circular arrow/button). **Use the video generation send button**, NOT the regular chat send button.

After clicking submit, wait 1-3 minutes for video generation to complete.

## Step 6 — Download Video ⭐

**Recommended: JS extract URL + curl download (reliable, path-controllable)**

### 🚨 绝对不要点击页面上的「下载电脑版」按钮！🚨

**那个按钮下载的是豆包桌面客户端安装程序（Doubao_online_installer.exe），不是视频文件！**

这是豆包网页右上角的固定推广按钮，跟视频生成结果无关。点了就会下载一个 exe 安装包，白白浪费时间。

**唯一正确的下载方式是下面的 JS 提取 URL 方法。**

### Procedure

1. **Extract video URL** from page:
```bash
node "D:\wujm\QClaw\resources\openclaw\config\skills\xbrowser\scripts\xb.cjs" run --browser cft eval "JSON.stringify(Array.from(document.querySelectorAll('video')).map(v => v.currentSrc))"
```
This returns a JSON array of video CDN URLs (usually 1 video).

2. **Download** using PowerShell Invoke-WebRequest:
```powershell
$videoUrl = "<URL_FROM_STEP_1>"
$outPath = "D:\wujm\QClaw_data\workspace-doubao-video\doubao-video-<scene>.mp4"
Invoke-WebRequest -Uri $videoUrl -OutFile $outPath -UseBasicParsing
Write-Output "Done: $((Get-Item $outPath).Length) bytes"
```

3. **Verify** the downloaded file:
```powershell
$file = "D:\wujm\QClaw_data\workspace-doubao-video\doubao-video-<scene>.mp4"
$info = Get-Item $file
Write-Output "文件: $($info.Name) 大小: $([math]::Round($info.Length/1KB, 1)) KB"
```

### Notes
- Video URL contains `download=true` parameter — ready for direct download
- File size typically 1-4 MB depending on content length
- Naming convention: `doubao-video-scene1.mp4`, `doubao-video-scene2.mp4`, etc.

## Quick Verification After Each Step

After filling script — take screenshot to verify:
```bash
node xb.cjs run --browser cft screenshot
```

After uploading images — verify thumbnails appear in the input area.

After clicking send — verify the page shows generation progress or "视频生成好啦".

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Chinese text garbled | Must use base64+TextDecoder method (Step 2) |
| Double quotes missing / truncated | Use `JSON.stringify()` in generator (Step 2a) — auto-escapes embedded quotes |
| `Identifier already declared` error | Use `_fx`/`_fy` variable names (not `_b`/`_c`) |
| `xb fill` only fills first line | Don't use `xb fill` for multi-line scripts; use base64 method |
| Cannot find upload input | `xb upload "input[type=file]" <path>` works on hidden inputs |
| Page shows "额度已用完" | Wait for quota refresh (00:00 CST daily, 10 free/day) |
| Not in video generation mode | Click "视频生成" button first |
| Element refs broken after ratio change | DOM refreshes on ratio change — re-snapshot |
| No video element found after generation | Wait 1-3 min, then re-snapshot — video may still be rendering |
| Download file empty/corrupt | Check URL validity; CDN URLs may expire — regenerate if needed |
| **`>>` or【情绪】missing from fill** | Script parsing stripped them — re-read .md and rebuild fill text with ALL parts (see Step 0 parsing rules) |
| **Fill text shorter than expected** | Check that `>> [指令]` and `【情绪：XXX】` lines are included — they add ~30-50 chars per dialogue line |
| **Text fills visually but submit button stays disabled** ⚠️ | You used `execCommand('insertText')` — it only updates DOM, NOT Slate's internal state. **Must use `slateEditor.insertText()` instead** (see Step 2). Doubao uses Slate.js rich-text editor. |
| **Slate editor not found in fiber tree** | The fiber depth may vary if Doubao updates their UI. Re-run the analysis: walk up from the contenteditable fiber, inspect each parent's `pendingProps.value` for an object with an `.editor` property that has `.insertText` method. |
| **参考图序号错误（脚本写参考图5但只传了4张）** ⚠️ | 你使用了全局固定编号（如永远 小零=5），而不是按本 Scene 实际上传顺序从1开始连续编号。**必须遵守：上传第1张=参考图1，第2张=参考图2...脚本中的 N 必须与该角色图片的上传位置一致。** 见 Step 3 的「上传顺序 = 参考图序号」规则。 |
| **点击「下载电脑版」却下载了 exe 安装程序** 🚨 | 那个按钮是豆包APP推广按钮，不是视频下载！**永远不要点它。** 正确方式：Step 6 的 JS 提取 `video.currentSrc` URL + Invoke-WebRequest 下载。 |

## xbrowser Tool Path & Commands

```
D:\wujm\QClaw\resources\openclaw\config\skills\xbrowser\scripts\xb.cjs
```

**Usage**: `node xb.cjs run --browser cft <action> [args]`

**Available actions**: `open`, `snapshot`, `screenshot`, `click`, `fill`, `eval`, `upload`, `type`, `press`, `wait`, `get`, `close`

## Complete End-to-End Example

See workflow doc: `D:\wujm\QClaw_data\workspace-doubao-video\doubao-video-e2e-workflow.md`
