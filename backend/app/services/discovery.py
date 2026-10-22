from __future__ import annotations
import json
import random
import asyncio
from datetime import datetime
from typing import List, Dict, Any, Optional
from backend.app.database import get_db_connection
from backend.app.models.video import VideoCandidate
from backend.app.services.bilibili_source import BilibiliSource, CURATED_FALLBACK_POOL
from backend.app.services.soul import SoulEngine
from backend.app.config import current_settings


class DiscoveryEngine:
    """
    Autonomous Content Discovery Engine (inspired by OpenBiliClaw's Blue Fish Lab & Soul scoring).
    Genuinely explores real, live Bilibili public content matching Big Chubby Fish's curiosity,
    evolving interests, unresolved doubts, favored UP hosts, and novelty seeking.
    """

    @classmethod
    def _compute_candidate_score(cls, item: Dict[str, Any], interests: Dict[str, float], novelty_weight: float) -> tuple[float, str]:
        tags = item.get("tags", [])
        title = item.get("title", "")
        desc = item.get("description", "")
        author = item.get("author", "")

        # 1. Interest alignment calculation
        alignment = 0.5
        matched_interests = []
        for interest_topic, weight in interests.items():
            # Check keywords in topic
            keywords = interest_topic.replace("与", " ").replace("、", " ").split()
            if any(k in title or k in desc or any(k in t for t in tags) for k in keywords):
                matched_interests.append((interest_topic, weight))

        if matched_interests:
            alignment = max(w for _, w in matched_interests)

        # 2. Novelty calculation
        is_novel = len(matched_interests) == 0
        novelty_score = 0.88 if is_novel else random.uniform(0.45, 0.78)

        total_score = round(alignment * (1.0 - novelty_weight) + novelty_score * novelty_weight, 3)

        # 3. Explain choice reason
        if matched_interests:
            best_topic = matched_interests[0][0]
            reasons = [
                f"在【{best_topic}】领域，UP主【{author}】的这个切入点非常引人入胜，激起了小肥鱼的求知欲！",
                f"正好对应我平时积累的【{best_topic}】认知，标题里的论点让我很想一探究竟~",
                f"根据大肥鱼的兴趣雷达，【{best_topic}】方向一直保持着高关注度，很期待UP主提出的独到见解。"
            ]
            reason = random.choice(reasons)
        else:
            reasons = [
                f"虽然【{title[:12]}】之前涉猎较少，但好奇心驱使我游出舒适区，探索未知的全新知识领域！",
                "这是一次跳出信息茧房的偶然漫游！大肥鱼觉得多涉猎冷门领域能激发更多灵感。",
                f"标题中的新概念一下抓住了我的目光，直觉告诉我这会是一个非常有启发性的视频。"
            ]
            reason = random.choice(reasons)

        return total_score, reason

    @classmethod
    async def explore(cls, force_refresh: bool = False) -> List[VideoCandidate]:
        """
        Executes an autonomous exploration run.
        Queries real Bilibili public category rankings and targeted WBI searches,
        filters out already-watched videos, scores remaining candidates, and updates the local candidate pool.
        """
        state = SoulEngine.get_current_state()
        interests = state.interests
        novelty_w = current_settings.novelty_weight

        # 1. Collect real candidates from multiple public channels
        raw_candidates: List[Dict[str, Any]] = []

        # A. Public Category Rankings (Science rid 36, Tech rid 188, DIY rid 207)
        rids = [36, 188, 207]
        chosen_rid = random.choice(rids)
        ranking_items = await BilibiliSource.fetch_ranking_feed(chosen_rid, limit=20)
        raw_candidates.extend(ranking_items)

        # B. Popular precious items (Must-watch)
        precious_items = await BilibiliSource.fetch_popular_precious(limit=15)
        raw_candidates.extend(precious_items)

        # C. Targeted WBI search based on fish's top interest or pending doubts
        top_interests = sorted(interests.items(), key=lambda x: x[1], reverse=True)
        search_kw = "人工智能"
        if top_interests:
            # Pick one of the top interests to search
            kw_topic = random.choice(top_interests[:3])[0]
            # Extract simple keyword
            if "科普" in kw_topic or "物理" in kw_topic:
                search_kw = random.choice(["量子力学", "深海生物", "韦伯望远镜", "黑洞"])
            elif "AI" in kw_topic or "开源" in kw_topic:
                search_kw = random.choice(["开源大模型", "具身智能", "边缘计算", "自主Agent"])
            elif "手作" in kw_topic or "工程" in kw_topic:
                search_kw = random.choice(["自制机器人", "机械时钟", "3D打印机", "精密制造"])
            else:
                search_kw = "冷知识"

        search_items = await BilibiliSource.search_by_keyword(search_kw, limit=12)
        raw_candidates.extend(search_items)

        # If network was unavailable or all returned empty, use curated fallback
        if not raw_candidates:
            print("[DiscoveryEngine] Real network returned empty, utilizing fallback pool.")
            raw_candidates.extend(CURATED_FALLBACK_POOL)

        # 2. Query already watched BV IDs to avoid repeats
        watched_bvids = set()
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT bvid FROM watch_history")
            watched_bvids = {r["bvid"] for r in cursor.fetchall()}

        scored_candidates: List[VideoCandidate] = []
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        seen_bvids = set()

        with get_db_connection() as conn:
            cursor = conn.cursor()
            for raw in raw_candidates:
                bvid = raw.get("bvid")
                if not bvid or bvid in watched_bvids or bvid in seen_bvids:
                    continue
                seen_bvids.add(bvid)

                score, reason = cls._compute_candidate_score(raw, interests, novelty_w)

                # Upsert into discovery_candidates table
                cursor.execute("""
                    INSERT INTO discovery_candidates (
                        bvid, title, author, cover, duration, pubdate, tags,
                        description, reason, score, status, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'discovered', ?)
                    ON CONFLICT(bvid) DO UPDATE SET
                        reason = excluded.reason,
                        score = excluded.score,
                        created_at = excluded.created_at
                """, (
                    bvid,
                    raw.get("title", ""),
                    raw.get("author", "未知UP主"),
                    raw.get("cover", ""),
                    raw.get("duration", "05:00"),
                    raw.get("pubdate", ""),
                    json.dumps(raw.get("tags", []), ensure_ascii=False),
                    raw.get("description", ""),
                    reason,
                    score,
                    now_str
                ))

                candidate = VideoCandidate(
                    bvid=bvid,
                    title=raw.get("title", ""),
                    author=raw.get("author", "未知UP主"),
                    cover=raw.get("cover", ""),
                    duration=raw.get("duration", "05:00"),
                    pubdate=raw.get("pubdate", ""),
                    tags=raw.get("tags", []),
                    description=raw.get("description", ""),
                    reason=reason,
                    score=score,
                    status="discovered",
                    source_channel=raw.get("source_channel", "bilibili_ranking")
                )
                scored_candidates.append(candidate)

        # Sort by score descending
        scored_candidates.sort(key=lambda x: x.score, reverse=True)
        return scored_candidates

    @classmethod
    def get_cached_candidates(cls, limit: int = 20) -> List[VideoCandidate]:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM discovery_candidates
                WHERE status = 'discovered'
                ORDER BY score DESC LIMIT ?
            """, (limit,))
            rows = cursor.fetchall()
            result = []
            for r in rows:
                tags = json.loads(r["tags"]) if r["tags"] else []
                result.append(VideoCandidate(
                    bvid=r["bvid"],
                    title=r["title"],
                    author=r["author"] or "未知UP主",
                    cover=r["cover"] or "",
                    duration=r["duration"] or "05:00",
                    pubdate=r["pubdate"] or "",
                    tags=tags,
                    description=r["description"] or "",
                    reason=r["reason"] or "",
                    score=r["score"] or 0.8,
                    status=r["status"] or "discovered"
                ))
            return result

    @classmethod
    def mark_candidate_status(cls, bvid: str, status: str) -> None:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE discovery_candidates SET status = ? WHERE bvid = ?", (status, bvid))
