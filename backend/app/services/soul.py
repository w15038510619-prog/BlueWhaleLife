from __future__ import annotations
import json
from datetime import datetime
from typing import Dict, Any, List, Optional
from backend.app.database import get_db_connection
from backend.app.models.persona import PersonalityState, PetStatus


class SoulEngine:
    """
    Personality & Interest Engine for '大肥鱼' (Big Chubby Fish).
    Tracks versioned traits, dynamic simulated moods, interest weights, and supports master rollback.
    """

    @classmethod
    def get_current_state(cls) -> PersonalityState:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, version, created_at, reason, traits, interests, is_current
                FROM personality_states
                WHERE is_current = 1
                ORDER BY version DESC LIMIT 1
            """)
            row = cursor.fetchone()
            if not row:
                # Fallback to default
                return PersonalityState(
                    version=1,
                    created_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    reason="初始化人设"
                )
            return PersonalityState(
                id=row["id"],
                version=row["version"],
                created_at=row["created_at"],
                reason=row["reason"],
                traits=json.loads(row["traits"]),
                interests=json.loads(row["interests"]),
                is_current=bool(row["is_current"])
            )

    @classmethod
    def evolve_interests(cls, new_topics: List[str], reason: str) -> PersonalityState:
        """
        Evolves interest weights and increments version.
        Saves historical change with human-readable reason.
        """
        current = cls.get_current_state()
        new_version = current.version + 1
        updated_interests = dict(current.interests)

        # Strengthen or introduce new topics
        for topic in new_topics:
            topic_clean = topic.strip()
            if not topic_clean:
                continue
            if topic_clean in updated_interests:
                updated_interests[topic_clean] = min(1.0, round(updated_interests[topic_clean] + 0.05, 2))
            else:
                updated_interests[topic_clean] = 0.75  # Initial exploration weight

        with get_db_connection() as conn:
            cursor = conn.cursor()
            # Mark previous states as not current
            cursor.execute("UPDATE personality_states SET is_current = 0 WHERE is_current = 1")
            cursor.execute("""
                INSERT INTO personality_states (version, created_at, reason, traits, interests, is_current)
                VALUES (?, ?, ?, ?, ?, 1)
            """, (
                new_version,
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                reason,
                json.dumps(current.traits, ensure_ascii=False),
                json.dumps(updated_interests, ensure_ascii=False)
            ))

        return cls.get_current_state()

    @classmethod
    def rollback_state(cls, target_version: int) -> PersonalityState:
        """
        Rollback personality and interests to a specific historical version.
        """
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, version, created_at, reason, traits, interests
                FROM personality_states
                WHERE version = ?
            """, (target_version,))
            row = cursor.fetchone()
            if not row:
                raise ValueError(f"Version {target_version} not found in personality history.")

            # Create a new version that restores target version's parameters with explicit reason
            cursor.execute("SELECT MAX(version) FROM personality_states")
            max_ver = cursor.fetchone()[0] or 1
            new_version = max_ver + 1

            cursor.execute("UPDATE personality_states SET is_current = 0 WHERE is_current = 1")
            cursor.execute("""
                INSERT INTO personality_states (version, created_at, reason, traits, interests, is_current)
                VALUES (?, ?, ?, ?, ?, 1)
            """, (
                new_version,
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                f"【主人指令回滚】成功回退到版本 {target_version} 的性格与兴趣参数设定。",
                row["traits"],
                row["interests"]
            ))

        return cls.get_current_state()

    @classmethod
    def get_version_history(cls) -> List[PersonalityState]:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, version, created_at, reason, traits, interests, is_current
                FROM personality_states
                ORDER BY version DESC
            """)
            rows = cursor.fetchall()
            return [
                PersonalityState(
                    id=r["id"],
                    version=r["version"],
                    created_at=r["created_at"],
                    reason=r["reason"],
                    traits=json.loads(r["traits"]),
                    interests=json.loads(r["interests"]),
                    is_current=bool(r["is_current"])
                )
                for r in rows
            ]

    @classmethod
    def get_pet_status(cls) -> PetStatus:
        """
        Retrieves the simulated status for desktop pet and dashboard.
        """
        with get_db_connection() as conn:
            cursor = conn.cursor()
            # Fetch latest watch for context
            cursor.execute("""
                SELECT bvid, title, watched_at
                FROM watch_history
                ORDER BY id DESC LIMIT 1
            """)
            last_watch = cursor.fetchone()

            # Calculate growth score based on watched videos and knowledge notes
            cursor.execute("SELECT COUNT(*) FROM watch_history")
            watch_count = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM knowledge_notes WHERE is_active = 1")
            note_count = cursor.fetchone()[0]
            growth_score = 100 + (watch_count * 15) + (note_count * 5)

            last_bvid = last_watch["bvid"] if last_watch else None
            last_title = last_watch["title"] if last_watch else None

            activity = "在鱼缸里优哉游哉地吐泡泡，好奇地巡视屏幕..."
            bubble = "今天有什么新奇事物在等着我们呢？"
            state = "idle"
            mood = "好奇而精神"

            if last_title:
                activity = f"刚刚回味完《{last_title[:16]}...》，在笔记本上画了个问号"
                bubble = f"《{last_title[:12]}》里的观点真有意思，让我琢磨了好一会儿！"
                state = "thinking"
                mood = "求知若渴"

            return PetStatus(
                state=state,
                mood=mood,
                growth_score=growth_score,
                current_activity=activity,
                bubble_text=bubble,
                last_bvid=last_bvid,
                last_discovery_title=last_title
            )
