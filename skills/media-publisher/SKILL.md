---
name: media-publisher
description: "发布视频到小红书/抖音/视频号三平台。触发条件：用户要求发布视频、分发视频、同步视频到平台，或明确提到小红书/抖音/视频号发布。技能包含完整的浏览器自动化流程，处理 Wujie 微前端框架、Ant Design Upload 组件等复杂场景。"
---

# Media Publisher — 三平台视频发布

自动化发布视频到小红书、抖音、视频号。

## 工作流程

### Step 0 — 确认视频文件

视频文件位置：`D:\wujm\QClaw_data\workspace-doubao-video\final_with_bgm.mp4`

```powershell
$file = "D:\wujm\QClaw_data\workspace-doubao-video\final_with_bgm.mp4"
if (Test-Path $file) {
  $info = Get-Item $file
  Write-Output "视频: $($info.Name) 大小: $([math]::Round($info.Length/1MB, 1)) MB"
} else {
  Write-Output "ERROR: 视频文件不存在"
}
```

### Step 1 — 小红书发布

**前提条件**：RedBookSkills Chrome Profile（端口9222）有登录态

```powershell
# 1. 启动RedBookSkills专用Chrome
python "D:\.agents\skills\redbookskills\scripts\chrome_launcher.py"

# 2. xbrowser打开发布页
node "D:\wujm\QClaw\resources\openclaw\config\skills\xbrowser\scripts\xb.cjs" run --browser cft open "https://creator.xiaohongshu.com/publish/publish?source=official"

# 3. 等待页面加载后snapshot
Start-Sleep -Seconds 3
node "D:\wujm\QClaw\resources\openclaw\config\skills\xbrowser\scripts\xb.cjs" run --browser cft snapshot

# 4. 点击"上传视频"标签
node "D:\wujm\QClaw\resources\openclaw\config\skills\xbrowser\scripts\xb.cjs" run --browser cft click <上传视频标签ref>

# 5. 上传视频
node "D:\wujm\QClaw\resources\openclaw\config\skills\xbrowser\scripts\xb.cjs" run --browser cft upload "input[type=file]" "D:\wujm\QClaw_data\workspace-doubao-video\final_with_bgm.mp4"

# 6. 等待视频处理（建议60-120秒）
Start-Sleep -Seconds 90

# 7. 填写标题和正文
node "D:\wujm\QClaw\resources\openclaw\config\skills\xbrowser\scripts\xb.cjs" run --browser cft click <标题ref>
node "D:\wujm\QClaw\resources\openclaw\config\skills\xbrowser\scripts\xb.cjs" run --browser cft type <标题ref> "标题内容"
node "D:\wujm\QClaw\resources\openclaw\config\skills\xbrowser\scripts\xb.cjs" run --browser cft click <正文ref>
node "D:\wujm\QClaw\resources\openclaw\config\skills\xbrowser\scripts\xb.cjs" run --browser cft type <正文ref> "正文内容"

# 8. 添加话题标签
node "D:\wujm\QClaw\resources\openclaw\config\skills\xbrowser\scripts\xb.cjs" run --browser cft click <话题标签ref>

# 9. 点击发布
node "D:\wujm\QClaw\resources\openclaw\config\skills\xbrowser\scripts\xb.cjs" run --browser cft click <发布ref>
```

**成功标志**：页面跳转到空白发布页（"拖拽视频到此"）

---

### Step 2 — 抖音发布

**前提条件**：cft浏览器有抖音登录态（吾视闪电账号）

```powershell
# 1. 打开发布页
node "D:\wujm\QClaw\resources\openclaw\config\skills\xbrowser\scripts\xb.cjs" run --browser cft open "https://creator.douyin.com/creator-micro/content/upload"

# 2. 上传视频
node "D:\wujm\QClaw\resources\openclaw\config\skills\xbrowser\scripts\xb.cjs" run --browser cft upload "input[type=file]" "D:\wujm\QClaw_data\workspace-doubao-video\final_with_bgm.mp4"

# 3. 等待处理（视频较大时需要更久）
Start-Sleep -Seconds 60

# 4. 填写标题
node "D:\wujm\QClaw\resources\openclaw\config\skills\xbrowser\scripts\xb.cjs" run --browser cft fill <标题ref> "标题内容"

# 5. 填写简介（如果需要）
node "D:\wujm\QClaw\resources\openclaw\config\skills\xbrowser\scripts\xb.cjs" run --browser cft click <简介ref>
node "D:\wujm\QClaw\resources\openclaw\config\skills\xbrowser\scripts\xb.cjs" run --browser cft type <简介ref> "简介内容"

# 6. 添加话题标签
node "D:\wujm\QClaw\resources\openclaw\config\skills\xbrowser\scripts\xb.cjs" run --browser cft click <话题ref>

# 7. 设置"内容由AI生成"声明（如需要）
node "D:\wujm\QClaw\resources\openclaw\config\skills\xbrowser\scripts\xb.cjs" run --browser cft click <AI声明ref>

# 8. 点击发布
node "D:\wujm\QClaw\resources\openclaw\config\skills\xbrowser\scripts\xb.cjs" run --browser cft click <发布ref>
```

**成功标志**：页面跳转到 `content/manage?enter_from=publish`

---

### Step 3 — 视频号发布 ⭐ Bridge方案

