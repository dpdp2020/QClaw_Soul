# -*- coding: utf-8 -*-
"""
批量发布商品到1688 - 通用版 v2（含查重）
用法: python batch_publish.py <Excel文件路径>
自动识别列格式，支持任意列顺序和中文表头。
查重：发布前按SKU比对已上架商品，命中则跳过。
"""
import json, hashlib, hmac, time, requests, openpyxl, sys, re

# ========== 凭证 & 配置 ==========
AK = '4962785'; AS = 'W6v0SLfR4w'; TK = '255bdc2a-7e4a-4a8e-b476-fb0b4efa366b'
CAT_ID = 1036016; SCENE = 'popular'; FREIGHT_ID = 13900148; SEND_ADDRESS_ID = 33847521

EXCEL_PATH = sys.argv[1] if len(sys.argv) > 1 else None

# ========== API 签名 ==========
def sign(url_path, params):
    s = sorted(params.items(), key=lambda x: x[0])
    raw = url_path + ''.join([k + str(v) for k, v in s])
    return hmac.new(AS.encode(), raw.encode(), hashlib.sha1).hexdigest().upper()

def api_post(api_name, biz_params, ns='com.alibaba.product'):
    url_path = f'param2/1/{ns}/{api_name}/{AK}'
    url = f'https://gw.open.1688.com/openapi/{url_path}'
    ts = str(int(time.time() * 1000))
    p = {'access_token': TK, 'app_key': AK, '_aop_timestamp': ts}
    p.update(biz_params)
    p['_aop_signature'] = sign(url_path, p)
    r = requests.post(url, data=p, timeout=30)
    return r.json()

# ========== 查重：拉取已上架商品SKU ==========
def get_existing_skus():
    sku_set = set()
    page_no = 1
    page_size = 50
    total = None

    while True:
        r = api_post('alibaba.product.list.get', {
            'pageNo': page_no,
            'pageSize': page_size,
            'statusList': 'PUBLISHED',
        })
        res = r.get('result', {})
        pr = res.get('pageResult', {})
        products = pr.get('resultList', []) or []

        for p in products:
            # 优先用 productCargoNumber（货号）做查重
            cargo = p.get('productCargoNumber', '')
            if cargo:
                sku_set.add(str(cargo).strip())
            # 也用 catProp 的 p-1998（名称）和 p-3151（型号）做补充匹配
            for attr in (p.get('attributes', []) or []):
                aid = str(attr.get('attributeID', ''))
                val = attr.get('value', '')
                if val and aid in ('1998', '3151'):
                    sku_set.add(str(val).strip())

        if total is None:
            total = pr.get('totalCount', 0)
            if total == 0:
                break

        if len(products) < page_size:
            break
        page_no += 1
        if page_no * page_size > total:
            break
        time.sleep(0.3)

    return sku_set

# ========== Excel 列自动识别 ==========
def build_col_map(ws):
    header_map = {
        'title':      ['标题', '商品标题', 'title', '商品名称', '产品名称'],
        'price':      ['价格', '销售价格', '单价', 'price', '批发价', '售价'],
        'stock':      ['库存', '库存数量', 'stock', '可售数量'],
        'sku':        ['sku', 'SKU', '商品编码', '货号', 'SKU编码', 'product_code'],
        'pic_url':    ['主图', '主图URL', '图片', '图片URL', 'pic_url', 'picUrl', '图片地址'],
        'desc':       ['描述', '详情', '详情描述', 'description', '商品描述'],
        'weight':     ['重量', '重量kg', 'weight', '商品重量', '毛重'],
        'brand':      ['品牌', 'brand', '商标'],
        'model':      ['型号', '规格', '规格型号', 'model'],
        'origin':     ['产地', '生产地', 'origin', '货源地'],
        'freight_id': ['运费模板', '运费', 'freight', '运费模板ID'],
        'cat_id':     ['类目ID', '类目', 'category', 'catId'],
    }

    col_map = {}
    first_row = list(ws.iter_rows(min_row=1, max_row=1, values_only=True))[0]
    max_col = ws.max_column

    for col_idx in range(max_col):
        val = str(first_row[col_idx]).strip() if first_row[col_idx] is not None else ''
        if not val:
            continue
        for field, keywords in header_map.items():
            if val in keywords:
                col_map[field] = col_idx
                break
            if field not in col_map and any(kw in val for kw in keywords if len(kw) >= 2):
                col_map[field] = col_idx
                break

    if not col_map:
        if max_col >= 15:
            col_map = {'title':1,'cat_id':2,'price':4,'stock':5,'sku':6,'pic_url':7,'desc':8,'weight':9,'freight_id':10,'brand':11,'model':12,'origin':13}
        elif max_col >= 13:
            col_map = {'title':0,'price':3,'stock':4,'sku':5,'pic_url':6,'desc':7,'weight':8,'brand':10,'model':11,'origin':12}
        elif max_col >= 8:
            col_map = {'title':0,'price':1,'stock':2,'sku':3,'pic_url':4,'desc':5,'weight':6,'brand':7}

    return col_map

