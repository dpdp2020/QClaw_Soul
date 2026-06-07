# -*- coding: utf-8 -*-
import hashlib, hmac, time, requests, sys, os

AK="4962785"; AS="W6v0SLfR4w"; TK="255bdc2a-7e4a-4a8e-b476-fb0b4efa366b"

def sign(url_path, params):
    s = sorted(params.items(), key=lambda x: x[0])
    raw = url_path + "".join([k + str(v) for k, v in s])
    return hmac.new(AS.encode(), raw.encode(), hashlib.sha1).hexdigest().upper()

def upload_image(image_path):
    url_path = "param2/1/com.alibaba.product/alibaba.photobank.photo.add/" + AK
    url = "https://gw.open.1688.com/openapi/" + url_path
    ts = str(int(time.time() * 1000))
    p = {"albumID": "-1", "access_token": TK, "app_key": AK,
          "_aop_timestamp": ts, "name": os.path.basename(image_path), "webSite": "1688"}
    p["_aop_signature"] = sign(url_path, p)
    with open(image_path, "rb") as f:
        img_bytes = f.read()
    r = requests.post(url, files={"imageBytes": (os.path.basename(image_path), img_bytes, "image/jpeg")},
                      data=p, timeout=30).json()
    return r.get("image", {}).get("url", "") or r.get("result", {}).get("url", "")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python upload_image.py <image_path>"); sys.exit(1)
    url = upload_image(sys.argv[1])
    if url:
        print("Uploaded:", url)
    else:
        print("Failed")
