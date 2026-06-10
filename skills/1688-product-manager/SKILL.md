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
| `data_wash.py` | **数据清洗**：补全空白包装信息（重量/体积）并标注估算值 |
| `delete_product.py` | 删除指定商品ID |
| `list_products.py` | 查询商品列表 |
| `get_product.py` | 查询商品详情 |
| `upload_image.py` | 上传图片到1688图片银行 |
| `modify_stock.py` | 修改商品库存（modifystock API） |
| `update_excel_pics.py` | 更新Excel图片URL并同步显示图片 |
| `scrape_and_match_cat.py` | 抓取官网产品 → 提取关键词 → 匹配1688类目 |

## 使用流程

### 0️⃣ 数据清洗（发布前必做）

**目的**：自动补全Excel中空白的包装字段（重量、体积长宽高），避免发布后因包装信息缺失导致物流计费异常。

**触发条件**：Excel中存在以下空白字段时自动补全：
- Col17 重量(kg)
- Col21 体积长(cm)
- Col22 体积宽(cm)
- Col23 体积高(cm)
- Col26 体积(m³)（自动计算）

**执行方式**：
```bash
# 独立运行数据清洗
python scripts/data_wash.py D:\wujm\安威\helper\1688_product_upload_cat_1780992963.xlsx

# 集成到批量发布（自动执行Step 0）
python scripts/batch_publish.py D:\wujm\安威\helper\1688_product_upload_cat_1780992963.xlsx
```

**清洗逻辑**：
1. 读取每行类目ID（Col4）和商品标题（Col3）
2. 根据类目ID匹配 `CATEGORY_PACKAGING_DEFAULTS` 中的默认值
3. 仅补全**空白字段**（已有值不覆盖）
4. 补全的字段标注**土黄色**（RGB 204,153,0）表示估算值
5. 自动计算体积(m³) = (长×宽×高 cm) / 1,000,000
6. 保存前创建备份文件 `.bak_wash`

**默认值参考库**（基于online-search同类目商品数据，2026-06-10更新）：
| 类目ID | 类目名称 | 默认尺寸(cm) | 默认重量(kg) | 适用产品 |
|--------|---------|-------------|---------------|----------|
| 1035216 | 路由器天线 | 12×8×2 | 0.01 | 双频FPC天线 |
| 124734049 | 数码天线 | 10×7×2 | 0.005 | GSM/WiFi FPC天线 |
| _default_small | 通用小件 | 10×7×2 | 0.005 | FPC天线（默认） |
| _default_medium | 通用中件 | 12×8×3 | 0.01 | 带配件天线 |

> 💡 **调整默认值**：直接编辑 `data_wash.py` 中的 `CATEGORY_PACKAGING_DEFAULTS` 字典，根据你的实际发货包装调整。

---

### 1️⃣ 发布新商品

**完整流程**（含数据清洗）：
1. 准备 Excel 文件（格式见下方「Excel 格式」）
2. 运行 `scripts/batch_publish.py <excel路径>`
   - **Step 0**: 自动执行数据清洗（`data_wash.py`），补全包装信息
   - **Step 1+**: 上传图片 → 获取类目属性 → 发布商品 → 输出结果
3. 检查输出结果（`*_publish_result.json`）

**仅数据清洗**（不发布）：
```bash
python scripts/data_wash.py <excel路径>
```

发布完成后结果保存为 `<excel文件名>_publish_result.json`。

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
| 重量(kg) | 重量、重量kg、weight、重量(kg) |
| 体积长(cm) | 体积长、长、length、体积长(cm) |
| 体积宽(cm) | 体积宽、宽、width、体积宽(cm) |
| 体积高(cm) | 体积高、高、height、体积高(cm) |
| 体积(m³) | 体积、体积m3、volume、体积(m³) |
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

## 修改价格和库存

通过 `product.increment.editInfo` 增量编辑接口实现。

### 修改价格
```python
# formValues 中传入 priceRange 和 skuTable
api_post('product.increment.editInfo', {
    'catId': '类目ID',
    'scene': 'cbu',
    'offerId': '商品ID',
    'dataBody': json.dumps({
        'formValues': {
            'priceRange': [{'priceRange_beginAmount': 1, 'priceRange_price': 新价格}],
            'skuTable': [{'sku_props': [], 'sku_amountOnSale': 新价格, 'sku_status': 1}],
        }
    }),
    'bizParam': '{}',
})
```