# ========== 辅助：安全取单元格值 ==========
def _int(row, col_map, field, default):
    idx = col_map.get(field)
    if idx is None or idx >= len(row): return default
    try: return int(row[idx])
    except Exception: return default

def _float(row, col_map, field, default):
    idx = col_map.get(field)
    if idx is None or idx >= len(row): return default
    try: return float(row[idx])
    except Exception: return default

def _str(row, col_map, field, default):
    idx = col_map.get(field)
    if idx is None or idx >= len(row): return default
    v = row[idx]
    return str(v).strip() if v is not None else default

# ========== 标题生成 ==========
def make_title(sku, raw_title):
    words = re.findall(r'[A-Za-z0-9\-\/\s]+', str(raw_title))
    ascii_part = ' '.join(words).strip()
    result = ''
    for ch in ascii_part:
        test = result + ch
        if len(test.encode('utf-8')) > 50: break
        result = test
    return result[:50] if result else str(sku)

# ========== 类目属性 ==========
def get_cat_schema():
    r = api_post('alibaba.new.product.getSchema', {
        'catId': CAT_ID, 'scene': SCENE, 'offerId': '', 'bizParam': '{}'
    })
    bd_str = r.get('result', {}).get('bizData', '{}')
    bd = json.loads(bd_str) if isinstance(bd_str, str) else (bd_str or {})
    opts = {}
    fields_src = (bd.get('data', {}) or {}).get('catProp', {}) or {}
    for prop in fields_src.get('fields', {}).get('dataSource', []):
        pname = prop.get('name', '')
        opts[pname] = {
            'required': prop.get('required', False),
            'type': prop.get('fieldType', 'string'),
            'options': {o['value']: o['text'] for o in prop.get('dataSource', [])}
        }
    return opts

def build_cat_prop(product, cat_opts):
    cp = {}
    for pname, pinfo in cat_opts.items():
        if not pinfo['required']: continue
        ptype = pinfo['type']
        opts = pinfo['options']
        if ptype == 'enum' and opts:
            first_val = next(iter(opts.keys()))
            cp[pname] = {'value': first_val, 'text': opts[first_val]}
        elif pname == 'p-2176':
            cp[pname] = {'value': -1, 'text': product.get('brand', ''), 'custom': True}
        elif pname == 'p-1998': cp[pname] = product.get('sku', '')
        elif pname == 'p-1398': cp[pname] = product.get('sku', '')  # 货号
        elif pname == 'p-3151': cp[pname] = product.get('model', '')
        elif pname == 'p-346': cp[pname] = product.get('origin', '')
    return cp

# ========== 图片URL处理 ==========
def normalize_pic_url(pic_url):
    if not pic_url: return ''
    s = str(pic_url).strip()
    if s.startswith('img/'): return 'https://cbu01.alicdn.com/' + s
    return s

