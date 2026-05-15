---
name: mx_search
description: 妙想资讯搜索skill，基于东方财富妙想搜索能力，用于获取金融资讯（新闻、公告、研报、政策等）。适用于个股资讯、板块主题、宏观经济、风险分析等信息检索。避免AI参考非权威或过时信息。
---

# 妙想资讯搜索skill (mx_search)

根据**用户问句**搜索相关**金融资讯**，获取与问句相关的资讯信息（如研报、新闻、解读等），并返回可读的文本内容。

## 环境配置

**必需的环境变量：**
- `MX_APIKEY` - 妙想Skills页面获取的API密钥

**API Key 已设置：**
```
mkt_CuM6Ow_ZGKwq5CJky6Zrx4iYbRVpYyfPQs-K7KNWPb0
```

## 调用方式

```bash
curl -X POST "https://mkapi2.dfcfs.com/finskillshub/api/claw/news-search" \
  -H "Content-Type: application/json" \
  -H "apikey: mkt_CuM6Ow_ZGKwq5CJky6Zrx4iYbRVpYyfPQs-K7KNWPb0" \
  -d '{"query": "搜索内容"}'
```

## 问句示例

| 类型 | 示例问句 |
|------|----------|
| 个股资讯 | 格力电器最新研报、贵州茅台机构观点 |
| 板块/主题 | 商业航天板块近期新闻、新能源政策解读 |
| 宏观/风险 | 美联储加息对A股影响、汇率风险分析 |
| 综合解读 | 今日大盘异动原因、北向资金流向解读 |

## 返回字段说明

| 字段路径 | 释义 |
|----------|------|
| `title` | 信息标题 |
| `secuList` | 关联证券列表 |
| `secuList[].secuCode` | 证券代码（如 002475） |
| `secuList[].secuName` | 证券名称（如立讯精密） |
| `secuList[].secuType` | 证券类型（股票/债券） |
| `trunk` | 信息核心正文 |

## 使用场景

- ✅ 获取个股最新资讯、研报、机构观点
- ✅ 查询板块/行业动态、政策解读
- ✅ 宏观经济分析、市场风险判断
- ✅ 需要权威、实时金融数据的场景