### 修改库存
```python
# formValues 中传入 totalSales
api_post('product.increment.editInfo', {
    'catId': '类目ID',
    'scene': 'cbu',
    'offerId': '商品ID',
    'dataBody': json.dumps({
        'formValues': {'totalSales': 新库存值}
    }),
    'bizParam': '{}',
})
```

**注意**：API 名称是 `product.increment.editInfo`（无 `alibaba.` 前缀），与 `alibaba.new.product.edit` 不同。返回结构：`{"result": "{json}", "success": true}`，result 为字符串需二次解析。

## 已知限制

- **`alibaba.new.product.edit` 不可靠**：API 返回 `success:true` 但实际不写入字段（货号、图片等均不生效）。已测试 formValues.productCargoNumber、global.systemParam.productCargoNumber 等多种方式，均不生效。
- **`product.increment.editInfo` 可用，但支持字段有限**：增量编辑接口支持 `title`、`description`、`priceRange`、`totalSales`，**不支持** `catProp`（类目属性）、`cbuSendAddress`（发货地址）、`freightTemplateId`（运费模板）、`officialLogistics`（件重尺）。如要修改这些字段，最靠谱方式是**删除重发**。
- **`officialLogistics`（件重尺）无法通过API写入**：非官方物流类目（`isOfficialLogisticsCategory=false`）不支持通过API设置件重尺，必须在1688后台手动填写。
- **`cbuSendAddress`（发货地址）发布时可写入**：`alibaba.new.product.add` 支持 `cbuSendAddress: {"value": <addressId>}`，但 `product.increment.editInfo` **不支持**修改已发布商品的发货地址。
- **数据清洗仅补全空白字段**：`data_wash.py` 不会覆盖已有值，如需强制刷新已有值，需手动编辑Excel或临时注释跳过逻辑。
- **包装默认值基于行业参考数据**：土黄色标注的字段为估算值，建议根据实际发货包装调整 `CATEGORY_PACKAGING_DEFAULTS`。
- **修改商品请手动登录** https://work.1688.com/product/manage.htm 操作（非上述支持的操作）。

## 实战经验（2026-06-10 沉淀）

### 删除重发流程

当需要通过API"修改"不支持的字段时（如件重尺、发货地址、类目属性），唯一靠谱方案是**删除旧商品 → 重新发布**。`republish_with_packing.py` 已实现此流程。

**用法**：
```bash
python scripts/republish_with_packing.py <Excel路径>
```

**流程**：
1. 读取Excel Col8（旧商品ID）→ 调用 `alibaba.product.delete` 删除
2. 根据Excel每行数据重新构建 `dataBody` → 调用 `alibaba.new.product.add` 发布
3. 将新商品ID回填Excel Col8 → 立即保存Excel

**注意**：必须在每次发布成功后**立即保存Excel**，防止脚本崩溃导致Col8未更新，下次运行会再次创建新商品（产生重复）。

---

### Excel操作注意事项

**⚠️ 操作Excel前必须先关闭Excel程序**，否则会导致文件损坏（`[Content_Types].xml` 缺失，ZipFile错误）。

**防护机制**（已在 `republish_with_packing.py` 中实现）：
1. 保存前创建 `.bak` 备份文件
2. 发布成功后立即 `wb.save()`，而非等全部完成后才保存
3. 如遇损坏，从最近的 `.bak` 或 `.bak_republishN` 恢复

**恢复命令**：
```powershell
Copy-Item "<excel>.bak" "<excel>" -Force
```

---

### API调用注意事项

#### 1. 必需参数
- **`scene`**：`alibaba.new.product.add` 必须传 `scene='popular'`（或其他有效值），否则返回 `Required argument scene` 错误。
- **`dataBody`**：商品详情必须打包成 `dataBody: json.dumps(body)` 传入，不能分散为独立参数。

#### 2. 签名计算
- 所有参数（含中文）按字典序排序后拼接
- 前缀：`param2/1/{namespace}/{api_name}/{AK}`
- HMAC-SHA1，输出大写十六进制
- **注意**：`requests.post(data=p)` 会对中文做URL编码，但签名计算时用的是原始UTF-8字符串，两者必须一致（原始脚本已处理此问题，不要自行修改签名逻辑）。

#### 3. 查询接口延迟
- `alibaba.product.get` **有缓存/延迟**，刚发布的商品可能几分钟内查不到
- **发布成功应以 `alibaba.new.product.add` 返回的 `itemId` 为准**，不要依赖 `alibaba.product.get` 立即验证
- 验证商品是否存在，最可靠方式是让用户**截图1688后台商品列表**

