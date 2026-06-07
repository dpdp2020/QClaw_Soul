# -*- coding: utf-8 -*-
import json, hashlib, hmac, time, requests, sys

AK="4962785"; AS="W6v0SLfR4w"; TK="255bdc2a-7e4a-4a8e-b476-fb0b4efa366b"

def sign(url_path, params):
    s = sorted(params.items(), key=lambda x: x[0])
    raw = url_path + "".join([k + str(v) for k, v in s])
    return hmac.new(AS.encode(), raw.encode(), hashlib.sha1).hexdigest().upper()

def delete(pid):
    url_path = "param2/1/com.alibaba.product/alibaba.product.delete/" + AK
    url = "https://gw.open.1688.com/openapi/" + url_path
    ts = str(int(time.time() * 1000))
    p = {"access_token": TK, "app_key": AK, "_aop_timestamp": ts, "productID": str(pid)}
    p["_aop_signature"] = sign(url_path, p)
    return requests.post(url, data=p, timeout=30).json()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python delete_product.py <productID>"); sys.exit(1)
    pid = sys.argv[1]
    r = delete(pid)
    if r.get("isSuccess"):
        print("Deleted: " + pid)
    else:
        print("Failed: " + str(r))
