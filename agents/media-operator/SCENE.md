# SCENE.md - 场景视觉配置

_场景背景、陈设规则、Seedance 参数的完整配置。_

## 场景固定规则

**动态版本：场景数量根据配音总时长决定：≤12秒→1个，≤24秒→2个。**

| 配置项 | 固定值 |
|--------|-------|
| 场景名称 | 财经演播室 (Financial News Studio) |
| 场景数量 | 1-2个（总时长≤24秒） |
| 镜头规格 | Medium Shot（中景） |

## 背景 Prompt（固定，不得增删）

中文场景描述（节哥需翻译为英文传入 Seedance）：
```
专业财经演播室，背景是大型弧形LED屏幕，显示股市行情和数据图表，柔和的环形灯光，清新的企业美学，4K电影质感，出镜角色位于画面左侧已有办公桌位置，不添加或修改任何家具，保持原有场景布局不变
```

英文版（供 Seedance API 直接使用）：
```
Professional financial news studio, Large curved LED screen displaying stock market data and charts in background, Soft studio ring lighting, Clean corporate aesthetic, 4K cinematic quality, News anchor at the existing desk on the left side of the frame, Do not add or modify any furniture, Keep original scene layout unchanged
```

**⚠️ 提示词灵活性：**
- 不得写死"Female news anchor"——主角由剧情决定，电闪闪/魏教授/老黑/小零都可能是主咖。
- 场景描述保持中立，角色站位由剧本分配。

## Seedance 参数

| 参数 | 值 | 备注 |
|------|-----|------|
| 模型 | `doubao-seedance-2-0-fast` | |
| 比例 | `9:16` 竖屏 | |
| 单场景时长 | **≤12秒** | 节哥设置，API 上限 15秒 |
| 整集时长 | **≤24秒**（2个 Scene） | |
| 提示词语言 | 纯英文，禁止中文字符 | |
| 参考语速 | **约3-4字/秒** | 用于估算台词字数 |

### 时长与字数对照表

| Scene 时长 | 参考中文字数 |
|-----------|-------------|
| ≤5秒 | ≤18字 |
| ≤8秒 | ≤28字 |
| ≤10秒 | ≤35字 |
| ≤12秒 | ≤42字 |

**写作流程：先定 Scene 时长目标 → 查字数上限 → 填台词 → 验证。**

---

_Last updated: 2026-05-07（单Scene上限更新为12秒，全片24秒；新增字数对照表）_

