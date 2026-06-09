---
name: 1688-product-manager
description: 1688(阿里巴巴中国站)商品管理技能。当用户需要发布新商品、删除商品、查询商品列表或详情、上传商品图片到1688图片银行时使用。触发词：发布1688商品、批量发布商品、删除1688商品、查询我的1688商品、上传图片到1688、1688商品管理。注意：修改已发布商品的价格/属性需手动在1688后台操作；**修改库存可通过API实现**（见下方「修改库存」章节）。
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
| `modify_stock.py` | 修改商品库存（modifystock API） |
| `update_excel_pics.py` | 更新Excel图片URL并同步显示图片 |
| `scrape_and_match_cat.py` | 抓取官网产品 → 提取关键词 → 匹配1688类目 |

## 使用流程

### 发布新商品

1. 准备 Excel 文件（格式见下方「Excel 格式」）
2. 运行 `scripts/batch_publish.py <excel路径>`
3. 脚本自动：上传图片 → 获取类目属性 → 发布商品 → 输出结果

### 删除商品

运行 `scripts/delete_product.py <商品ID>`

**API返回结构**: `{"result": {"isSuccess": true, "reason": "操作成功!"}}`
- 注意判断 `isSuccess` 字段（不是 `success`）

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

## 修改库存

运行 `scripts/modify_stock.py <商品ID> <库存值>`

### API参数结构（modifystock）
- **productStockChange** (JSON数组): `[{"productId": "商品ID", "productAmountChange": 库存变更值}]`
- **skuStocks** (JSON数组): `[{"skuId": "SKU ID", "stockChange": 库存变更值}]`
- **webSite**: `"1688"`
- **increaseModify**: `"false"`（非增量模式，直接设为指定值）
- 单SKU商品的 skuId 填商品ID即可
- productAmountChange / stockChange 为增量值（设为10就是库存+10）

## 已知限制

- **不能修改已发布商品的价格/属性**：`alibaba.new.product.edit` 对 catProp 校验过严；`alibaba.product.edit` ACL权限拒绝。请手动登录 https://work.1688.com/product/manage.htm 操作。
- **可以修改库存**：通过 `alibaba.product.modifystock` API 实现（见上方「修改库存」章节）。
- `alibaba.new.product.getSchema` 偶尔返回 `SYS_ERROR`，此时无法获取类目属性选项，发布会失败，需重试。

## API 签名方法

所有1688 API 使用 HMAC-SHA1 签名，规则：
1. 将所有参数（不含 `_aop_signature`）按 key 字典序排序
2. 拼接为 `key1value1key2value2...`（无分隔符）
3. 前缀加上 `param2/1/{namespace}/{api_name}/{AK}`
4. 对结果字符串做 HMAC-SHA1，输出大写十六进制

详见 `scripts/publish_product.py` 中的 `sign()` 函数。

## 类目搜索与自动匹配

### 类目搜索API（正确）

**API**: `alibaba.category.searchByKeyword`
- 命名空间: `com.alibaba.product`
- 方式: POST
- 参数: `keyword` (String) - 关键词
- 响应结构: `{"products": [{"categoryID": 123, "name": "xxx", "isLeaf": true, "categoryType": "3"}], "success": "true"}`
- 注意: 响应直接是 products/success，**无外层 result 包裹**

### 调用示例

```python
url_path = f'param2/1/com.alibaba.product/alibaba.category.searchByKeyword/{AK}'
url = f'https://gw.open.1688.com/openapi/{url_path}'
params = {'access_token': TK, 'app_key': AK, 'keyword': '手机天线'}
# 签名后POST请求
r = requests.post(url, data=params)
data = r.json()
# data['products'][0]['categoryID'] 返回类目ID
```

### 匹配逻辑

- 优先选 `isLeaf=true` 且 `categoryType="3"` 的叶子类目
- 可根据关键词在结果中筛选含特定词的类目（如"天线"）

### 自动匹配流程脚本

`scripts/scrape_and_match_cat.py`:
1. 抓取官网产品页面 → 提取关键词(meta标签)
2. 关键词存入Excel Col 15
3. 调用 `alibaba.category.searchByKeyword` API查询类目
4. 回填 Col 4(类目ID) + Col 5(类目名)
5. 保存为新Excel文件

```bash
python scripts/scrape_and_match_cat.py
```

### 已验证可用的类目

| 类目ID | 类目名称 | 适用产品 |
|--------|---------|---------|
| 1035216 | 路由器天线/卫星天线 | FPC天线、WiFi天线 |
| 124734049 | 数码天线 | 手机天线、数码设备天线 |
| 1032123 | 车用天线 | 车载天线 |

---

## 类目信息

### 路由器天线类目（正确）
- 类目ID：`1035216`
- 类目路径：电子元器件(986) > 对讲通信(10616) > 天线(10662) > 路由器天线
- industryCategoryId：`10662`
- 属性：品牌(p-2176)、型号(p-3151)、频率范围(p-2166,MHz)、长度(p-386,mm)、增益(p-3429)、输出阻抗(p-2673,Ω)、工作电压(p-1095,V)、最大功率(p-3795,W)
- **无SKU规格属性（saleProp）**，不支持多SKU

### 家具五金类目（旧/错误）
- 类目ID：`1036016`（办公家具相关，之前FPC天线产品误用此分类）

### 通用
- 运费模板ID：`13900148`
- 发货地址ID：`33847521`
- scene：`popular`

如类目变更，需重新获取 `getSchema` 以取得正确的 catProp 选项。

## 更新Excel图片

运行 `scripts/update_excel_pics.py <excel路径> <列范围> <URL或本地路径>`

### 用法示例

```bash
# 单列更新，所有行的H列设为同一URL
python scripts/update_excel_pics.py test.xlsx H https://cbu01.alicdn.com/img/xxx.jpg

# 多列更新，H-L列全部设为同一URL
python scripts/update_excel_pics.py test.xlsx H:L https://cbu01.alicdn.com/img/xxx.jpg

# 多列不同URL，H列用第1个URL，I列用第2个URL...
python scripts/update_excel_pics.py test.xlsx H,I,J,K,L url1.jpg url2.jpg url3.jpg url4.jpg url5.jpg

# 使用本地图片路径
python scripts/update_excel_pics.py test.xlsx H:L D:\\images\\aw168_img_16.jpg
```

### 功能说明

- 更新指定列的图片URL
- 自动下载图片并嵌入到Excel单元格显示
- 支持URL和本地文件路径
- 图片显示尺寸：150x150像素，行高110


### 随机选图发布（从分类子文件夹自动选图）

图片需先分类到子文件夹：instrument/ patent/ certificate/ other/

`ash
# 随机选图 + 上传1688 + 更新Excel + 发布
python batch_publish.py D:\wujm\安威\helper\1688_product_upload.xlsx --random-pics

# 自定义各类图片数量
python batch_publish.py D:\wujm\安威\helper\1688_product_upload.xlsx --random-pics --instrument-count 3 --patent-count 1 --certificate-count 2

# 仅选图不上传（测试用）
python batch_publish.py D:\wujm\安威\helper\1688_product_upload.xlsx --random-pics --skip-upload

# 指定图片根目录
python batch_publish.py D:\wujm\安威\helper\1688_product_upload.xlsx --random-pics --images-dir D:\other\images
`

选图逻辑：
- 主图1：从instrument中随机选1张（产品场景图）
- 主图2-3：从instrument中继续随机选（应用场景+公司实力）
- 主图4-5：从patent中随机选2张
- 主图6：从certificate中随机选1张
- 不够6张时从other补充
