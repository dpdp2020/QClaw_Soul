---
name: mx_stock_simulator
description: 东方财富妙想模拟股票交易系统。支持股票组合持仓查询、买卖操作、撤单、委托查询、历史成交查询和资金查询等功能。通过调用东方财富模拟交易API，实现真实的交易体验。
triggers:
  - 买入股票
  - 卖出股票
  - 查询持仓
  - 查询资金
  - 撤单
  - 委托查询
  - 模拟交易
  - 我的模拟账户
---

# 东方财富妙想模拟股票交易

## 环境配置

**必需的环境变量：**
- `MX_APIKEY` - 妙想Skills页面获取的API密钥（必填）
- `MX_API_URL` - API基础地址（可选，默认：`https://mkapi2.dfcfs.com/finskillshub`）

**API Key 设置：**
```
mkt_CuM6Ow_ZGKwq5CJky6Zrx4iYbRVpYyfPQs-K7KNWPb0
```

## 功能列表

| 功能 | 接口路径 | 触发词 |
|------|----------|--------|
| 持仓查询 | POST `/api/claw/mockTrading/positions` | 查询持仓、我的持仓、持仓情况 |
| 买入/卖出 | POST `/api/claw/mockTrading/trade` | 买入、卖出、buy、sell |
| 撤单 | POST `/api/claw/mockTrading/cancel` | 撤单、撤销订单、cancel |
| 委托查询 | POST `/api/claw/mockTrading/orders` | 查询委托、委托记录、历史成交 |
| 资金查询 | POST `/api/claw/mockTrading/balance` | 查询资金、账户余额、资金情况 |

## 通用请求格式

```bash
curl -X POST "${MX_API_URL}<接口路径>" \
  -H "apikey: ${MX_APIKEY}" \
  -H "Content-Type: application/json" \
  -d '<请求体>'
```

## 接口详情

### 1. 持仓查询

```bash
curl -X POST "https://mkapi2.dfcfs.com/finskillshub/api/claw/mockTrading/positions" \
  -H "apikey: mkt_CuM6Ow_ZGKwq5CJky6Zrx4iYbRVpYyfPQs-K7KNWPb0" \
  -H "Content-Type: application/json" \
  -d '{"moneyUnit": 1}'
```

**响应字段：**
- `totalAssets` - 总资产（元）
- `availBalance` - 可用余额（元）
- `totalPosValue` - 总持仓市值（元）
- `posCount` - 持仓股票数量
- `posList` - 持仓明细数组

### 2. 买入/卖出操作

```bash
curl -X POST "https://mkapi2.dfcfs.com/finskillshub/api/claw/mockTrading/trade" \
  -H "apikey: mkt_CuM6Ow_ZGKwq5CJky6Zrx4iYbRVpYyfPQs-K7KNWPb0" \
  -H "Content-Type: application/json" \
  -d '{
    "type": "buy",
    "stockCode": "600519",
    "price": 1780.00,
    "quantity": 100,
    "useMarketPrice": false
  }'
```

**参数说明：**
| 参数 | 必填 | 说明 |
|------|------|------|
| `type` | 是 | buy=买入，sell=卖出 |
| `stockCode` | 是 | 股票代码（6位数字，如600519） |
| `price` | 否 | 委托价格，useMarketPrice=false时必填 |
| `quantity` | 是 | 委托数量（必须为100的整数倍） |
| `useMarketPrice` | 否 | true=市价委托（自动以最新价） |

### 3. 撤单操作

```bash
curl -X POST "https://mkapi2.dfcfs.com/finskillshub/api/claw/mockTrading/cancel" \
  -H "apikey: mkt_CuM6Ow_ZGKwq5CJky6Zrx4iYbRVpYyfPQs-K7KNWPb0" \
  -H "Content-Type: application/json" \
  -d '{"orderId": "ORD987654", "stockCode": "600519"}'
```

**一键撤单：**
```bash
curl -X POST "https://mkapi2.dfcfs.com/finskillshub/api/claw/mockTrading/cancel" \
  -H "apikey: mkt_CuM6Ow_ZGKwq5CJky6Zrx4iYbRVpYyfPQs-K7KNWPb0" \
  -H "Content-Type: application/json" \
  -d '{"type": "all"}'
```

### 4. 委托查询

```bash
curl -X POST "https://mkapi2.dfcfs.com/finskillshub/api/claw/mockTrading/orders" \
  -H "apikey: mkt_CuM6Ow_ZGKwq5CJky6Zrx4iYbRVpYyfPQs-K7KNWPb0" \
  -H "Content-Type: application/json" \
  -d '{"fltOrderDrt": 0, "fltOrderStatus": 0}'
```

**委托状态说明：**
- 1=未报, 2=已报, 3=部成, 4=已成, 5=部成待撤, 6=已报待撤, 7=部撤, 8=已撤, 9=废单, 10=撤单失败

### 5. 资金查询

```bash
curl -X POST "https://mkapi2.dfcfs.com/finskillshub/api/claw/mockTrading/balance" \
  -H "apikey: mkt_CuM6Ow_ZGKwq5CJky6Zrx4iYbRVpYyfPQs-K7KNWPb0" \
  -H "Content-Type: application/json" \
  -d '{"moneyUnit": 1}'
```

## 错误处理

| 错误码 | 说明 | 处理方式 |
|--------|------|----------|
| 113 | 今日调用次数达上限 | 前往妙想Skills页面获取更多次数 |
| 114/115/116 | API密钥问题 | 检查MX_APIKEY是否正确 |
| 404 | 未绑定模拟组合账户 | 前往 https://dl.dfcfs.com/m/itc4 创建账户 |

## 注意事项

1. **交易时间**：仅在A股交易时间可操作（9:30-11:30, 13:00-15:00）
2. **股票代码**：仅支持A股，6位数字格式
3. **委托数量**：必须为100的整数倍
4. **价格规则**：沪市最多2位小数，深市最多3位小数
