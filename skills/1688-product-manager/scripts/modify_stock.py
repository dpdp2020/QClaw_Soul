# -*- coding: utf-8 -*-
"""
1688 修改商品库存 - alibaba.product.modifystock

用法:
    python modify_stock.py <商品ID> <库存值>
示例:
    python modify_stock.py 1058675280267 10
"""

import sys, json, hashlib, hmac, time, requests

AK = '4962785'
AS = 'W6v0SLfR4w'
TK = '255bdc2a-7e4a-4a8e-b476-fb0b4efa366b'

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

def main():
    if len(sys.argv) < 3:
        print('Usage: python modify_stock.py <product_id> <stock_change>')
        print('Example: python modify_stock.py 1058675280267 10')
        sys.exit(1)

    product_id = sys.argv[1]
    stock_change = int(sys.argv[2])

    print(f'Modifying stock for product {product_id}: +{stock_change}')

    r = api_post('alibaba.product.modifystock', {
        'webSite': '1688',
        'increaseModify': 'false',
        'productStockChange': json.dumps([{
            'productId': product_id,
            'productAmountChange': stock_change
        }]),
        'skuStocks': json.dumps([{
            'skuId': product_id,
            'stockChange': stock_change
        }])
    })

    print(json.dumps(r, ensure_ascii=False, indent=2))

    if r.get('success'):
        print(f'\n[SUCCESS] Product {product_id} stock modified by +{stock_change}')
    else:
        print(f'\n[FAIL] Error: {r.get("errorMessage", r)}')

if __name__ == '__main__':
    main()
