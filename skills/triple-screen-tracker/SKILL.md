---
name: triple-screen-tracker
description: "A股三重滤网每日跟踪。分析自选股周线趋势/日线动量/实时价位，输出BUY/WATCH/AVOID信号。This skill should be used when the user asks about A股三重滤网, 每日跟踪, 技术面信号, triple screen, daily tracker. Keywords: 三重滤网, 每日跟踪, 技术面信号, triple screen, daily tracker, 买入信号, 周线趋势."
---

# A股三重滤网每日跟踪

> 周线定方向，日线找买点，实时看位置——三重滤网技术分析系统

## 核心能力

### 能力1：分析单只股票三重滤网信号
调用 `scripts/triple_screen_tracker.py`，传入股票代码和名称，输出 BUY/WATCH/NEUTRAL/AVOID 信号及详细指标。

### 能力2：批量跟踪自选股
脚本内置9只自选股（天孚通信、中际旭创、新易盛、中微公司、拓荆科技、华海清科、阳光电源、宁德时代、北方华创），运行即输出全部信号。

### 能力3：生成JSON数据文件
每次运行自动保存 `triple_screen_tech_YYYYMMDD.json` 到当前目录，包含完整指标数据供后续分析。

## 使用流程

### 步骤 1：确认依赖已安装

```bash
pip install requests pandas numpy
```

### 步骤 2：运行脚本

```bash
python scripts/triple_screen_tracker.py
```

脚本会：
1. 依次分析9只自选股
2. 输出每只股票的信号、价格、位置、警告信息
3. 按 BUY > WATCH > NEUTRAL > AVOID 分组汇总
4. 保存 JSON 数据文件

### 步骤 3：解读输出

**信号说明：**
| 信号 | 含义 | 操作建议 |
|------|------|---------|
| BUY | 周线向上 + 日线金叉 + 位置合理 | 重点关注/考虑买入 |
| WATCH | 周线向上但日线未确认 | 加入观察列表 |
| NEUTRAL | 趋势不明或数据不足 | 暂不操作 |
| AVOID | 周线向下或动量弱势 | 回避 |

**警告信息：**
- `break daily ema13, watch stop` — 跌破日线EMA13，注意止损
- `macd momentum weak` — MACD动量减弱
- `break 20d high, strong signal` — 突破20日高点，强势信号
- `break prev close 2%, weak signal` — 跌破昨收2%，弱势
- `weekly ema13 sloping down, caution` — 周线EMA13向下，谨慎

## 数据源

- **实时行情**: 腾讯财经 API (qt.gtimg.cn)
- **历史K线**: 腾讯财经前复权API (web.ifzq.gtimg.cn)
- **备用验证**: 新浪财经API (hq.sinajs.cn)

## 自选股列表

脚本自动从 `workspace-strategy-analyst/stock_pool.json` 读取280只成长股。

### 数据来源

选股池文件：`D:\wujm\QClaw_data\workspace-strategy-analyst\stock_pool.json`

包含280只高成长股，字段包括：
- 股票名称、代码
- 行业分类
- 营收增长率、净利润增长率
- 公司市值

### 核心9只龙头股

| 代码 | 名称 | 板块 |
|------|------|------|
| 300394 | 天孚通信 | 创业板 |
| 300308 | 中际旭创 | 创业板 |
| 300502 | 新易盛 | 创业板 |
| 688012 | 中微公司 | 科创板 |
| 688072 | 拓荆科技 | 科创板 |
| 688120 | 华海清科 | 科创板 |
| 300274 | 阳光电源 | 创业板 |
| 300750 | 宁德时代 | 创业板 |
| 002371 | 北方华创 | 主板 |

### 自定义选股池

**方式1：修改stock_pool.json（推荐）**

编辑 `D:\wujm\QClaw_data\workspace-strategy-analyst\stock_pool.json`，添加或删除股票：

```json
{
  "stocks": [
    {"name": "股票名", "code": "000001", "industry": "行业", ...},
    ...
  ]
}
```

**方式2：使用环境变量指定其他JSON文件**

```bash
export TRIPLE_SCREEN_STOCK_POOL=/path/to/your/stocks.json
python triple_screen_tracker.py
```

**方式3：代码中传参**

```python
from triple_screen_tracker import load_watch_list
WATCH_LIST = load_watch_list("/path/to/stocks.json")
```

## 输出格式

```
============================================================
  Triple Screen Daily Tracker  2026-05-10 (Sunday)
  *** Non-trading day (market closed) ***
============================================================

[W] [+] BUY last=259.1 prev=259.81 -0.27% B47%
       quote_date=2026-05-08

------------------------------------------------------------
  Summary: BUY signals first, then WATCH
------------------------------------------------------------

  [BUY] (6 stocks):
    - 中际旭创(300308) last=886.0 (prev=877.47) +0.97%
    - 中微公司(688012) last=370.0 (prev=384.6) -3.80%
    ...

  [WATCH] (1 stocks):
    - 新易盛(300502) last=551.67 (prev=563.5) -2.10%
    ...
```

## 验收标准

- ✅ 所有股票数据成功获取（无DATA ERROR）
- ✅ 信号与周线/日线指标一致
- ✅ JSON文件成功保存
- ✅ 非交易日自动标注

## 注意事项

- 依赖网络连通性（腾讯/新浪财经API）
- 如遇代理问题，脚本已内置 `trust_env=False` 绕过系统代理
- 非交易日显示 `last=` 价格（来自最近一个交易日K线）
- 分红除权日K线含额外列，脚本已自动处理
- 科创板(688xxx)与创业板(300xxx)的API返回格式不同，脚本已兼容

## 依赖 Skills

无

## 维护日志

- 2026-05-10: 初始版本，修复股票代码错误(300620→300394)、分红数据7列Bug、NEUTRAL分类Bug
