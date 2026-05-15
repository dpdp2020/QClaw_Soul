---
name: qclaw-soul-sync
description: "同步 QClaw Agent 定义、知识库和技能到 GitHub 仓库。当用户提到'同步到GitHub'、'上传soul'、'推送agent定义'、'更新QClaw_Soul仓库'、'sync soul'、'上传技能'、'同步技能到GitHub'时触发。支持全量同步和增量同步，自动处理大文件排除和目录结构维护。"
---

# QClaw Soul Sync — Agent 定义 & 知识库 GitHub 同步

## 配置

| 项目 | 值 |
|------|-----|
| GitHub 仓库 | `dpdp2020/QClaw_Soul` |
| 本地数据根目录 | `D:\wujm\QClaw_data` |
| 文件大小限制 | 50MB（GitHub 限制） |
| 默认分支 | `main` |

## 同步映射

### Agent 定义文件

| 本地路径 | 仓库路径 |
|----------|----------|
| `{data}/workspace/SOUL.md` | `agents/main/SOUL.md` |
| `{data}/workspace/AGENTS.md` | `agents/main/AGENTS.md` |
| `{data}/workspace/IDENTITY.md` | `agents/main/IDENTITY.md` |
| `{data}/workspace/USER.md` | `agents/main/USER.md` |
| `{data}/workspace/TOOLS.md` | `agents/main/TOOLS.md` |
| `{data}/workspace-finance-learner/SOUL.md` | `agents/finance-learner/SOUL.md` |
| `{data}/workspace-finance-learner/IDENTITY.md` | `agents/finance-learner/IDENTITY.md` |
| `{data}/workspace-finance-learner/TOOLS.md` | `agents/finance-learner/TOOLS.md` |
| `{data}/workspace-finance-learner/USER.md` | `agents/finance-learner/USER.md` |
| `{data}/workspace-market-news/SOUL.md` | `agents/market-news/SOUL.md` |
| `{data}/workspace-market-news/IDENTITY.md` | `agents/market-news/IDENTITY.md` |
| `{data}/workspace-market-news/RULES.md` | `agents/market-news/RULES.md` |
| `{data}/workspace-market-news/TOOLS.md` | `agents/market-news/TOOLS.md` |
| `{data}/workspace-market-news/USER.md` | `agents/market-news/USER.md` |
| `{data}/workspace-strategy-analyst/SOUL.md` | `agents/strategy-analyst/SOUL.md` |
| `{data}/workspace-strategy-analyst/IDENTITY.md` | `agents/strategy-analyst/IDENTITY.md` |
| `{data}/workspace-strategy-analyst/STRATEGY.md` | `agents/strategy-analyst/STRATEGY.md` |
| `{data}/workspace-strategy-analyst/TOOLS.md` | `agents/strategy-analyst/TOOLS.md` |
| `{data}/workspace-strategy-analyst/USER.md` | `agents/strategy-analyst/USER.md` |
| `{data}/workspace-trader/SOUL.md` | `agents/trader/SOUL.md` |
| `{data}/workspace-trader/IDENTITY.md` | `agents/trader/IDENTITY.md` |
| `{data}/workspace-trader/RULES.md` | `agents/trader/RULES.md` |
| `{data}/workspace-trader/API.md` | `agents/trader/API.md` |
| `{data}/workspace-trader/TOOLS.md` | `agents/trader/TOOLS.md` |
| `{data}/workspace-trader/USER.md` | `agents/trader/USER.md` |
| `{data}/workspace-media-operator/SOUL.md` | `agents/media-operator/SOUL.md` |
| `{data}/workspace-media-operator/IDENTITY.md` | `agents/media-operator/IDENTITY.md` |
| `{data}/workspace-media-operator/CAST.md` | `agents/media-operator/CAST.md` |
| `{data}/workspace-media-operator/PRODUCTION.md` | `agents/media-operator/PRODUCTION.md` |
| `{data}/workspace-media-operator/SCENE.md` | `agents/media-operator/SCENE.md` |
| `{data}/workspace-media-operator/TOOLS.md` | `agents/media-operator/TOOLS.md` |
| `{data}/workspace-media-operator/USER.md` | `agents/media-operator/USER.md` |
| `{data}/workspace-media-producer/SOUL.md` | `agents/media-producer/SOUL.md` |
| `{data}/workspace-media-producer/IDENTITY.md` | `agents/media-producer/IDENTITY.md` |
| `{data}/workspace-media-producer/PRODUCTION.md` | `agents/media-producer/PRODUCTION.md` |
| `{data}/workspace-media-producer/RULES.md` | `agents/media-producer/RULES.md` |
| `{data}/workspace-media-producer/TOOLS.md` | `agents/media-producer/TOOLS.md` |
| `{data}/workspace-media-producer/USER.md` | `agents/media-producer/USER.md` |
| `{data}/workspace-media-publisher/SOUL.md` | `agents/media-publisher/SOUL.md` |
| `{data}/workspace-media-publisher/IDENTITY.md` | `agents/media-publisher/IDENTITY.md` |
| `{data}/workspace-media-publisher/TOOLS.md` | `agents/media-publisher/TOOLS.md` |
| `{data}/workspace-media-publisher/USER.md` | `agents/media-publisher/USER.md` |
| `{data}/workspace-doubao-video/SOUL.md` | `agents/doubao-video/SOUL.md` |
| `{data}/workspace-doubao-video/IDENTITY.md` | `agents/doubao-video/IDENTITY.md` |
| `{data}/workspace-doubao-video/PRODUCTION.md` | `agents/doubao-video/PRODUCTION.md` |
| `{data}/workspace-doubao-video/RULES.md` | `agents/doubao-video/RULES.md` |
| `{data}/workspace-doubao-video/TOOLS.md` | `agents/doubao-video/TOOLS.md` |
| `{data}/workspace-doubao-video/USER.md` | `agents/doubao-video/USER.md` |

