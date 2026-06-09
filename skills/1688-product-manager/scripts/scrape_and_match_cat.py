"""
1688类目自动匹配工具 v3 - 正确API版本
API: alibaba.category.searchByKeyword (com.alibaba.product命名空间)
流程: 抓取官网产品 → 提取关键词 → 保存到Excel → 用关键词查1688类目 → 回填类目ID和名称到Excel
"""
import json, hashlib, hmac, time, re, requests, openpyxl
from bs4 import BeautifulSoup

AK = '4962785'; AS = 'W6v0SLfR4w'; TK = '255bdc2a-7e4a-4a8e-b476-fb0b4efa366b'

def sign(url_path, params):
    s = sorted(params.items(), key=lambda x: x[0])
    raw = url_path + ''.join([k + str(v) for k, v in s])
    return hmac.new(AS.encode(), raw.encode(), hashlib.sha1).hexdigest().upper()

def api_post(api_name, params):
    """调用1688 API (POST)"""
    url_path = f'param2/1/com.alibaba.product/{api_name}/{AK}'
    url = f'https://gw.open.1688.com/openapi/{url_path}'
    ts = str(int(time.time() * 1000))
    p = {'access_token': TK, 'app_key': AK, '_aop_timestamp': ts}
    p.update(params)
    p['_aop_signature'] = sign(url_path, p)
    r = requests.post(url, data=p, timeout=30)
    return r.json()

def api_get(api_name, params):
    """调用1688 API (GET)"""
    url_path = f'param2/1/com.alibaba.product/{api_name}/{AK}'
    url = f'https://gw.open.1688.com/openapi/{url_path}'
    ts = str(int(time.time() * 1000))
    p = {'access_token': TK, 'app_key': AK, '_aop_timestamp': ts}
    p.update(params)
    p['_aop_signature'] = sign(url_path, p)
    r = requests.get(url, params=p, timeout=30)
    return r.json()

# ===== 1. 抓取官网产品 =====
def scrape_aw168(url):
    r = requests.get(url, timeout=15, headers={'User-Agent': 'Mozilla/5.0'})
    r.encoding = 'utf-8'
    soup = BeautifulSoup(r.text, 'html.parser')
    
    name = ''
    h1 = soup.find('h1') or soup.find('h2')
    if h1: name = h1.get_text(strip=True)
    
    model = ''
    for text in soup.find_all(string=re.compile(r'型号|Model')):
        m = re.search(r'[A-Z]{2,}[-]?\d+', text)
        if m: model = m.group(); break
    
    # 关键词提取
    keywords = []
    kw_tag = soup.find('meta', attrs={'name': 'keywords'})
    if kw_tag and kw_tag.get('content'):
        keywords = [k.strip() for k in kw_tag['content'].split(',') if k.strip()]
    if not keywords:
        words = re.findall(r'[\w\+]+', name)
        keywords = [w for w in words if len(w) >= 2 and not w.isdigit()]
    
    # 产品图
    images = []
    for img in soup.find_all('img'):
        src = img.get('src', '') or img.get('data-src', '')
        if src and ('product' in src or 'uploads' in src or 'images' in src):
            if not src.startswith('http'):
                src = 'https://www.aw168.cn' + src
            if src not in images:
                images.append(src)
    
    return {'name': name, 'model': model, 'keywords': keywords, 'images': images}

# ===== 2. 用关键词搜索1688类目 (正确API) =====
def search_category_by_keyword(keywords):
    """
    通过 alibaba.category.searchByKeyword 搜索类目
    返回最佳匹配的叶子节点类目 (isLeaf=true, categoryType="3")
    """
    best_match = None
    
    for kw in keywords:
        try:
            print(f'    尝试关键词: [{kw}]')
            r = api_post('alibaba.category.searchByKeyword', {'keyword': kw})
            
            # 响应结构: {"products": [...], "success": "true"} (无result包裹)
            success = r.get('success') == 'true'
            products = r.get('products', [])
            
            if not success and 'result' in r:
                # 兼容有result包裹的情况
                result_data = r['result']
                success = result_data.get('success') == 'true'
                products = result_data.get('products', [])
            
            if success:
                # products 已在上面提取
                
                # 优先找 isLeaf=true 且 categoryType="3" 的叶子类目
                for cat in products:
                    cid = cat.get('categoryID', 0)
                    cname = cat.get('name', '')
                    is_leaf = cat.get('isLeaf', False)
                    cat_type = cat.get('categoryType', '')
                    
                    # 优先选叶子节点(categoryType=3)
                    if cid and is_leaf and cat_type == '3':
                        return {
                            'catId': cid,
                            'catName': cname,
                            'catLevel': cat.get('level', ''),
                            'categoryType': cat_type,
                            'keyword': kw,
                            'allCats': products[:5]
                        }
                
                # 如果没有type=3的，返回第一个有ID的
                for cat in products:
                    cid = cat.get('categoryID', 0)
                    if cid:
                        return {
                            'catId': cid,
                            'catName': cat.get('name', ''),
                            'catLevel': '',
                            'categoryType': cat.get('categoryType', ''),
                            'keyword': kw,
                            'allCats': products[:5]
                        }
            else:
                err = r.get('error_message', r.get('error_code', '?'))
                print(f'    错误: {err}')
                
        except Exception as e:
            print(f'    异常: {e}')
    
    return best_match

