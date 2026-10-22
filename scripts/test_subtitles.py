import httpx

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://www.bilibili.com"
}

def check_video_subtitles(bvid: str):
    with httpx.Client(timeout=8.0) as client:
        res = client.get(f"https://api.bilibili.com/x/web-interface/view?bvid={bvid}", headers=headers)
        data = res.json()
        if data.get("code") == 0:
            d = data["data"]
            title = d.get("title")
            sub_list = d.get("subtitle", {}).get("list", [])
            print(f"Video {bvid} ({title}): {len(sub_list)} subtitles available")
            for sub in sub_list:
                sub_url = sub.get("subtitle_url")
                if sub_url and not sub_url.startswith("http"):
                    sub_url = "https:" + sub_url
                print(f"  Lang: {sub.get('lan_doc')}, URL: {sub_url[:60]}...")
                if sub_url:
                    sub_res = client.get(sub_url, headers=headers)
                    if sub_res.status_code == 200:
                        lines = sub_res.json().get("body", [])
                        print(f"  Parsed {len(lines)} subtitle lines!")
                        for l in lines[:3]:
                            print(f"    [{l.get('from')}s -> {l.get('to')}s]: {l.get('content')}")

if __name__ == "__main__":
    # Test on a video known to have subtitles
    check_video_subtitles("BV1AHnB6NEhM")
    check_video_subtitles("BV1yF41117MX")