### 知识库文件

| 本地路径 | 仓库路径 |
|----------|----------|
| `{data}/workspace/assets/actors/*` | `assets/actors/*` |
| `{data}/workspace-finance-learner/knowledge-base/*` | `knowledge-base/*` |
| 其他 Agent 的 `knowledge-base/*` | `knowledge-base/{agent-name}/*` |

## 执行流程

### 1. 获取 GitHub Token

```powershell
# 方式一：从 config.json 读取（持久化配置，推荐）
$cfgPath = "C:\Users\adigle\.qclaw\skills\qclaw-soul-sync\config.json"
$cfg = Get-Content $cfgPath | ConvertFrom-Json
$token = $cfg.github_token
```

若 Token 不可用（config.json 不存在），要求用户提供 PAT（需 `repo` 权限）。

### 2. 克隆仓库

```powershell
$workDir = "D:\wujm\QClaw\data\workspace\_soul_sync_tmp"
if (Test-Path $workDir) { Remove-Item -Recurse -Force $workDir }
git clone "https://x-access-token:${token}@github.com/dpdp2020/QClaw_Soul.git" $workDir
```

### 3. 同步文件

按"同步映射"表复制文件到克隆目录。规则：
- **跳过 >50MB 文件**，记录到输出报告
- **删除仓库中存在但本地已移除的文件**（仅限映射范围内的文件）
- 保持 `README.md` 和 `.gitignore` 不变

### 4. 提交并推送

```powershell
cd $workDir
git add -A
$changed = git diff --cached --name-only
if ($changed) {
    git commit -m "sync: update agent definitions & knowledge base - $(Get-Date -Format 'yyyy-MM-dd HH:mm')"
    git push origin main
} else {
    echo "No changes to sync"
}
```

### 5. 清理

```powershell
Remove-Item -Recurse -Force $workDir
```

## 增量模式

默认全量同步。若用户指定 `--agent <name>`，仅同步该 Agent 的文件：

| `--agent` 值 | 同步范围 |
|---------------|----------|
| `main` | `agents/main/*` |
| `finance-learner` | `agents/finance-learner/SOUL.md` + `knowledge-base/*` |
| `market-news` | `agents/market-news/SOUL.md` |
| `strategy-analyst` | `agents/strategy-analyst/SOUL.md` |
| `trader` | `agents/trader/SOUL.md` |
| `media-operator` | `agents/media-operator/SOUL.md` |
| `media-producer` | `agents/media-producer/SOUL.md` |
| `media-publisher` | `agents/media-publisher/SOUL.md` |
| `knowledge-base` | 仅 `knowledge-base/*` |

## 同步技能包 (`--skill`)

将本地 `~/.qclaw/skills/` 目录中的自定义技能包同步到仓库的 `skills/` 目录。

**使用方式：**
```bash
# 同步所有 managed skills（从 ~/.qclaw/skills/ 到 GitHub skills/）
python scripts/sync_soul.py --skill --token <GITHUB_PAT>

# 预览模式（不实际推送）
python scripts/sync_soul.py --skill --token <GITHUB_PAT> --dry-run
```

**同步范围（managed skills）：**
| 技能名 | 说明 |
|--------|------|
| `triple-screen-tracker` | 三重滤网每日跟踪 |
| `quant-backtester` | 量化策略回测 |
| `mx_stock_simulator` | 股票模拟器 |
| `mx_search` | 资讯搜索 |
| `aippt` | PPT生成 |
| `kdocs` | 文档处理 |
| `persona-switch` | 人格切换 |
| `fbs_bookwriter` | 书稿写作 |
| `wecom-weisheng-scrm` | 企业微信 |
| `qclaw-soul-sync` | 本技能本身 |

**仓库目标结构：**
```
dpdp2020/QClaw_Soul
└── skills/
    ├── triple-screen-tracker/
    │   ├── SKILL.md
    │   ├── _meta.json
    │   └── scripts/
    │       └── triple_screen_tracker.py
    └── ...
```

**触发条件：**
- 用户说"同步技能"、"上传技能到GitHub"、"把xxx上传"
- 技能目录结构原样复制到 `skills/<skill-name>/`

## 输出报告

每次同步后输出简要报告：

```
🔄 QClaw Soul Sync Report
─────────────────────────
✅ 新增: 3 files
📝 修改: 5 files
🗑️ 删除: 0 files
⚠️ 跳过(>50MB): 1 files
  - 以交易为生_原书第2版.pdf (55.6MB)
📦 commit: sync: update agent definitions & knowledge base - 2026-05-01 19:30
🔗 https://github.com/dpdp2020/QClaw_Soul
```

## 注意事项

- PAT Token 存储在 `config.json`，不会在对话中明文展示。
- 同步完成后提醒用户删除已暴露的 Token（如在 GitHub 界面手动撤销）。
- 大文件建议用 Git LFS 或微云备份。

## 版本历史

- 2026-05-10: 新增 `assets/actors/*` 到知识库文件映射；新增 `--skill` 模式，支持将本地技能包同步到仓库 `skills/` 目录
- 2026-05-04: 支持 config.json 持久化 token，改用 Invoke-RestMethod (PowerShell) 替代 curl。
