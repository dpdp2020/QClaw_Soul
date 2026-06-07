# -*- coding: utf-8 -*-
"""批量导入商品到1688 - 最终版
从Excel读取商品数据 → 上传图片到阿里图片空间 → 发布商品
"""
import json, hashlib, hmac, time, requests, os, openpyxl, urllib.request

# ========== 配置 ==========
AK = '4962785'; AS = 'W6v0SLfR4w'; TK = '255bdc2a-7e4a-4a8e-b476-fb0b4efa366b'
CAT_ID = 1036016; SCENE = 'popular'; FREIGHT_ID = 13900148; SEND_ADDRESS_ID = 33847521
EXCEL_PATH = r'D:\wujm\安威\helper\1688_product_upload_5G_antenna.xlsx'
IMAGE_DIR = r'D:\wujm\安威\helper\images'

def api_post(api_name, biz_params, ns='com.alibaba.product'):
    url_path = f'param2/1/{ns}/{api_name}/{AK}'
    url = f'https://gw.open.1688.com/openapi/{url_path}'
    ts = str(int(time.time() * 1000))
    all_p = {'access_token': TK, 'app_key': AK, '_aop_timestamp': ts}
    all_p.update(biz_params)
    s = sorted(all_p.items(), key=lambda x: x[0])
    sig = hmac.new(AS.encode(), (url_path + ''.join([k+str(v) for k,v in s])).encode(), hashlib.sha1).hexdigest().upper()
    all_p['_aop_signature'] = sig
    resp = requests.post(url, data=all_p, timeout=30)
    return resp.json()

def download_image(url, save_path):
    if url.startswith('http'):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=15) as r, open(save_path, 'wb') as f:
                f.write(r.read())
            return True
        except:
            return False
    return False

# ========== 读取Excel ==========
print('=== Reading Excel ===')
wb = openpyxl.load_workbook(EXCEL_PATH)
ws = wb.active
COL = {'title': 1, 'price': 4, 'stock': 5, 'sku': 6, 'image_url': 7, 'description': 8, 'weight': 9, 'brand': 11, 'model': 12, 'origin': 13, 'template': 14}
products = []
for i, row in enumerate(ws.iter_rows(values_only=True)):
    if i == 0: continue
    if row[COL['title']] is None: continue
    products.append({
        'row': i + 1,
        'raw_title': str(row[COL['title']] or '').strip(),
        'price': float(row[COL['price']] or 0),
        'stock': int(row[COL['stock']] or 0),
        'sku': str(row[COL['sku']] or '').strip(),
        'image_url': str(row[COL['image_url']] or '').strip(),
        'description': str(row[COL['description']] or '').strip(),
        'weight': float(row[COL['weight']] or 0.1),
        'brand': str(row[COL['brand']] or '').strip(),
        'model': str(row[COL['model']] or '').strip(),
        'origin': str(row[COL['origin']] or '').strip(),
        'freight_id': int(row[COL['template']]) if row[COL['template']] else FREIGHT_ID,
    })

print(f'Found {len(products)} products')
for p in products:
    print(f"  Row{p['row']}: {p['sku']} price={p['price']}")

# ========== 获取类目Schema ==========
print('\n=== Getting Schema ===')
r_schema = api_post('alibaba.new.product.getSchema', {
    'catId': CAT_ID, 'scene': SCENE, 'offerId': 657003000582, 'bizParam': '{}'
})
bd = json.loads(r_schema['result']['bizData'])
cp_schema = bd['data']['catProp']
cat_prop_options = {}
for prop in cp_schema.get('fields', {}).get('dataSource', []):
    pname = prop.get('name', '')
    cat_prop_options[pname] = {
        'required': prop.get('required', False),
        'type': prop.get('fieldType', 'string'),
        'options': {o['value']: o['text'] for o in prop.get('dataSource', [])}
    }

