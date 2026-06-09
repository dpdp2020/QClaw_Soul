# -*- coding: utf-8 -*-
"""
批量发布商品到1688 - 通用版 v2（含查重）
用法: python batch_publish.py <Excel文件路径>
自动识别列格式，支持任意列顺序和中文表头。
查重：发布前按SKU比对已上架商品，命中则跳过。
"""
import json, hashlib, hmac, time, requests, openpyxl, sys, re, random, glob, argparse, os

# ========== 凭证 & 配置 ==========
AK = '4962785'; AS = 'W6v0SLfR4w'; TK = '255bdc2a-7e4a-4a8e-b476-fb0b4efa366b'
CAT_ID = 1035216; SCENE = 'popular'; FREIGHT_ID = 13900148; SEND_ADDRESS_ID = 33847521

# CLI arguments
_parser = argparse.ArgumentParser(description='batch publish products to 1688')
_parser.add_argument('excel', nargs='?', help='Excel file path')
_parser.add_argument('--random-pics', action='store_true', help='randomly select images from classified subfolders')
_parser.add_argument('--images-dir', default=r'D:\wujm\安威\helper\images', help='images root dir')
_parser.add_argument('--instrument-count', type=int, default=3, help='instrument images (default: 2)')
_parser.add_argument('--patent-count', type=int, default=2, help='patent images (default: 2)')
_parser.add_argument('--certificate-count', type=int, default=1, help='certificate images (default: 1)')
_parser.add_argument('--product-dir', default=None, help='product images dir (fixed main1 images)')
_parser.add_argument('--skip-upload', action='store_true', help='skip 1688 upload (for testing)')
_args = _parser.parse_args()
EXCEL_PATH = _args.excel

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
            # 过滤已删除的商品
            if p.get('status') == 'member deleted':
                continue
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
        'pic_url':    ['主图', '主图URL', '图片', '图片URL', 'pic_url', 'picUrl', '图片地址', '主图1(产品宣传图)'],
        'pic_url2':   ['主图2', '主图2URL', '副图2', '应用场景图'],
        'pic_url3':   ['主图3', '主图3URL', '副图3', '公司实景'],
        'pic_url4':   ['主图4', '主图4URL', '副图4', '资质'],
        'pic_url5':   ['主图5', '主图5URL', '副图5', '产品介绍'],
        'pic_url6':   ['主图6', '主图6URL', '副图6', '证书'],
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

def _str_multi(row, col_map, fields):
    urls = []
    for f in fields:
        v = _str(row, col_map, f, '')
        if v: urls.append(v)
    return urls

# ========== 标题生成 ==========
def make_title(sku, raw_title):
    """标题生成：最多60字节(约20个汉字)，1688审核严格"""
    result = str(raw_title).strip() if raw_title else str(sku)
    # 截断到60字节(1688实际限制比文档更严)
    encoded = result.encode('utf-8')
    if len(encoded) > 60:
        result = encoded[:60].decode('utf-8', 'ignore').rstrip()
    return result if result else str(sku)

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
        elif pname == 'p-2176':  # 品牌
            cp[pname] = {'value': -1, 'text': product.get('brand', '安威'), 'custom': True}
        elif pname == 'p-3151':  # 型号
            cp[pname] = product.get('model', '')
        elif pname == 'p-2166':  # 频率范围(MHz)
            cp[pname] = product.get('freq_range', '600-6000')
        elif pname == 'p-386':   # 长度(mm)
            cp[pname] = product.get('length_mm', '50')
    # 可选属性
    if 'p-1398' in cat_opts: cp['p-1398'] = product.get('sku', '')   # 货号
    if 'p-3429' in cat_opts and product.get('gain'): cp['p-3429'] = product.get('gain')  # 增益
    if 'p-2673' in cat_opts and product.get('impedance'): cp['p-2673'] = product.get('impedance')  # 输出阻抗
    if 'p-1095' in cat_opts and product.get('voltage'): cp['p-1095'] = product.get('voltage')  # 工作电压
    if 'p-3795' in cat_opts and product.get('max_power'): cp['p-3795'] = product.get('max_power')  # 最大功率
    return cp

# ========== 图片URL处理 ==========
def normalize_pic_url(pic_url):
    if not pic_url: return ''
    s = str(pic_url).strip()
    if s.startswith('img/'): return 'https://cbu01.alicdn.com/' + s
    return s

# ========== 主程序 ==========


