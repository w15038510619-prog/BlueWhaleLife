from __future__ import annotations
import hashlib
import json
import time
import urllib.parse
from typing import List, Dict, Any, Optional
import httpx

MIXIN_KEY_ENC_TAB = [
    46, 47, 18, 2, 53, 8, 23, 32, 15, 50, 10, 31, 58, 3, 45, 35, 27, 43, 5, 49,
    33, 9, 42, 19, 29, 28, 14, 39, 12, 38, 41, 13, 37, 48, 7, 16, 24, 55, 40,
    61, 26, 17, 0, 1, 60, 51, 30, 4, 22, 25, 54, 21, 56, 59, 6, 63, 57, 62, 11,
    36, 20, 34, 44, 52
]

# Curated fallback pool in case network is disconnected
CURATED_FALLBACK_POOL: List[Dict[str, Any]] = [
    {
        "bvid": "BV1xx411c7mD",
        "title": "【深海探索】马里亚纳海沟10000米深处，那些像幽灵一样发光的生物如何生存？",
        "author": "深蓝物语",
        "cover": "https://images.unsplash.com/photo-1544551763-46a013bb70d5?w=600&auto=format&fit=crop&q=80",
        "duration": "14:22",
        "pubdate": "2026-03-15",
        "tags": ["奇妙大自然与海洋生物", "深海生态", "生物发光", "深潜纪录"],
        "description": "深渊带没有一丝阳光，承受着相当于数百个大气压的极端压力。科考团队使用万米载人深潜器，记录下狮子鱼与发光栉水母的独门生存策略。",
        "has_subtitles": False
    },
    {
        "bvid": "BV1pA411V7qM",
        "title": "用树莓派和乐高积木，我做了一台能全自动给多肉植物浇水拍照的巡检小车！",
        "author": "极客小工匠",
        "cover": "https://images.unsplash.com/photo-1518770660439-4636190af475?w=600&auto=format&fit=crop&q=80",
        "duration": "09:45",
        "pubdate": "2026-03-18",
        "tags": ["手作与神奇工程", "前沿AI与开源软件", "树莓派", "开源硬件"],
        "description": "花了三周时间从零设计底盘结构，结合OpenCV视觉循迹和土壤湿度传感器，让阳台上的植物有了24小时专属管家。",
        "has_subtitles": False
    },
    {
        "bvid": "BV1GJ411x7hZ",
        "title": "韦伯太空望远镜拍到宇宙诞生第一批星系：现代宇宙学标准模型真的要被颠覆了吗？",
        "author": "星空漫游指南",
        "cover": "https://images.unsplash.com/photo-1451187580459-43490279c0fa?w=600&auto=format&fit=crop&q=80",
        "duration": "18:10",
        "pubdate": "2026-03-20",
        "tags": ["硬核科普与天文物理", "宇宙学", "韦伯望远镜", "大爆炸"],
        "description": "早期宇宙星系的质量和亮度远超原有理论预测。天体物理学界正在激烈争论：是暗物质演化模型需要修正，还是超大质量黑洞的形成另有捷径？",
        "has_subtitles": False
    }
]