# ========== 主程序 ==========
def main():
    global EXCEL_PATH
    if not EXCEL_PATH:
        print('用法: python batch_publish.py <Excel文件路径>')
        sys.exit(1)

    print(f'=== 读取Excel: {EXCEL_PATH} ===')
    wb = openpyxl.load_workbook(EXCEL_PATH)
    ws = wb.active

    col_map = build_col_map(ws)
    print(f'列识别结果: {col_map}')

    products = []
    for row in ws.iter_rows(min_row=2, values_only=True):
        if not row: continue
        title_val_col = col_map.get('title', 1)
        title_val = row[title_val_col] if title_val_col < len(row) else None
        if title_val is None: continue

        products.append({
            'title':      _str(row, col_map, 'title', ''),
            'cat_id':     _int(row, col_map, 'cat_id', CAT_ID),
            'price':      _float(row, col_map, 'price', 9.9),
            'stock':      _int(row, col_map, 'stock', 100),
            'sku':        _str(row, col_map, 'sku', ''),
            'pic_url':    _str(row, col_map, 'pic_url', ''),
            'desc':       _str(row, col_map, 'desc', ''),
            'weight':     _float(row, col_map, 'weight', 0.01),
            'freight_id': _int(row, col_map, 'freight_id', FREIGHT_ID),
            'brand':      _str(row, col_map, 'brand', 'ANWEI安威'),
            'model':      _str(row, col_map, 'model', ''),
            'origin':     _str(row, col_map, 'origin', '广东深圳'),
        })

    print(f'共读取 {len(products)} 个商品\n')
    if not products:
        print('[ERROR] 未找到任何商品数据')
        sys.exit(1)

    # ========== 查重 ==========
    print('=== 查重：拉取已上架商品SKU ===')
    try:
        existing_skus = get_existing_skus()
        print(f'已上架商品SKU数: {len(existing_skus)}')
        if existing_skus:
            sample = list(existing_skus)[:5]
            print(f'  示例: {sample}')
    except Exception as e:
        print(f'[WARN] 查重失败，将跳过查重直接发布: {e}')
        existing_skus = set()

    skip_count = 0
    for p in products:
        if p['sku'] and p['sku'] in existing_skus:
            p['_skip'] = True
            skip_count += 1
        else:
            p['_skip'] = False

    if skip_count > 0:
        print(f'查重命中，将跳过 {skip_count} 个已上架商品\n')
    else:
        print('查重通过，无重复商品\n')

    # ========== 获取类目属性 ==========
    print('=== 获取类目Schema ===')
    try:
        cat_opts = get_cat_schema()
        print(f'类目属性数: {len(cat_opts)}')
    except Exception as e:
        print(f'[WARN] 获取类目属性失败: {e}')
        cat_opts = {}

    # ========== 逐条发布 ==========
    results = []
    for p in products:
        if p.get('_skip'):
            print(f'--- SKIP (已上架): {p["sku"]} ({p["title"][:30]}) ---')
            results.append({'sku': p['sku'], 'success': True, 'skipped': True})
            continue

        print(f'\n--- {p["sku"]} ({p["title"][:30]}) ---')

        pic_url = normalize_pic_url(p['pic_url'])
        if not pic_url or not pic_url.startswith('http'):
            print(f'  [SKIP] 主图URL无效: {p["pic_url"]}')
            results.append({'sku': p['sku'], 'success': False, 'error': 'Invalid pic_url'})
            continue

        title = make_title(p['sku'], p['title'])
        print(f'  Title [{len(title.encode("utf-8"))} bytes]: {title}')
        print(f'  Pic: {pic_url[:60]}')

        cp = build_cat_prop(p, cat_opts)
        body = {
            'formValues': {
                'outerId': p['sku'],
                'title': title,
                'primaryPicture': {'imageList': [{'url': pic_url}]},
                'description': {'detailList': [{'id': '0', 'title': 'Details', 'content': f"<p>{p['desc'][:8000]}</p>", 'isRequired': True}]},
                'catProp': cp,
                'skuTable': [{'sku_props': [], 'sku_amountOnSale': p['price'], 'sku_cargoNumber': p['sku'], 'sku_status': 1}],
                'onlineTrade': {'value': 17410},
                'cbuUnit': {'unit': '个'},
                'quotationType': {'value': 2},
                'invReduce': {'value': '1', 'text': '下单时扣减'},
                'freight': {'freightType': 'T', 'freightId': p['freight_id']},
                'upshelfTime': {'value': 1, 'subText': '商品已经开售'},
                'cbuSendAddress': {'value': SEND_ADDRESS_ID},
                'beginAmount': 1,
                'weight': p['weight'],
                'suttleWeight': p['weight'],
                'volume': {'height': 10, 'width': 100, 'length': 200},
                'totalSales': p['stock'],
                'priceRange': [{'pricerange_beginAmount': 1, 'pricerange_price': p['price']}],
                'batchSale': {'enable': True, 'sellUnit': '个', 'scale': '1'},
                'lightCustom': {'text': '不支持', 'value': -9999},
                'officialLogistics': {'skuInfo': [{'length': 200, 'width': 100, 'height': 10, 'weight': int(p['weight']*1000), 'volume': 200000, 'sku_props': []}]}
            },
            'global': {'systemParam': {'catId': p['cat_id'], 'contextPath': '/popular'}}
        }

        r = api_post('alibaba.new.product.add', {
            'catId': p['cat_id'], 'scene': SCENE, 'dataBody': json.dumps(body),
            'bizParam': '{}', 'productSourceChannels': '[]',
            'productCargoNumber': p['sku']
        })

        success = r.get('result', {}).get('success', False)
        if success:
            bd_raw = r['result'].get('bizData', {})
            bd = json.loads(bd_raw) if isinstance(bd_raw, str) else (bd_raw or {})
            dj_raw = bd.get('dataJson', '{}')
            dj = json.loads(dj_raw) if isinstance(dj_raw, str) else (dj_raw or {})
            item_id = dj.get('itemId', '?')
            status = bd.get('data', {}).get('offerStatus', '?')
            print(f'  [SUCCESS!] itemId={item_id} status={status}')
            results.append({'sku': p['sku'], 'success': True, 'itemId': item_id, 'status': status})
        else:
            err = r.get('result', {}).get('bizCode', '?')
            print(f'  [FAIL] {err}')
            results.append({'sku': p['sku'], 'success': False, 'error': err})

        time.sleep(1)

    # ========== 汇总 ==========
    print(f'\n=== 完成 ===')
    ok = sum(1 for r in results if r.get('success') and not r.get('skipped'))
    skipped = sum(1 for r in results if r.get('skipped'))
    fail = sum(1 for r in results if not r.get('success'))
    print(f'成功: {ok} | 跳过(已上架): {skipped} | 失败: {fail}')

    for r in results:
        if r.get('skipped'):
            print(f'  SKIP: {r["sku"]} (已上架)')
        elif r.get('success'):
            print(f'  OK: {r["sku"]} -> itemId={r.get("itemId")}')
        else:
            print(f'  FAIL: {r["sku"]} -> {r.get("error","")[:80]}')

    result_file = EXCEL_PATH.replace('.xlsx', '_publish_result.json')
    with open(result_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f'\n结果已保存: {result_file}')

if __name__ == '__main__':
    main()