# ========== 随机选图 ==========
def random_select_images(images_dir, counts=None, product_img=None):
    """从分类子文件夹随机选图 (instrument/patent/certificate)
    
    Args:
        images_dir: 图片根目录
        counts: {"instrument": 2, "patent": 2, "certificate": 1}
        product_img: 主图1固定图片路径（可选，不传则从instrument随机选）
    
    Returns:
        dict: {"all": [6张图路径(主图1-6)], 各类别列表}
    """
    if counts is None:
        counts = {"instrument": 2, "patent": 2, "certificate": 1}
    
    result = {"instrument": [], "patent": [], "certificate": []}
    
    for cat, num in counts.items():
        cat_dir = os.path.join(images_dir, cat)
        if not os.path.isdir(cat_dir):
            print(f'[WARN] subfolder not found: {cat_dir}')
            continue
        files = []
        for ext in ('*.jpg', '*.jpeg', '*.png', '*.bmp'):
            files.extend(glob.glob(os.path.join(cat_dir, ext)))
        if not files:
            print(f'[WARN] no images in: {cat_dir}')
            continue
        selected = random.sample(files, min(num, len(files)))
        result[cat] = selected
    
    # Build 6-image list: main1 fixed (product_img) or random from instrument
    all_imgs = []
    if product_img and os.path.isfile(product_img):
        all_imgs.append(product_img)
        print(f'[INFO] Main1 fixed: {os.path.basename(product_img)} (product)')
    else:
        # Fallback: use first instrument image as main1
        if result["instrument"]:
            all_imgs.append(result["instrument"][0])
            result["instrument"] = result["instrument"][1:]
    
    # Add remaining images: instrument + patent + certificate
    all_imgs.extend(result["instrument"])
    all_imgs.extend(result["patent"])
    all_imgs.extend(result["certificate"])
    
    # Pad to 6 with 'other' if needed
    while len(all_imgs) < 6:
        other_dir = os.path.join(images_dir, "other")
        if os.path.isdir(other_dir):
            others = []
            for ext in ('*.jpg', '*.jpeg', '*.png', '*.bmp'):
                others.extend(glob.glob(os.path.join(other_dir, ext)))
            remaining = [f for f in others if f not in all_imgs]
            if remaining:
                all_imgs.append(remaining[0])
                continue
        break
    
    result["all"] = all_imgs[:6]
    
    print(f'[INFO] Selected {len(all_imgs[:6])} images:')
    for i, img in enumerate(result["all"], 1):
        cat_name = "product" if i == 1 and product_img else "other"
        if i > 1 or not product_img:
            for c in ["instrument", "patent", "certificate"]:
                if c in img.replace("\\", "/"):
                    cat_name = c
                    break
        print(f'  main{i}: {os.path.basename(img)} ({cat_name})')
    
    return result
def upload_images_to_1688(image_paths):
    """批量上传图片到1688图片银行, 返回URL列表"""
    upload_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "upload_image.py")
    uploaded = []
    for img_path in image_paths:
        if not img_path or not os.path.isfile(img_path):
            print(f'[WARN] image not found: {img_path}')
            uploaded.append('')
            continue
        print(f'  Uploading: {os.path.basename(img_path)} ...', end=' ', flush=True)
        try:
            import subprocess
            r = subprocess.run(
                [sys.executable, upload_script, img_path],
                capture_output=True, text=True, timeout=60, encoding='utf-8', errors='replace'
            )
            full = (r.stdout or '') + (r.stderr or '')
            import re as _re
            m = _re.search(r'(img/ibank/[\w/.!-]+)', full)
            if m:
                uploaded.append(m.group(1))
                print('OK')
            else:
                print('FAIL (no URL)')
                uploaded.append('')
        except Exception as e:
            print(f'FAIL: {e}')
            uploaded.append('')
        time.sleep(0.5)
    return uploaded


def update_excel_pic_urls(excel_path, pic_urls, row_idx=None):
    """更新Excel主图1-6 URL列 (H=8, I-M=9-13)
    
    Args:
        excel_path: Excel file path
        pic_urls: list of 6 URLs/paths (main1-6)
        row_idx: specific row to update (1-indexed, None=all rows)
    """
    wb = openpyxl.load_workbook(excel_path)
    ws = wb.active
    PIC_COLS = [8, 9, 10, 11, 12, 13]  # H, I, J, K, L, M
    
    if row_idx is not None:
        rows = [row_idx]
    else:
        rows = range(2, ws.max_row + 1)
    
    for r in rows:
        has_content = False
        for col in range(1, ws.max_column + 1):
            if ws.cell(row=r, column=col).value is not None:
                has_content = True
                break
        if not has_content:
            continue
        for i, url in enumerate(pic_urls):
            if i < len(PIC_COLS) and url:
                # Support both 1688 URLs and local paths
                if url.startswith('http'):
                    val = url
                elif os.path.isfile(url):
                    val = url
                else:
                    val = 'https://cbu01.alicdn.com/' + url
                ws.cell(row=r, column=PIC_COLS[i], value=val)
    
    wb.save(excel_path)
    if row_idx:
        print(f'[OK] Excel row {row_idx} pic URLs updated')
    else:
        print(f'[OK] Excel pic URLs updated: {excel_path}')