**关键发现**：视频号使用 Wujie 微前端框架（iframe + Shadow DOM），file input 在 iframe 内部，xbrowser 无法直接访问。

**Bridge 上传方案**：

```javascript
// 1. 在主文档创建bridge input
var iframe = document.querySelector('iframe');
var bridge = document.createElement('input');
bridge.type = 'file';
bridge.id = '__bridge_input__';
bridge.style.cssText = 'position:fixed;top:-999px';
bridge.addEventListener('change', function() {
  var idoc = iframe.contentDocument;
  var iinp = idoc.querySelector('input[type=file]');
  if (iinp && bridge.files.length > 0) {
    var dt = new DataTransfer();
    for (var i = 0; i < bridge.files.length; i++) dt.items.add(bridge.files[i]);
    iinp.files = dt.files;
    var wrapper = iinp.closest('.ant-upload') || iinp.parentElement;
    if (wrapper) wrapper.dispatchEvent(new Event('change', {bubbles: true}));
    iinp.dispatchEvent(new Event('change', {bubbles: true}));
  }
});
document.body.appendChild(bridge);
```

**填写描述（关键：不能用 innerHTML）**：

```javascript
// 必须用 execCommand('insertText') 触发Vue合成事件
var doc = iframe.contentDocument;
var descEl = doc.querySelector('.input-editor') || doc.querySelector('[contenteditable="true"]');
descEl.focus();
doc.execCommand('selectAll', false, null);
doc.execCommand('insertText', false, '描述内容');
descEl.dispatchEvent(new Event('input', {bubbles: true}));
descEl.dispatchEvent(new Event('change', {bubbles: true}));
```

**完整流程**：

```powershell
# 1. 打开发布页
node "D:\wujm\QClaw\resources\openclaw\config\skills\xbrowser\scripts\xb.cjs" run --browser cft open "https://channels.weixin.qq.com/platform/post/create"

# 2. 注入bridge（需要base64编码JS后eval）
# 见下方脚本

# 3. 上传视频到bridge
node "D:\wujm\QClaw\resources\openclaw\config\skills\xbrowser\scripts\xb.cjs" run --browser cft upload "#__bridge_input__" "D:\wujm\QClaw_data\workspace-doubao-video\final_with_bgm.mp4"

# 4. 等待处理
Start-Sleep -Seconds 60

# 5. 填写短标题（用xbrowser原生fill）
node "D:\wujm\QClaw\resources\openclaw\config\skills\xbrowser\scripts\xb.cjs" run --browser cft fill <短标题ref> "短标题"

# 6. 填写描述（用execCommand）
# 需要eval执行JS

# 7. 点击发表（需要在iframe内执行）
# 需要eval执行JS
```

**成功标志**：页面跳转到 `platform/post/list`

---

## 技术要点

### 1. xbrowser 命令格式

```bash
node "<xb.cjs path>" run --browser <cft|chrome> <action> [args]

# 常用action
open <url>              # 打开网页
snapshot                # 获取元素快照（返回@ref）
click <@ref>            # 点击元素
fill <@ref> "text"      # 清空后填入
type <@ref> "text"      # 逐字符输入
upload <selector> <file> # 文件上传
eval "<js>"             # 执行JS
screenshot              # 截图
```

### 2. 处理 iframe/Wujie 的通用方案

**问题**：Wujie 微前端框架（iframe + Shadow DOM）中，file input 在 iframe 内。

**解决**：
1. 主文档创建 bridge `<input type="file">`
2. bridge change 事件中，用 DataTransfer 复制文件到 iframe 内的 file input
3. 触发 iframe 内 Ant Design Upload 组件的 change 事件

### 3. 触发 Vue/React 合成事件

**问题**：用 `innerHTML` 设置文本不会触发 Vue/React 数据绑定。

**解决**：
```javascript
element.focus();
document.execCommand('insertText', false, 'text');
element.dispatchEvent(new Event('input', {bubbles: true}));
```

### 4. 等待视频处理

视频上传后需要等待服务器处理（生成封面、转码等）：
- 小红书：60-120秒
- 抖音：60-90秒
- 视频号：60秒

建议在 upload 后用 `screenshot` 确认处理完成再填写表单。

---

## 常见问题

| 问题 | 解决方案 |
|------|---------|
| 登录态失效 | 检查对应 Chrome Profile 是否有登录 |
| 元素 ref 失效 | DOM 变化后重新 snapshot |
| 视频处理超时 | 增加等待时间，用 screenshot 确认状态 |
| 视频号上传失败 | 使用 Bridge 方案（见Step 3） |
| 标题/描述未生效 | 用 execCommand('insertText') 而非 innerHTML |
| 找不到元素 | 检查是否在 iframe 内，需要在 iframe 内执行 JS |

---

## 文件路径

| 资源 | 路径 |
|------|------|
| 视频文件 | `D:\wujm\QClaw_data\workspace-doubao-video\final_with_bgm.mp4` |
| xbrowser CLI | `D:\wujm\QClaw\resources\openclaw\config\skills\xbrowser\scripts\xb.cjs` |
| RedBookSkills Chrome | `D:\.agents\skills\redbookskills\scripts\chrome_launcher.py` |
| 发布日志 | `<workspace>/memory/publish-log-YYYY-MM-DD.md` |
