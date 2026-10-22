from __future__ import annotations
import json
from typing import List, Dict, Any, Optional
import httpx
from backend.app.models.video import VideoCandidate


# Curated realistic candidate pool for offline / zero-login exploration
CURATED_CANDIDATE_POOL: List[Dict[str, Any]] = [
    {
        "bvid": "BV1xx411c7mD",
        "title": "【深海探索】马里亚纳海沟10000米深处，那些像幽灵一样发光的生物如何生存？",
        "author": "深蓝物语",
        "cover": "https://images.unsplash.com/photo-1544551763-46a013bb70d5?w=600&auto=format&fit=crop&q=80",
        "duration": "14:22",
        "pubdate": "2026-03-15",
        "tags": ["奇妙大自然与海洋生物", "深海生态", "生物发光", "深潜纪录"],
        "description": "深渊带没有一丝阳光，承受着相当于数百个大气压的极端压力。科考团队使用万米载人深潜器，记录下狮子鱼与发光栉水母的独门生存策略。",
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
    },
    {
        "bvid": "BV1Ks411o7tU",
        "title": "只用纯手工木雕，还原《千与千寻》水上列车：木纹间的治愈美感",
        "author": "老木匠阿泽",
        "cover": "https://images.unsplash.com/photo-1513519245088-0e12902e5a38?w=600&auto=format&fit=crop&q=80",
        "duration": "12:05",
        "pubdate": "2026-03-21",
        "tags": ["手作与神奇工程", "治愈系动画与独立游戏", "木工", "吉卜力"],
        "description": "选用黑胡桃木和椴木，雕刻车厢座位与无脸男乘客，静下心来打磨每一个倒角。听着木屑掉落的声音，感受手作的温存。",
    },
    {
        "bvid": "BV1Rt411P7eW",
        "title": "为什么开源大模型越来越轻量却越来越聪明？从注意力蒸馏到MoE架构演进",
        "author": "AI探索者老周",
        "cover": "https://images.unsplash.com/photo-1620712943543-bcc4688e7485?w=600&auto=format&fit=crop&q=80",
        "duration": "16:30",
        "pubdate": "2026-03-22",
        "tags": ["前沿AI与开源软件", "硬核科普与天文物理", "大语言模型", "开源生态"],
        "description": "从百亿参数下沉到端侧芯片，AI如何做到既省算力又保逻辑？深入剖析知识蒸馏、混合专家系统（MoE）以及量化技术的最新突破。",
    },
    {
        "bvid": "BV1m5411z7vK",
        "title": "独自一人耗时两年开发的治愈水下独立游戏：当AI学会像鱼群一样自由游动",
        "author": "独立游荡者",
        "cover": "https://images.unsplash.com/photo-1546026423-cc4642628d2b?w=600&auto=format&fit=crop&q=80",
        "duration": "11:15",
        "pubdate": "2026-03-23",
        "tags": ["治愈系动画与独立游戏", "前沿AI与开源软件", "Boids算法", "独立游戏"],
        "description": "运用Boids鸟群/鱼群仿真算法，在Unreal引擎中搭建了一片宁静幽蓝的珊瑚礁世界。开发过程中踩过的物理引擎碰撞陷阱与艺术调试。",
    },
    {
        "bvid": "BV1nK411w7cL",
        "title": "【硬核拆解】圆珠笔顶端那颗0.5毫米碳化钨球珠，到底有多难制造？",
        "author": "工业显微镜",
        "cover": "https://images.unsplash.com/photo-1585336261026-64a66a7ecdb9?w=600&auto=format&fit=crop&q=80",
        "duration": "08:50",
        "pubdate": "2026-03-24",
        "tags": ["手作与神奇工程", "生活哲学与冷知识", "材料科学", "精密制造"],
        "description": "别小看日常几块钱的圆珠笔，其笔尖球珠的圆度公差需要控制在微米级别，涉及到高温粉末冶金、精密研磨和特种钢材配比。",
    },
    {
        "bvid": "BV1zW411j7rF",
        "title": "为什么猫咪呼噜声具有自愈频率？动物行为学家聊聊陪伴与治愈的科学",
        "author": "自然之眼记录",
        "cover": "https://images.unsplash.com/photo-1514888286974-6c03e2ca1dba?w=600&auto=format&fit=crop&q=80",
        "duration": "10:40",
        "pubdate": "2026-03-25",
        "tags": ["生活哲学与冷知识", "奇妙大自然与海洋生物", "动物行为学", "心理治愈"],
        "description": "25到140赫兹之间的振动频率已被证明可以促进骨骼与肌腱修复。猫咪不仅在开心时呼噜，在紧张与自我疗愈时同样会启动这种机制。",
    },
    {
        "bvid": "BV1bX411B7mH",
        "title": "量子纠缠到底是超光速传递还是幽灵行动？用抛硬币思想实验讲明白",
        "author": "费曼小迷弟",
        "cover": "https://images.unsplash.com/photo-1635070041078-e363dbe005cb?w=600&auto=format&fit=crop&q=80",
        "duration": "21:05",
        "pubdate": "2026-03-26",
        "tags": ["硬核科普与天文物理", "量子力学", "贝尔不等式", "物理哲学"],
        "description": "爱因斯坦为什么称它为“鬼魅般的超距作用”？贝尔不等式实验如何排除了局域隐变量理论？不涉及复杂张量计算，用简单直观的逻辑梳理物理争论。",
    }
]


class BilibiliSource:
    """
    Compliant read-only Bilibili data source.
    Supports local curated exploration pool as well as real read-only public API calls.
    """

    @staticmethod
    def get_candidate_pool() -> List[Dict[str, Any]]:
        return CURATED_CANDIDATE_POOL

    @staticmethod
    async def fetch_video_details(bvid: str) -> Optional[Dict[str, Any]]:
        """
        Attempts to fetch public video details via Bilibili read-only web interface.
        If network fails or bvid is mock, returns matching mock or synthesized fallback.
        """
        # First check curated pool
        for item in CURATED_CANDIDATE_POOL:
            if item["bvid"] == bvid:
                return item.copy()

        # Try real Bilibili public view endpoint (Read-only, no auth required)
        url = f"https://api.bilibili.com/x/web-interface/view?bvid={bvid}"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": "https://www.bilibili.com"
        }
        try:
            async with httpx.AsyncClient(timeout=6.0) as client:
                res = await client.get(url, headers=headers)
                if res.status_code == 200:
                    data = res.json()
                    if data.get("code") == 0 and "data" in data:
                        d = data["data"]
                        return {
                            "bvid": bvid,
                            "title": d.get("title", f"B站视频 {bvid}"),
                            "author": d.get("owner", {}).get("name", "未知UP主"),
                            "cover": d.get("pic", ""),
                            "duration": str(d.get("duration", 0)),
                            "pubdate": str(d.get("pubdate", "")),
                            "tags": [d.get("tname", "综合")],
                            "description": d.get("desc", ""),
                            "is_real_data": True
                        }
        except Exception as e:
            print(f"[BilibiliSource] Public API fetch failed for {bvid}: {e}. Falling back.")

        # Fallback if network unavailable or custom BV entered
        return {
            "bvid": bvid,
            "title": f"B站视频 {bvid}",
            "author": "UP主",
            "cover": "https://images.unsplash.com/photo-1544551763-46a013bb70d5?w=600&auto=format&fit=crop&q=80",
            "duration": "10:00",
            "pubdate": "近期",
            "tags": ["日常探索"],
            "description": "（未取得完整视频或字幕数据，将基于公开标题与基础信息进行严谨分析）",
            "is_real_data": False
        }