def main():
    global EXCEL_PATH
    if not EXCEL_PATH:
        print('用法: python batch_publish.py <Excel文件路径>')
        sys.exit(1)

    # ========== random pics ==========
    fixed_product_imgs = []
    if getattr(_args, 'random_pics', False):
        print('=== random select images ===')
        
        # Load product images (fixed main1 for each row)
        product_dir = _args.product_dir or os.path.join(_args.images_dir, 'product')
        if os.path.isdir(product_dir):
            product_files = []
            for ext in ('*.jpg', '*.jpeg', '*.png', '*.bmp'):
                product_files.extend(glob.glob(os.path.join(product_dir, ext)))
            product_files.sort()
            fixed_product_imgs = product_files
            print(f'[INFO] Found {len(product_files)} product images for fixed main1')
        
        counts = {
            'instrument': _args.instrument_count,
            'patent': _args.patent_count,
            'certificate': _args.certificate_count,
        }
        
        # We'll select images per product row later
        # For now, just store the config
        _random_pics_config = {
            'images_dir': _args.images_dir,
            'counts': counts,
            'product_imgs': fixed_product_imgs,
            'skip_upload': getattr(_args, 'skip_upload', False)
        }
    else:
        _random_pics_config = None


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

        _sku   = _str(row, col_map, 'sku', '')
        _title = _str(row, col_map, 'title', '')
        pic_main   = _str(row, col_map, 'pic_url', '')
        pic_detail = _str_multi(row, col_map, ['pic_url2','pic_url3','pic_url4','pic_url5','pic_url6'])
        products.append({
            'title':      make_title(_sku, _title),
            'cat_id':     _int(row, col_map, 'cat_id', CAT_ID),
            'price':      _float(row, col_map, 'price', 9.9),
            'stock':      _int(row, col_map, 'stock', 100),
            'sku':        _str(row, col_map, 'sku', ''),
            'pic_main':   pic_main,
            'pic_detail': pic_detail,
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
        # Per-row image selection for --random-pics (before SKIP check)
        if '_random_pics_config' in dir() and _random_pics_config:
            product_idx = products.index(p)  # 0-based row index
            product_imgs = _random_pics_config['product_imgs']
            fixed_main1 = product_imgs[product_idx] if product_idx < len(product_imgs) else None

            sel = random_select_images(
                _random_pics_config['images_dir'],
                _random_pics_config['counts'],
                product_img=fixed_main1
            )

            if not _random_pics_config['skip_upload']:
                print('  Uploading images to 1688 ...')
                urls = upload_images_to_1688(sel['all'])
                urls = [u for u in urls if u]
                if urls:
                    p['pic_main'] = urls[0] if urls else ''
                    p['pic_detail'] = urls[1:] if len(urls) > 1 else []
                    if EXCEL_PATH:
                        update_excel_pic_urls(EXCEL_PATH, urls, row_idx=product_idx + 2)
            else:
                p['pic_main'] = sel['all'][0] if sel['all'] else ''
                p['pic_detail'] = sel['all'][1:] if len(sel['all']) > 1 else []
                if EXCEL_PATH:
                    update_excel_pic_urls(EXCEL_PATH, sel['all'][:6], row_idx=product_idx + 2)

        if p.get('_skip'):
            print(f'--- SKIP (已上架): {p["sku"]} ({p["title"][:30]}) ---')
            results.append({'sku': p['sku'], 'success': True, 'skipped': True})
            continue

        print(f'\n--- {p["sku"]} ({p["title"][:30]}) ---')

        main_pic = normalize_pic_url(p['pic_main'])
        detail_pics = [normalize_pic_url(u) for u in p['pic_detail'] if u]
        detail_pics = [u for u in detail_pics if u.startswith('http')]

        if not main_pic or not main_pic.startswith('http'):
            print(f'  [SKIP] 主图URL无效: {p["pic_urls"]}')
            results.append({'sku': p['sku'], 'success': False, 'error': 'Invalid pic_url'})
            continue

        title = make_title(p['sku'], p['title'])
        print(f'  Title [{len(title.encode("utf-8"))} bytes]: {title}')
        print(f'  主图: {main_pic[:60]}')
        if detail_pics:
            print(f'  详情图({len(detail_pics)}张)')

        # 详情页HTML构建 = 纯文本产品参数 + 主图2-6作为<img>嵌入
        import html as html_mod
        if p['desc']:
            escaped = html_mod.escape(p['desc'][:8000])
            escaped = escaped.replace('\r\n', '<br>').replace('\n', '<br>').replace('  ', '&nbsp;')
            desc_html = f'<div style="font-family:Arial,Helvetica,sans-serif;font-size:14px;line-height:1.8;color:#333;padding:10px;">{escaped}</div>'
        else:
            desc_html = ''
        for dp in detail_pics:
            desc_html += f'<p style="text-align:center;margin:10px 0;"><img src="{dp}" style="max-width:100%;height:auto;"/></p>'
        cp = build_cat_prop(p, cat_opts)
        body = {
            'formValues': {
                'outerId': p['sku'],
                'title': title,
                'primaryPicture': {'imageList': [{'url': main_pic}]},
                'description': {'detailList': [{'id': '0', 'title': 'Details', 'content': desc_html, 'isRequired': True}]},
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