def build_cat_prop(product, cat_opts):
    cp = {}
    for pname, pinfo in cat_opts.items():
        if not pinfo['required']: continue
        ptype = pinfo['type']
        opts = pinfo['options']
        if ptype == 'enum' and opts:
            if pname == 'p-20021':
                for val, txt in opts.items():
                    for kw in ['黑', '银', '白', '金', '红', '蓝', '灰']:
                        if kw in txt: cp[pname] = {'value': val, 'text': txt}; break
                    else: continue
                    break
                else:
                    first_val = next(iter(opts.keys()))
                    cp[pname] = {'value': first_val, 'text': opts[first_val]}
            else:
                first_val = next(iter(opts.keys()))
                cp[pname] = {'value': first_val, 'text': opts[first_val]}
        elif pname == 'p-2176':
            cp[pname] = {'value': -1, 'text': product['brand'], 'custom': True}
        elif pname == 'p-1998': cp[pname] = product['sku']
        elif pname == 'p-3151': cp[pname] = product['model']
        elif pname == 'p-346': cp[pname] = product['origin']
    return cp

def make_title(sku, raw_title):
    """从SKU+原始标题生成ASCII安全标题（最大50字节）"""
    # 提取关键词（英文字符）
    import re
    words = re.findall(r'[A-Za-z0-9\-\/\s]+', raw_title)
    ascii_part = ' '.join(words).strip()
    # 截取到50字节
    result = ''
    for ch in ascii_part:
        test = result + ch
        if len(test.encode('utf-8')) > 50: break
        result = test
    if not result:
        result = sku
    return result[:50]

# ========== 图片上传 ==========
print('\n=== Uploading Images ===')
image_map = {}
sku_local = {'AW-FPC-5GNR-LTE': os.path.join(IMAGE_DIR, 'product_2.jpg')}
for p in products:
    img_url = p['image_url']
    if not img_url: image_map[img_url] = None; continue
    if img_url in image_map: continue

    local_path = None
    if os.path.exists(img_url):
        local_path = img_url
    elif os.path.exists(os.path.join(IMAGE_DIR, os.path.basename(img_url))):
        local_path = os.path.join(IMAGE_DIR, os.path.basename(img_url))
    elif img_url.startswith('http'):
        fname = f'temp_{p["row"]}_{os.path.basename(img_url) or "img.jpg"}'
        local_path = os.path.join(IMAGE_DIR, fname)
        if not os.path.exists(local_path): download_image(img_url, local_path)
    if not local_path or not os.path.exists(local_path):
        fallback = sku_local.get(p['sku'])
        if fallback and os.path.exists(fallback): local_path = fallback

    if local_path and os.path.exists(local_path):
        with open(local_path, 'rb') as f: img_bytes = f.read()
        if len(img_bytes) > 5 * 1024 * 1024: image_map[img_url] = None; continue
        ts = str(int(time.time() * 1000))
        upload_url = f'https://gw.open.1688.com/openapi/param2/1/com.alibaba.product/alibaba.photobank.photo.add/{AK}'
        params = {'albumID': '-1', 'access_token': TK, 'app_key': AK, '_aop_timestamp': ts, 'name': os.path.basename(local_path), 'webSite': '1688'}
        s = sorted(params.items(), key=lambda x: x[0])
        sig = hmac.new(AS.encode(), (f'param2/1/com.alibaba.product/alibaba.photobank.photo.add/{AK}' + ''.join([k+str(v) for k,v in s])).encode(), hashlib.sha1).hexdigest().upper()
        params['_aop_signature'] = sig
        r = requests.post(upload_url, files={'imageBytes': (os.path.basename(local_path), img_bytes, 'image/jpeg')}, data=params, timeout=30)
        try:
            jr = r.json()
            photo_url = jr.get('image', {}).get('url', '') or jr.get('result', {}).get('url', '')
            if photo_url:
                print(f'  [OK] Row{p["row"]}: {photo_url}')
                image_map[img_url] = photo_url
            else:
                print(f'  [FAIL] Row{p["row"]}: {jr}'); image_map[img_url] = None
        except:
            print(f'  [FAIL] Row{p["row"]}: {r.text[:100]}'); image_map[img_url] = None
    else:
        print(f'  [NOT FOUND] Row{p["row"]}: {img_url}'); image_map[img_url] = None
    time.sleep(0.5)