#### 4. 风控/限流
- 短时间内频繁删除+重发（10+次/小时）可能触发1688风控
- 风控表现：API返回 `success:true` + `itemId`，但商品实际未创建（查不到）
- **规避方案**：
  1. 每次操作后间隔至少1-2分钟
  2. 如遇风控，停止操作，等待几小时或次日再试
  3. 使用 `republish_with_packing.py` 批量处理，不要单次单商品反复重发

---

### 删除商品API返回格式

`alibaba.product.delete` 返回格式：**注意判断 `result.isSuccess`，不是外层 `isSuccess`**。
```json
{
  "result": {
    "isSuccess": true,
    "reason": "操作成功!"
  }
}
```

错误时也可能返回 `{"isSuccess": true, "reason": "操作失败!"}`（外层 `isSuccess` 始终是 `true`，必须看 `result.isSuccess`）。

---

### 重复商品问题排查

**症状**：1688后台出现多个相同商品（不同ID）。

**原因**：脚本在"发布成功 → 保存Excel"之间崩溃，导致：
1. Col8仍是旧ID
2. 新商品已创建成功（API返回了itemId）
3. 下次运行脚本 → 又创建新商品 → 重复

**解决方案**：
1. 登录1688后台，按发布时间排序，删除重复商品（保留最新那个）
2. 手动将保留的商品ID填入Excel Col8
3. 以后运行前确保脚本有"发布成功后立即保存"逻辑

**预防**：已在 `republish_with_packing.py` 中添加 `_save_excel()` 函数，每次发布成功后立即调用。

---

### 类目属性（catProp）注意事项

- `alibaba.new.product.getSchema` 返回的属性结构复杂，需从 `formValues.catProp` 中提取 `value`/`text`
- 部分类目（如124734049 数码天线）的 `getSchema` 返回**0个属性**（正常现象，不要认为是API错误）
- 属性ID格式：`p-xxxx`（如 `p-3151` 型号、`p-1398` 货号）
- **`product.increment.editInfo` 不支持修改 `catProp`**，必须删除重发

---

### 调试技巧

1. **API返回假成功**：用 `alibaba.product.get` 验证商品是否存在，不要只看 `add` 接口的返回
2. **Excel损坏**：检查是否有 `.bak` 文件，或重新运行 `data_wash.py`（会创建新的 `.bak_wash`）
3. **签名错误**：检查是否漏传 `scene` 或 `dataBody`；中文字符是否正常编码
4. **图片上传失败**：检查 `picUrl` 是否是1688图片银行完整URL（以 `https://cbu01.alicdn.com/` 开头）

## 货号规则

- **货号 = 型号**，有型号才填，没有就不填
- **SKU ≠ 型号**，SKU 是备用数据项，不是货号
- 1688 的"货号"取自**类目属性 `p-1398`** 的值，不是外层参数 `productCargoNumber` 或 `outerId`
- `batch_publish.py` 中 `outerId` 用型号优先、SKU 兜底（保证不空）
- 从官网抓取时，SKU 可能来自 URL 编号（如 aw168.cn/pro/wifi/237.html → AW237），这不是型号

## 产品图规则

- 所有产品图必须全部放入 `primaryPicture.imageList`，不能只放1张主图
- 1688 前台的产品图展示来自 `imageList`，不是 description 中的 `<img>` 标签
- Excel 中主图1-6列的图片都应传入 `imageList`
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

```bash
# 随机选图 + 上传1688 + 更新Excel + 发布
python batch_publish.py D:\wujm\安威\helper\1688_product_upload.xlsx --random-pics

# 自定义各类图片数量
python batch_publish.py D:\wujm\安威\helper\1688_product_upload.xlsx --random-pics --instrument-count 3 --patent-count 1 --certificate-count 2

# 仅选图不上传（测试用）
python batch_publish.py D:\wujm\安威\helper\1688_product_upload.xlsx --random-pics --skip-upload

# 指定图片根目录
python batch_publish.py D:\wujm\安威\helper\1688_product_upload.xlsx --random-pics --images-dir D:\other\images
```

选图逻辑：
- 主图1：从instrument中随机选1张（产品场景图）
- 主图2-3：从instrument中继续随机选（应用场景+公司实力）
- 主图4-5：从patent中随机选2张
- 主图6：从certificate中随机选1张
- 不够6张时从other补充
