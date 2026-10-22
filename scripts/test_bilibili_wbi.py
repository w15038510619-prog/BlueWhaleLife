import hashlib
import urllib.parse
import time
import httpx

MIXIN_KEY_ENC_TAB = [
    46, 47, 18, 2, 53, 8, 23, 32, 15, 50, 10, 31, 58, 3, 45, 35, 27, 43, 5, 49,
    33, 9, 42, 19, 29, 28, 14, 39, 12, 38, 41, 13, 37, 48, 7, 16, 24, 55, 40,
    61, 26, 17, 0, 1, 60, 51, 30, 4, 22, 25, 54, 21, 56, 59, 6, 63, 57, 62, 11,
    36, 20, 34, 44, 52
]

def get_mixin_key(orig: str) -> str:
    return "".join([orig[i] for i in MIXIN_KEY_ENC_TAB])[:32]

def enc_wbi(params: dict, img_key: str, sub_key: str) -> dict:
    mixin_key = get_mixin_key(img_key + sub_key)
    curr_time = round(time.time())
    params["wts"] = curr_time
    params = dict(sorted(params.items()))
    params = {
        k: "".join(filter(lambda c: c not in "!'()*", str(v)))
        for k, v in params.items()
    }
    query = urllib.parse.urlencode(params)
    wbi_sign = hashlib.md5((query + mixin_key).encode()).hexdigest()
    params["w_rid"] = wbi_sign
    return params

def main():
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://www.bilibili.com"
    }

    with httpx.Client(timeout=8.0) as client:
        nav_res = client.get("https://api.bilibili.com/x/web-interface/nav", headers=headers).json()
        wbi_img = nav_res.get("data", {}).get("wbi_img", {})
        img_key = wbi_img.get("img_url", "").rsplit("/", 1)[1].split(".")[0]
        sub_key = wbi_img.get("sub_url", "").rsplit("/", 1)[1].split(".")[0]

        signed = enc_wbi({"keyword": "量子计算", "search_type": "video"}, img_key, sub_key)
        query = urllib.parse.urlencode(signed)
        search_url = f"https://api.bilibili.com/x/web-interface/wbi/search/type?{query}"

        search_res = client.get(search_url, headers=headers)
        print("Search status:", search_res.status_code)
        data = search_res.json()
        print("Search code:", data.get("code"))
        if data.get("code") == 0:
            results = data.get("data", {}).get("result", [])
            print(f"WBI Search found {len(results)} videos!")
            for r in results[:3]:
                title = r.get("title", "").replace('<em class="keyword">', "").replace("</em>", "")
                print(f"  [{r.get('bvid')}] {title[:30]} by {r.get('author')}")

if __name__ == "__main__":
    main()