class BilibiliSource:
    """
    Compliant read-only Bilibili Data Source.
    Fetches genuine public rankings, WBI keyword searches, and multi-tier video details (subtitles, metadata).
    Zero unauthorized cookie injection, zero platform bypassing, strictly read-only public endpoints.
    """

    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://www.bilibili.com"
    }

    _wbi_cache: Dict[str, Any] = {"img_key": "", "sub_key": "", "cached_at": 0}

    @classmethod
    def _get_mixin_key(cls, orig: str) -> str:
        return "".join([orig[i] for i in MIXIN_KEY_ENC_TAB])[:32]

    @classmethod
    async def _get_wbi_keys(cls) -> tuple[str, str]:
        now = time.time()
        # Cache WBI keys for 2 hours
        if cls._wbi_cache["img_key"] and (now - cls._wbi_cache["cached_at"]) < 7200:
            return cls._wbi_cache["img_key"], cls._wbi_cache["sub_key"]

        try:
            async with httpx.AsyncClient(timeout=6.0) as client:
                res = await client.get("https://api.bilibili.com/x/web-interface/nav", headers=cls.HEADERS)
                data = res.json()
                wbi_img = data.get("data", {}).get("wbi_img", {})
                img_url = wbi_img.get("img_url", "")
                sub_url = wbi_img.get("sub_url", "")
                if img_url and sub_url:
                    img_key = img_url.rsplit("/", 1)[1].split(".")[0]
                    sub_key = sub_url.rsplit("/", 1)[1].split(".")[0]
                    cls._wbi_cache = {"img_key": img_key, "sub_key": sub_key, "cached_at": now}
                    return img_key, sub_key
        except Exception as e:
            print(f"[BilibiliSource] Failed to fetch WBI keys: {e}")

        # Fallback public default keys if nav unavailable
        return "7cd084941338484aae1ad9425b84077c", "4932caff0ff746eab6f01bf08b70ac45"

    @classmethod
    def _sign_wbi(cls, params: dict, img_key: str, sub_key: str) -> dict:
        mixin_key = cls._get_mixin_key(img_key + sub_key)
        params["wts"] = round(time.time())
        params = dict(sorted(params.items()))
        params = {
            k: "".join(filter(lambda c: c not in "!'()*", str(v)))
            for k, v in params.items()
        }
        query = urllib.parse.urlencode(params)
        wbi_sign = hashlib.md5((query + mixin_key).encode()).hexdigest()
        params["w_rid"] = wbi_sign
        return params

    @classmethod
    async def search_by_keyword(cls, keyword: str, limit: int = 15) -> List[Dict[str, Any]]:
        """Perform compliant public WBI keyword search."""
        img_key, sub_key = await cls._get_wbi_keys()
        params = {"keyword": keyword, "search_type": "video", "page_size": limit}
        signed = cls._sign_wbi(params, img_key, sub_key)
        query = urllib.parse.urlencode(signed)
        url = f"https://api.bilibili.com/x/web-interface/wbi/search/type?{query}"

        results = []
        try:
            async with httpx.AsyncClient(timeout=7.0) as client:
                res = await client.get(url, headers=cls.HEADERS)
                if res.status_code == 200:
                    data = res.json()
                    if data.get("code") == 0:
                        raw_items = data.get("data", {}).get("result", [])
                        for item in raw_items:
                            bvid = item.get("bvid")
                            if not bvid:
                                continue
                            raw_title = item.get("title", "")
                            # Strip HTML highlight tags <em class="keyword">
                            clean_title = raw_title.replace('<em class="keyword">', "").replace("</em>", "").strip()
                            clean_desc = (item.get("description") or "").strip()
                            tags = [t.strip() for t in (item.get("tag") or "").split(",") if t.strip()]

                            results.append({
                                "bvid": bvid,
                                "title": clean_title,
                                "author": item.get("author", "未知UP主"),
                                "cover": item.get("pic", ""),
                                "duration": str(item.get("duration", "05:00")),
                                "pubdate": str(item.get("pubdate", "")),
                                "tags": tags or [keyword],
                                "description": clean_desc,
                                "source_channel": "wbi_search"
                            })
        except Exception as e:
            print(f"[BilibiliSource] WBI search failed for '{keyword}': {e}")
        return results

    @classmethod
    async def fetch_ranking_feed(cls, rid: int, limit: int = 25) -> List[Dict[str, Any]]:
        """Fetch real public category ranking list (rid: 36=Science, 188=Tech, 24=Anime, 207=DIY)."""
        url = f"https://api.bilibili.com/x/web-interface/ranking/v2?rid={rid}&type=all"
        results = []
        try:
            async with httpx.AsyncClient(timeout=7.0) as client:
                res = await client.get(url, headers=cls.HEADERS)
                if res.status_code == 200:
                    data = res.json()
                    if data.get("code") == 0:
                        items = data.get("data", {}).get("list", [])[:limit]
                        for item in items:
                            bvid = item.get("bvid")
                            if not bvid:
                                continue
                            results.append({
                                "bvid": bvid,
                                "title": item.get("title", ""),
                                "author": item.get("owner", {}).get("name", "未知UP主"),
                                "cover": item.get("pic", ""),
                                "duration": str(item.get("duration", 0)),
                                "pubdate": str(item.get("pubdate", "")),
                                "tags": [item.get("tname", "精选视频")],
                                "description": item.get("desc", ""),
                                "source_channel": f"ranking_rid_{rid}"
                            })
        except Exception as e:
            print(f"[BilibiliSource] Ranking fetch failed for rid {rid}: {e}")
        return results

    @classmethod
    async def fetch_popular_precious(cls, limit: int = 20) -> List[Dict[str, Any]]:
        """Fetch Bilibili 'Must-watch' public popular archive (入站必刷)."""
        url = f"https://api.bilibili.com/x/web-interface/popular/precious?page_size={limit}&page=1"
        results = []
        try:
            async with httpx.AsyncClient(timeout=7.0) as client:
                res = await client.get(url, headers=cls.HEADERS)
                if res.status_code == 200:
                    data = res.json()
                    if data.get("code") == 0:
                        items = data.get("data", {}).get("list", [])
                        for item in items:
                            bvid = item.get("bvid")
                            if not bvid:
                                continue
                            results.append({
                                "bvid": bvid,
                                "title": item.get("title", ""),
                                "author": item.get("owner", {}).get("name", "未知UP主"),
                                "cover": item.get("pic", ""),
                                "duration": str(item.get("duration", 0)),
                                "pubdate": str(item.get("pubdate", "")),
                                "tags": [item.get("tname", "入站必刷")],
                                "description": item.get("desc", ""),
                                "source_channel": "popular_precious"
                            })
        except Exception as e:
            print(f"[BilibiliSource] Popular precious fetch failed: {e}")
        return results

    @classmethod
    async def fetch_video_details(cls, bvid: str) -> Optional[Dict[str, Any]]:
        """
        Multi-tier video metadata and content extraction:
        1. Query public view endpoint for core metadata and CID.
        2. Query and download public / AI subtitles if available.
        3. Formats timeline transcript with timestamps.
        4. Accurately marks whether content understanding is full or partial.
        """
        # First check curated pool fallback
        for item in CURATED_FALLBACK_POOL:
            if item["bvid"] == bvid:
                fallback = item.copy()
                fallback["comprehension_tier"] = "metadata_only"
                fallback["is_partial"] = True
                fallback["subtitles_text"] = ""
                fallback["evidence_anchors"] = ["简介内容", "视频标题"]
                return fallback

        url = f"https://api.bilibili.com/x/web-interface/view?bvid={bvid}"
        try:
            async with httpx.AsyncClient(timeout=7.0) as client:
                res = await client.get(url, headers=cls.HEADERS)
                if res.status_code == 200:
                    data = res.json()
                    code = data.get("code", -1)
                    if code == 0 and "data" in data:
                        d = data["data"]
                        title = d.get("title", f"B站视频 {bvid}")
                        author = d.get("owner", {}).get("name", "未知UP主")
                        cover = d.get("pic", "")
                        duration = d.get("duration", 0)
                        pubdate = str(d.get("pubdate", ""))
                        tname = d.get("tname", "综合")
                        desc = d.get("desc", "")
                        stat = d.get("stat", {})

                        # Check for subtitles
                        sub_list = d.get("subtitle", {}).get("list", [])
                        subtitles_text = ""
                        has_subtitles = False
                        sub_evidence = []

                        if sub_list:
                            # Pick first subtitle (Chinese preferred)
                            chosen_sub = sub_list[0]
                            for sub in sub_list:
                                if "zh" in sub.get("lan", "").lower():
                                    chosen_sub = sub
                                    break

                            sub_url = chosen_sub.get("subtitle_url", "")
                            if sub_url:
                                if not sub_url.startswith("http"):
                                    sub_url = "https:" + sub_url
                                sub_res = await client.get(sub_url, headers=cls.HEADERS)
                                if sub_res.status_code == 200:
                                    sub_data = sub_res.json()
                                    lines = sub_data.get("body", [])
                                    if lines:
                                        has_subtitles = True
                                        transcript_parts = []
                                        for idx, l in enumerate(lines):
                                            start_sec = l.get("from", 0.0)
                                            m, s = divmod(int(start_sec), 60)
                                            text_line = l.get("content", "").strip()
                                            transcript_parts.append(f"[{m:02d}:{s:02d}] {text_line}")
                                            if idx % 8 == 0:
                                                sub_evidence.append(f"[{m:02d}:{s:02d}] {text_line[:20]}")
                                        subtitles_text = "\n".join(transcript_parts)

                        comprehension_tier = "subtitles" if has_subtitles else "metadata_only"
                        is_partial = not has_subtitles

                        return {
                            "bvid": bvid,
                            "title": title,
                            "author": author,
                            "cover": cover,
                            "duration": f"{duration // 60:02d}:{duration % 60:02d}",
                            "pubdate": pubdate,
                            "tags": [tname],
                            "description": desc,
                            "view_count": stat.get("view", 0),
                            "like_count": stat.get("like", 0),
                            "has_subtitles": has_subtitles,
                            "subtitles_text": subtitles_text,
                            "comprehension_tier": comprehension_tier,
                            "is_partial": is_partial,
                            "evidence_anchors": sub_evidence or ["视频标题", "UP主简介核心论述"],
                            "is_valid": True
                        }
                    else:
                        print(f"[BilibiliSource] Video {bvid} error code {code}: {data.get('message')}")
                        from backend.app.config import current_settings
                        if current_settings.demo_mode:
                            return {
                                "bvid": bvid,
                                "title": f"演示精选视频 ({bvid})",
                                "author": "科学创作者",
                                "cover": "https://images.unsplash.com/photo-1544551763-46a013bb70d5?w=600&auto=format&fit=crop&q=80",
                                "duration": "08:30",
                                "pubdate": "近期",
                                "tags": ["科学探索", "开源技术"],
                                "description": "演示模式下的探索知识内容，用于走通知识提炼与评论决策全流程。",
                                "has_subtitles": False,
                                "subtitles_text": "",
                                "comprehension_tier": "metadata_only",
                                "is_partial": True,
                                "evidence_anchors": ["公开视频简介", "演示核心概念"],
                                "is_valid": True
                            }
                        return {
                            "bvid": bvid,
                            "title": f"未知视频 ({bvid})",
                            "author": "未知UP主",
                            "cover": "",
                            "description": "",
                            "tags": [],
                            "is_valid": False,
                            "comprehension_tier": "failed",
                            "is_partial": True,
                            "failure_reason": f"B站接口返回: {data.get('message', '视频不可用或已失效')}"
                        }
        except Exception as e:
            print(f"[BilibiliSource] Network error fetching {bvid}: {e}")

        return None
