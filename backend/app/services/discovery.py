from __future__ import annotations
import json
import random
from datetime import datetime
from typing import List, Dict, Any, Optional
from backend.app.database import get_db_connection
from backend.app.models.video import VideoCandidate
from backend.app.services.bilibili_source import BilibiliSource
from backend.app.services.soul import SoulEngine
from backend.app.config import current_settings


class DiscoveryEngine:
    """
    Autonomous Content Discovery Engine (inspired by OpenBiliClaw's discovery and soul scoring).
    Explores read-only Bilibili content matching the fish's curiosity, interests, and novelty seeking.
    """

    @classmethod
    def _compute_candidate_score(cls, item: Dict[str, Any], interests: Dict[str, float], novelty_weight: float) -> tuple[float, str]:
        tags = item.get("tags", [])
        title = item.get("title", "")
        desc = item.get("description", "")

        # 1. Interest alignment calculation
        alignment = 0.5
        matched_interests = []
        for interest_topic, weight in interests.items():
            if any(t in interest_topic or interest_topic in t for t in tags) or interest_topic in title or interest_topic in desc:
                matched_interests.append((interest_topic, weight))

        if matched_interests:
            alignment = max(w for _, w in matched_interests)
        
        # 2. Novelty calculation (slight randomness + unexplored topic reward)
        is_novel = len(matched_interests) == 0
        novelty_score = 0.85 if is_novel else random.uniform(0.4, 0.75)

        total_score = round(alignment * (1.0 - novelty_weight) + novelty_score * novelty_weight, 3)

        # 3. Explain choice reason
        if matched_interests:
            best_topic = matched_interests[0][0]
            reasons = [
                f"因为我对【{best_topic}】一直保持着浓厚兴趣，这个视频切入的角度非常特别，很想一探究竟！",
                f"正好符合我平时积累的【{best_topic}】知识库，想看看UP主有没有提出不一样的独门见解。",
                f"在我的兴趣雷达里，【{best_topic}】的权重很高，这个标题一下就吸引了我的鱼眼~"
            ]
            reason = random.choice(reasons)
        else:
            reasons = [
                "虽然这个领域我之前接触得不多，但好奇心驱使我游出舒适区，去看看陌生的新天地！",
                "这是一次跳出信息茧房的偶遇！标题里的概念让我很想弄明白它究竟是什么原理。",
                "大肥鱼的直觉告诉我，多涉猎一些冷门未知的领域，说不定能产生意想不到的灵感火花！"
            ]
            reason = random.choice(reasons)

        return total_score, reason

    @classmethod
    def explore(cls, force_refresh: bool = False) -> List[VideoCandidate]:
        """
        Executes an autonomous exploration run ('出去逛逛').
        Filters out already-watched videos, scores remaining candidates, and updates the local candidate pool.
        """
        state = SoulEngine.get_current_state()
        interests = state.interests
        novelty_w = current_settings.novelty_weight

        # Get pool of candidates
        raw_candidates = BilibiliSource.get_candidate_pool()

        # Query already watched BV IDs
        watched_bvids = set()
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT bvid FROM watch_history")
            watched_bvids = {r["bvid"] for r in cursor.fetchall()}

        scored_candidates: List[VideoCandidate] = []
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        with get_db_connection() as conn:
            cursor = conn.cursor()
            for raw in raw_candidates:
                bvid = raw["bvid"]
                # Skip already watched
                if bvid in watched_bvids:
                    continue

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
                    status="discovered"
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
            if not rows:
                # If cache empty, auto-explore
                return cls.explore()

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
