# -*- coding: utf-8 -*-
import json, hashlib, hmac, time, requests, sys

AK="4962785"; AS="W6v0SLfR4w"; TK="255bdc2a-7e4a-4a8e-b476-fb0b4efa366b"

def sign(url_path, params):
    s = sorted(params.items(), key=lambda x: x[0])
    raw = url_path + "".join([k + str(v) for k, v in s])
    return hmac.new(AS.encode(), raw.encode(), hashlib.sha1).hexdigest().upper()

def get_product(pid):
    url_path = "param2/1/com.alibaba.product/alibaba.product.get/" + AK
    url = "https://gw.open.1688.com/openapi/" + url_path
    ts = str(int(time.time() * 1000))
    p = {"access_token": TK, "app_key": AK, "_aop_timestamp": ts, "productID": str(pid)}
    p["_aop_signature"] = sign(url_path, p)
    return requests.get(url, params=p, timeout=30).json()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python get_product.py <productID>"); sys.exit(1)
    r = get_product(sys.argv[1])
    pi = r.get("productInfo", {})
    if pi:
        print("ID:", pi.get("productID"))
        print("Title:", pi.get("subject"))
        print("Status:", pi.get("status"))
        print("Stock:", pi.get("saleInfo", {}).get("amountOnSale"))
        print("Price:", pi.get("saleInfo", {}).get("priceRanges"))
    else:
        print("Failed:", r)
