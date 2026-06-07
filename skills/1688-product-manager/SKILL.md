---
name: 1688-product-manager
description: 1688(阿里巴巴中国站)商品管理技能。当用户需要发布新商品、删除商品、查询商品列表或详情、上传商品图片到1688图片银行时使用。触发词：发布1688商品、批量发布商品、删除1688商品、查询我的1688商品、上传图片到1688、1688商品管理。注意：修改已发布商品（改价格/库存/属性）当前1688开放平台API不支持，需手动在1688后台操作。
---

# 1688 商品管理技能

管理 1688 店铺（anweirf.1688.com）的商品：发布、删除、查询、图片上传。

## 凭证（请勿外传）

```
Access Key (AK): 4962785
Access Secret (AS): W6v0SLfR4w
Access Token (TK): 255bdc2a-7e4a-4a8e-b476-fb0b4efa366b
店铺: anweirf.1688.com
```

## 核心脚本

所有脚本位于 `scripts/`，调用前先用 `read` 读取对应脚本确认参数。

| 脚本 | 功能 |
|------|------|
| `publish_product.py` | 发布单个商品（add API） |
| `batch_publish.py` | 从 Excel 批量发布商品 |
| `delete_product.py` | 删除指定商品ID |
| `list_products.py` | 查询商品列表 |
| `get_product.py` | 查询商品详情 |
| `upload_image.py` | 上传图片到1688图片银行 |

## 使用流程

### 发布新商品

1. 准备 Excel 文件（格式见下方「Excel 格式」）
2. 运行 `scripts/batch_publish.py <excel路径>`
3. 脚本自动：上传图片 → 获取类目属性 → 发布商品 → 输出结果

### 删除商品

运行 `scripts/delete_product.py <商品ID>`

### 查询商品

- 列表：`scripts/list_products.py [页码]`
- 详情：`scripts/get_product.py <商品ID>`

## Excel 格式（批量发布）

`batch_publish.py` 支持**任意列顺序**，自动识别列名，无需严格对齐。

### 自动识别的列（按表头名称匹配）

| 字段 | 支持的表头关键词 |
|------|----------------|
| 标题 | 标题、商品标题、title、商品名称 |
| 价格 | 价格、销售价格、单价、price |
| 库存 | 库存、库存数量、stock |
| SKU | SKU、商品编码、货号 |
| 主图URL | 主图、主图URL、图片URL、pic_url |
| 详情描述 | 描述、详情、详情描述、description |
| 重量 | 重量、重量kg、weight |
| 品牌 | 品牌、brand |
| 规格型号 | 型号、规格、规格型号、model |
| 产地 | 产地、生产地、origin |
| 运费模板 | 运费模板、运费 |
| 类目ID | 类目ID、类目 |

- 数据从第2行开始（第1行为表头）
- **主图URL**：支持 1688 图片银行完整URL（如 `https://cbu01.alicdn.com/img/ibank/...`），也支持本地图片路径（脚本自动上传）
- 若表头缺失，自动回退到位置兼容模式（15列完整格式 / 13列旧格式 / 8列极简格式）
- **必填**：标题、价格、SKU、主图

### 调用示例

```bash
python scripts/batch_publish.py D:\wujm\安威\helper\aw168_wifi_products.xlsx
```

发布完成后结果保存为 `<excel文件名>_publish_result.json`。

## 已知限制

- **不能修改已发布商品**：1688开放平台 `alibaba.new.product.edit` API 对 catProp 校验过严，无法绕过；`alibaba.product.modifyStock` 对单SKU商品无效。修改价格/库存/属性请手动登录 https://work.1688.com/product/manage.htm 操作。
- `alibaba.new.product.getSchema` 偶尔返回 `SYS_ERROR`，此时无法获取类目属性选项，发布会失败，需重试。

## API 签名方法

所有1688 API 使用 HMAC-SHA1 签名，规则：
1. 将所有参数（不含 `_aop_signature`）按 key 字典序排序
2. 拼接为 `key1value1key2value2...`（无分隔符）
3. 前缀加上 `param2/1/{namespace}/{api_name}/{AK}`
4. 对结果字符串做 HMAC-SHA1，输出大写十六进制

详见 `scripts/publish_product.py` 中的 `sign()` 函数。

## 类目信息

- 默认类目ID：`1036016`（办公家具相关）
- 运费模板ID：`13900148`
- 发货地址ID：`33847521`
- scene：`popular`

如类目变更，需重新获取 `getSchema` 以取得正确的 catProp 选项。
