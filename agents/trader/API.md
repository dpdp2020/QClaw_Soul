# API.md - 接口配置文件

_东方财富模拟盘 API 配置。_

## 基本信息

| 配置项 | 值 |
|--------|-----|
| 模拟盘API | `https://mkapi2.dfcfs.com/finskillshub/api/claw/mockTrading/` |
| API Key | `mkt_CuM6Ow_ZGKwq5CJky6Zrx4iYbRVpYyfPQs-K7KNWPb0` |

## 常用接口

### 查询持仓
```
POST /positions
Headers: Authorization: Bearer {API Key}
```

### 买入
```
POST /buy
Headers: Authorization: Bearer {API Key}
Body: { "stock_code": "600023", "price": 5.65, "volume": 1000 }
```

### 卖出
```
POST /sell
Headers: Authorization: Bearer {API Key}
Body: { "stock_code": "600023", "price": 5.70, "volume": 6000 }
```

## 请求格式

- Content-Type: `application/json`
- 认证方式: Bearer Token（API Key 放入 Authorization Header）
- 所有金额单位：人民币（元）
- 股票数量单位：股（100的整数倍）

