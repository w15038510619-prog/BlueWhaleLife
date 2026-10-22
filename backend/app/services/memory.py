from __future__ import annotations
import json
from datetime import datetime
from typing import List, Optional, Dict, Any
from backend.app.database import get_db_connection
from backend.app.models.video import VideoAnalysis, UpdateDraftRequest
from backend.app.models.memory import KnowledgeNote, KnowledgeNoteCreate, KnowledgeNoteUpdate, MemorySearchResult


class MemoryService:
    """
    SQLite Long-Term Memory System.
    Handles viewing history, tiered comprehension evidence, structured knowledge notes,
    semantic/keyword search, deduplication, and memory forgetting/correction.
    """

    @classmethod
    def record_watch(cls, item: VideoAnalysis) -> None:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            now = item.watched_at or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            evidence_json = json.dumps(item.evidence_map or {}, ensure_ascii=False)

            cursor.execute("""
                INSERT INTO watch_history (
                    bvid, title, author, cover, description, tags, watched_at,
                    choice_reason, summary, learned, viewpoint, doubts,
                    worth_commenting, comment_draft, draft_status, user_notes,
                    comprehension_tier, is_partial, evidence_map, failure_reason,
                    comment_decision_reason, publisher_type, published_at,
                    published_comment_id, publish_error
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(bvid) DO UPDATE SET
                    watched_at = excluded.watched_at,
                    summary = excluded.summary,
                    learned = excluded.learned,
                    viewpoint = excluded.viewpoint,
                    doubts = excluded.doubts,
                    worth_commenting = excluded.worth_commenting,
                    comment_draft = excluded.comment_draft,
                    draft_status = excluded.draft_status,
                    comprehension_tier = excluded.comprehension_tier,
                    is_partial = excluded.is_partial,
                    evidence_map = excluded.evidence_map,
                    failure_reason = excluded.failure_reason,
                    comment_decision_reason = excluded.comment_decision_reason,
                    publisher_type = excluded.publisher_type,
                    published_at = excluded.published_at,
                    published_comment_id = excluded.published_comment_id,
                    publish_error = excluded.publish_error
            """, (
                item.bvid,
                item.title,
                item.author,
                item.cover,
                item.description,
                json.dumps(item.tags, ensure_ascii=False),
                now,
                item.choice_reason,
                item.summary,
                item.learned,
                item.viewpoint,
                item.doubts,
                1 if item.worth_commenting else 0,
                item.comment_draft,
                item.draft_status,
                item.user_notes,
                item.comprehension_tier,
                1 if item.is_partial else 0,
                evidence_json,
                item.failure_reason,
                item.comment_decision_reason,
                item.publisher_type,
                item.published_at,
                item.published_comment_id,
                item.publish_error
            ))

    @classmethod
    def _row_to_analysis(cls, r: Any) -> VideoAnalysis:
        tags = json.loads(r["tags"]) if r["tags"] else []
        ev_map = {}
        if "evidence_map" in r.keys() and r["evidence_map"]:
            try:
                ev_map = json.loads(r["evidence_map"])
            except Exception:
                pass

        return VideoAnalysis(
            bvid=r["bvid"],
            title=r["title"],
            author=r["author"] or "未知UP主",
            cover=r["cover"] or "",
            description=r["description"] or "",
            tags=tags,
            watched_at=r["watched_at"] or "",
            choice_reason=r["choice_reason"] or "",
            summary=r["summary"] or "",
            learned=r["learned"] or "",
            viewpoint=r["viewpoint"] or "",
            doubts=r["doubts"] or "",
            worth_commenting=bool(r["worth_commenting"]),
            comment_draft=r["comment_draft"] or "",
            draft_status=r["draft_status"] or "draft",
            user_notes=r["user_notes"] or "",
            comprehension_tier=r["comprehension_tier"] if "comprehension_tier" in r.keys() and r["comprehension_tier"] else "metadata_only",
            is_partial=bool(r["is_partial"]) if "is_partial" in r.keys() else False,
            evidence_map=ev_map,
            failure_reason=r["failure_reason"] if "failure_reason" in r.keys() and r["failure_reason"] else "",
            comment_decision_reason=r["comment_decision_reason"] if "comment_decision_reason" in r.keys() and r["comment_decision_reason"] else "",
            publisher_type=r["publisher_type"] if "publisher_type" in r.keys() and r["publisher_type"] else "pending_approval",
            published_at=r["published_at"] if "published_at" in r.keys() and r["published_at"] else "",
            published_comment_id=r["published_comment_id"] if "published_comment_id" in r.keys() and r["published_comment_id"] else "",
            publish_error=r["publish_error"] if "publish_error" in r.keys() and r["publish_error"] else ""
        )

    @classmethod
    def get_watch_history(cls, limit: int = 50, offset: int = 0) -> List[VideoAnalysis]:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM watch_history
                ORDER BY id DESC LIMIT ? OFFSET ?
            """, (limit, offset))
            rows = cursor.fetchall()
            return [cls._row_to_analysis(r) for r in rows]

    @classmethod
    def get_watch_by_bvid(cls, bvid: str) -> Optional[VideoAnalysis]:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM watch_history WHERE bvid = ?", (bvid,))
            r = cursor.fetchone()
            if not r:
                return None
            return cls._row_to_analysis(r)

    @classmethod
    def update_draft(cls, bvid: str, req: UpdateDraftRequest) -> Optional[VideoAnalysis]:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            current = cls.get_watch_by_bvid(bvid)
            if not current:
                return None
            new_status = req.draft_status if req.draft_status is not None else current.draft_status
            new_draft = req.comment_draft if req.comment_draft is not None else current.comment_draft
            new_notes = req.user_notes if req.user_notes is not None else current.user_notes
            new_pub = req.publisher_type if req.publisher_type is not None else current.publisher_type

            cursor.execute("""
                UPDATE watch_history
                SET draft_status = ?, comment_draft = ?, user_notes = ?, publisher_type = ?
                WHERE bvid = ?
            """, (new_status, new_draft, new_notes, new_pub, bvid))

        return cls.get_watch_by_bvid(bvid)

    @classmethod
    def add_knowledge_note(cls, req: KnowledgeNoteCreate) -> KnowledgeNote:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO knowledge_notes (topic, content, source_bvid, created_at, importance, is_active)
                VALUES (?, ?, ?, ?, ?, 1)
            """, (req.topic, req.content, req.source_bvid, now, req.importance))
            note_id = cursor.lastrowid
            return KnowledgeNote(
                id=note_id,
                topic=req.topic,
                content=req.content,
                source_bvid=req.source_bvid,
                created_at=now,
                importance=req.importance,
                is_active=True
            )

    @classmethod
    def get_knowledge_notes(cls, active_only: bool = True, limit: int = 100) -> List[KnowledgeNote]:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            sql = "SELECT * FROM knowledge_notes"
            if active_only:
                sql += " WHERE is_active = 1"
            sql += " ORDER BY id DESC LIMIT ?"
            cursor.execute(sql, (limit,))
            rows = cursor.fetchall()
            return [
                KnowledgeNote(
                    id=r["id"],
                    topic=r["topic"],
                    content=r["content"],
                    source_bvid=r["source_bvid"],
                    created_at=r["created_at"],
                    importance=r["importance"],
                    is_active=bool(r["is_active"])
                )
                for r in rows
            ]

    @classmethod
    def update_knowledge_note(cls, note_id: int, req: KnowledgeNoteUpdate) -> Optional[KnowledgeNote]:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM knowledge_notes WHERE id = ?", (note_id,))
            r = cursor.fetchone()
            if not r:
                return None
            topic = req.topic if req.topic is not None else r["topic"]
            content = req.content if req.content is not None else r["content"]
            importance = req.importance if req.importance is not None else r["importance"]
            is_active = 1 if (req.is_active if req.is_active is not None else bool(r["is_active"])) else 0

            cursor.execute("""
                UPDATE knowledge_notes
                SET topic = ?, content = ?, importance = ?, is_active = ?
                WHERE id = ?
            """, (topic, content, importance, is_active, note_id))

        return cls.get_knowledge_note_by_id(note_id)

    @classmethod
    def get_knowledge_note_by_id(cls, note_id: int) -> Optional[KnowledgeNote]:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM knowledge_notes WHERE id = ?", (note_id,))
            r = cursor.fetchone()
            if not r:
                return None
            return KnowledgeNote(
                id=r["id"],
                topic=r["topic"],
                content=r["content"],
                source_bvid=r["source_bvid"],
                created_at=r["created_at"],
                importance=r["importance"],
                is_active=bool(r["is_active"])
            )

    @classmethod
    def forget_knowledge_note(cls, note_id: int) -> bool:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE knowledge_notes SET is_active = 0 WHERE id = ?", (note_id,))
            return cursor.rowcount > 0

    @classmethod
    def deduplicate_notes(cls) -> int:
        merged_count = 0
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM knowledge_notes WHERE is_active = 1 ORDER BY id ASC")
            notes = cursor.fetchall()
            seen_topics: Dict[str, int] = {}
            for n in notes:
                topic = n["topic"].strip()
                if topic in seen_topics:
                    cursor.execute("UPDATE knowledge_notes SET is_active = 0 WHERE id = ?", (n["id"],))
                    merged_count += 1
                else:
                    seen_topics[topic] = n["id"]
        return merged_count

    @classmethod
    def search_memories(cls, query: str, limit: int = 10) -> MemorySearchResult:
        q = f"%{query.strip()}%"
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM watch_history
                WHERE title LIKE ? OR summary LIKE ? OR learned LIKE ? OR viewpoint LIKE ?
                ORDER BY id DESC LIMIT ?
            """, (q, q, q, q, limit))
            video_rows = cursor.fetchall()

            cursor.execute("""
                SELECT * FROM knowledge_notes
                WHERE is_active = 1 AND (topic LIKE ? OR content LIKE ?)
                ORDER BY importance DESC, id DESC LIMIT ?
            """, (q, q, limit))
            note_rows = cursor.fetchall()

            matched_videos = [cls._row_to_analysis(r) for r in video_rows]
            matched_notes = [
                KnowledgeNote(
                    id=r["id"],
                    topic=r["topic"],
                    content=r["content"],
                    source_bvid=r["source_bvid"],
                    created_at=r["created_at"],
                    importance=r["importance"],
                    is_active=bool(r["is_active"])
                )
                for r in note_rows
            ]

            return MemorySearchResult(
                videos=matched_videos,
                notes=matched_notes,
                query=query
            )

    @classmethod
    def get_related_memories(cls, tags: List[str], title: str, limit: int = 3) -> List[Dict[str, Any]]:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM watch_history ORDER BY id DESC LIMIT 40")
            rows = cursor.fetchall()
            related = []
            for r in rows:
                r_tags = json.loads(r["tags"]) if r["tags"] else []
                overlap = set(tags).intersection(set(r_tags))
                if overlap or any(word in r["title"] for word in title.split() if len(word) > 2):
                    related.append({
                        "bvid": r["bvid"],
                        "title": r["title"],
                        "viewpoint": r["viewpoint"],
                        "learned": r["learned"]
                    })
                    if len(related) >= limit:
                        break
            return related

    # Chat history persistence
    @classmethod
    def record_chat_message(cls, role: str, content: str, pet_state: str = "idle", mood: str = "") -> None:
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO chat_messages (role, content, pet_state, mood, created_at)
                VALUES (?, ?, ?, ?, ?)
            """, (role, content, pet_state, mood, now_str))

    @classmethod
    def get_recent_chat_history(cls, limit: int = 30) -> List[Dict[str, Any]]:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM chat_messages
                ORDER BY id ASC LIMIT ?
            """, (limit,))
            rows = cursor.fetchall()
            return [
                {
                    "id": r["id"],
                    "role": r["role"],
                    "content": r["content"],
                    "pet_state": r["pet_state"],
                    "mood": r["mood"],
                    "created_at": r["created_at"]
                }
                for r in rows
            ]