# ========== 发布商品 ==========
print('\n=== Publishing Products ===')
results = []
for p in products:
    print(f'\n--- Row{p["row"]}: {p["sku"]} ---')
    img_rel_url = image_map.get(p['image_url'])
    if not img_rel_url:
        print(f'  [SKIP] Image upload failed')
        results.append({'row': p['row'], 'sku': p['sku'], 'success': False, 'error': 'Image upload failed'})
        continue

    # 生成安全的ASCII标题
    title = make_title(p['sku'], p['raw_title'])
    print(f'  Title [{len(title.encode("utf-8"))} bytes]: {title}')

    cp = build_cat_prop(p, cat_prop_options)
    body = {
        'formValues': {
            'title': title,
            'primaryPicture': {'imageList': [{'url': img_rel_url}]},
            'description': {'detailList': [{'id': '0', 'title': 'Product Details', 'content': f"<p>{p['description'][:8000]}</p>", 'isRequired': True}]},
            'catProp': cp,
            'skuTable': [{'sku_props': [], 'sku_amountOnSale': p['price'], 'sku_cargoNumber': p['sku'], 'sku_status': 1}],
            'onlineTrade': {'value': 17410}, 'cbuUnit': {'unit': '个'},
            'quotationType': {'value': 2}, 'invReduce': {'value': '1', 'text': '下单时扣减'},
            'freight': {'freightType': 'T', 'freightId': p['freight_id'] or FREIGHT_ID},
            'upshelfTime': {'value': 1, 'subText': '商品已经开售'},
            'cbuSendAddress': {'value': SEND_ADDRESS_ID},
            'beginAmount': 1, 'weight': p['weight'], 'suttleWeight': p['weight'],
            'volume': {'height': 10, 'width': 100, 'length': 200},
            'totalSales': p['stock'],
            'priceRange': [{'pricerange_beginAmount': 1, 'pricerange_price': p['price']}],
            'batchSale': {'enable': True, 'sellUnit': '个', 'scale': '1'},
            'lightCustom': {'text': '不支持', 'value': -9999},
            'officialLogistics': {'skuInfo': [{'length': 200, 'width': 100, 'height': 10, 'weight': int(p['weight']*1000), 'volume': 200000, 'sku_props': []}]}
        },
        'global': {'systemParam': {'catId': CAT_ID, 'contextPath': '/popular'}}
    }
    r = api_post('alibaba.new.product.add', {
        'catId': CAT_ID, 'scene': SCENE, 'dataBody': json.dumps(body),
        'bizParam': '{}', 'productSourceChannels': '[]'
    })
    success = r.get('result', {}).get('success', False)
    if success:
        bd = r['result']['bizData']
        dj = json.loads(bd.get('dataJson', '{}'))
        item_id = dj.get('itemId', '?')
        status = dj.get('offerStatus', '?')
        print(f'  [SUCCESS!] itemId={item_id} status={status}')
        results.append({'row': p['row'], 'sku': p['sku'], 'title': title, 'success': True, 'itemId': item_id, 'status': status})
    else:
        bd_str = r.get('result', {}).get('bizData', '')
        err = r.get('result', {}).get('bizCode', '?')
        if bd_str:
            try:
                bj = json.loads(bd_str) if isinstance(bd_str, str) else bd_str
                dj = json.loads(bj.get('dataJson', '{}'))
                fe = dj.get('data', {}).get('models', {}).get('formError', {})
                if fe:
                    for k, v in fe.items():
                        for m in v.get('message', []): err = f'{k}:{m.get("msg","")}'
                        for ik, iv in v.get('itemMessage', {}).items():
                            for m in iv.get('message', []): err = f'{k}.{ik}:{m.get("msg","")}'
            except: pass
        print(f'  [FAIL] {err}')
        results.append({'row': p['row'], 'sku': p['sku'], 'title': title, 'success': False, 'error': err})
    time.sleep(1)

# ========== 结果汇总 ==========
print('\n\n=== FINAL RESULTS ===')
ok = [r for r in results if r['success']]
fail = [r for r in results if not r['success']]
print(f'Success: {len(ok)}/{len(results)}')
for r in ok: print(f'  OK: {r["sku"]} -> itemId={r.get("itemId")}')
print(f'Failed: {len(fail)}/{len(results)}')
for r in fail: print(f'  FAIL: {r["sku"]} -> {r.get("error","")[:80]}')
with open(r'D:\wujm\安威\helper\batch_import_result.json', 'w', encoding='utf-8') as f:
    json.dump(results, f, ensure_ascii=False, indent=2)
print('\nResults saved to batch_import_result.json')