# ===== 3. 主流程 =====
def main():
    excel_path = r'D:\wujm\安威\helper\1688_product_upload.xlsx'
    product_urls = {
        2: 'https://www.aw168.cn/pro/wifi/276.html',
        3: 'https://www.aw168.cn/pro/wifi/237.html',
    }

    print('='*60)
    print('  1688 类目自动匹配工具 v3')
    print('='*60)

    # Step 1: 抓取官网产品
    print('\n[Step 1] 抓取官网产品信息')
    scraped = {}
    for row_num, url in product_urls.items():
        try:
            print(f'\n  Row {row_num}: {url}')
            data = scrape_aw168(url)
            scraped[row_num] = data
            print(f'    名称: {data["name"][:40]}')
            print(f'    型号: {data["model"] or "(未识别)"}')
            print(f'    关键词({len(data["keywords"])}个): {data["keywords"][:6]}')
            print(f'    图片: {len(data["images"])}张')
        except Exception as e:
            print(f'    失败: {e}')

    # Step 2: 保存关键词到Excel Col 15
    print('\n[Step 2] 保存关键词到Excel (Col 15)')
    wb = openpyxl.load_workbook(excel_path)
    ws = wb.active
    for row_num, data in scraped.items():
        kw_str = ','.join(data['keywords'][:10])
        ws.cell(row_num, 15).value = kw_str
        print(f'  Row {row_num} Col15: {kw_str}')

    # Step 3: 用关键词查询1688类目
    print('\n[Step 3] 用关键词查询1688类目')
    cat_results = {}
    for row_num, data in scraped.items():
        print(f'\n  Row {row_num}: {data["name"][:35]}')
        
        result = search_category_by_keyword(data['keywords'])
        
        if result:
            print(f'  [OK] 匹配成功!')
            print(f'       关键词: [{result["keyword"]}]')
            print(f'       类目ID: {result["catId"]}')
            print(f'       类目名: {result["catName"]} (type={result["categoryType"]})')
            
            # 显示备选
            alt = [c for c in result['allCats'] if c.get('categoryID') != result['catId']]
            if alt:
                print(f'       备选:')
                for i, c in enumerate(alt[:3], 1):
                    leaf_mark = '*' if c.get('isLeaf') else ' '
                    print(f'         {i}. [{leaf_mark}] {c.get("categoryID")} - {c.get("name")}')
            
            cat_results[row_num] = result
        else:
            print(f'  [X] 未找到匹配类目')

    # Step 4: 回填类目ID(Col4)和类目名称(Col5)到Excel
    print('\n[Step 4] 回填类目到Excel')
    updated_count = 0
    for row_num, result in cat_results.items():
        ws.cell(row_num, 4).value = result['catId']
        ws.cell(row_num, 5).value = result['catName']
        updated_count += 1
        print(f'  Row {row_num}: ID={result["catId"]} 名称={result["catName"]}')

    # 保存到新文件名
    import os
    tmp = excel_path.replace('.xlsx', f'_cat_{int(time.time())}.xlsx')
    wb.save(tmp)
    print(f'\n[OK] 已更新{updated_count}个产品的类目信息')
    print(f'     保存到: {tmp}')

    # 保存完整结果JSON
    output = {
        'scraped': scraped,
        'cat_results': cat_results,
        'updated_file': tmp,
        'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
    }
    with open(r'D:\wujm\安威\helper\cat_results.json', 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f'     JSON结果: D:\\wujm\\安威\\helper\\cat_results.json')

if __name__ == '__main__':
    main()
