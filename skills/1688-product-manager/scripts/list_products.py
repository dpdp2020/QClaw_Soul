# -*- coding: utf-8 -*-
import json, hashlib, hmac, time, requests, sys

AK="4962785"; AS="W6v0SLfR4w"; TK="255bdc2a-7e4a-4a8e-b476-fb0b4efa366b"

def sign(url_path, params):
    s = sorted(params.items(), key=lambda x: x[0])
    raw = url_path + "".join([k + str(v) for k, v in s])
    return hmac.new(AS.encode(), raw.encode(), hashlib.sha1).hexdigest().upper()

def list_products(page_no=1, page_size=20):
    url_path = "param2/1/com.alibaba.product/alibaba.product.list.get/" + AK
    url = "https://gw.open.1688.com/openapi/" + url_path
    ts = str(int(time.time() * 1000))
    p = {"access_token": TK, "app_key": AK, "_aop_timestamp": ts,
          "pageNo": page_no, "pageSize": page_size, "statusList": "PUBLISHED"}
    p["_aop_signature"] = sign(url_path, p)
    return requests.get(url, params=p, timeout=30).json()

if __name__ == "__main__":
    page = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    size = int(sys.argv[2]) if len(sys.argv) > 2 else 20
    r = list_products(page, size)
    result = r.get("result", {})
    if result.get("success"):
        for prod in result.get("products", []):
            pi = prod.get("productInfo", {})
            print(pi.get("productID"), "|", pi.get("subject", "")[:40], "| stock:", pi.get("saleInfo", {}).get("amountOnSale"))
        print("Total:", result.get("total"))
    else:
        print("Failed:", r)
