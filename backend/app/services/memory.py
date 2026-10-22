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
    Handles viewing history, structured knowledge notes, semantic/keyword search,
    deduplication, and memory forgetting/correction.
    """

    @classmethod
    def record_watch(cls, item: VideoAnalysis) -> None:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            now = item.watched_at or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cursor.execute("""
                INSERT INTO watch_history (
                    bvid, title, author, cover, description, tags, watched_at,
                    choice_reason, summary, learned, viewpoint, doubts,
                    worth_commenting, comment_draft, draft_status, user_notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(bvid) DO UPDATE SET
                    watched_at = excluded.watched_at,
                    summary = excluded.summary,
                    learned = excluded.learned,
                    viewpoint = excluded.viewpoint,
                    doubts = excluded.doubts,
                    worth_commenting = excluded.worth_commenting,
                    comment_draft = excluded.comment_draft,
                    draft_status = excluded.draft_status
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
                item.user_notes
            ))

    @classmethod
    def get_watch_history(cls, limit: int = 50, offset: int = 0) -> List[VideoAnalysis]:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM watch_history
                ORDER BY id DESC LIMIT ? OFFSET ?
            """, (limit, offset))
            rows = cursor.fetchall()
            result = []
            for r in rows:
                tags = json.loads(r["tags"]) if r["tags"] else []
                result.append(VideoAnalysis(
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
                    user_notes=r["user_notes"] or ""
                ))
            return result

    @classmethod
    def get_watch_by_bvid(cls, bvid: str) -> Optional[VideoAnalysis]:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM watch_history WHERE bvid = ?", (bvid,))
            r = cursor.fetchone()
            if not r:
                return None
            tags = json.loads(r["tags"]) if r["tags"] else []
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
                user_notes=r["user_notes"] or ""
            )

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

            cursor.execute("""
                UPDATE watch_history
                SET draft_status = ?, comment_draft = ?, user_notes = ?
                WHERE bvid = ?
            """, (new_status, new_draft, new_notes, bvid))

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
        """
        Soft deletes (forgets) a note, preserving historical integrity while removing it from active memory.
        """
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE knowledge_notes SET is_active = 0 WHERE id = ?", (note_id,))
            return cursor.rowcount > 0

    @classmethod
    def deduplicate_notes(cls) -> int:
        """
        Identifies duplicate notes by identical topic or near-identical content and archives the older duplicates.
        """
        merged_count = 0
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, topic, content FROM knowledge_notes
                WHERE is_active = 1
                ORDER BY id ASC
            """)
            rows = cursor.fetchall()
            seen_topics = {}
            for r in rows:
                t = r["topic"].strip().lower()
                if t in seen_topics:
                    # Mark older or duplicate one inactive
                    cursor.execute("UPDATE knowledge_notes SET is_active = 0 WHERE id = ?", (r["id"],))
                    merged_count += 1
                else:
                    seen_topics[t] = r["id"]

        return merged_count

    @classmethod
    def search_memories(cls, query: str, limit: int = 10) -> MemorySearchResult:
        clean_q = query.strip()
        if not clean_q:
            return MemorySearchResult(query=query)

        search_term = f"%{clean_q}%"
        with get_db_connection() as conn:
            cursor = conn.cursor()
            # 1. Search knowledge notes
            cursor.execute("""
                SELECT * FROM knowledge_notes
                WHERE is_active = 1 AND (topic LIKE ? OR content LIKE ?)
                ORDER BY importance DESC, id DESC LIMIT ?
            """, (search_term, search_term, limit))
            n_rows = cursor.fetchall()
            notes = [
                KnowledgeNote(
                    id=r["id"],
                    topic=r["topic"],
                    content=r["content"],
                    source_bvid=r["source_bvid"],
                    created_at=r["created_at"],
                    importance=r["importance"],
                    is_active=bool(r["is_active"])
                )
                for r in n_rows
            ]

            # 2. Search watch history
            cursor.execute("""
                SELECT bvid, title, author, watched_at, summary, learned, viewpoint
                FROM watch_history
                WHERE title LIKE ? OR learned LIKE ? OR summary LIKE ? OR viewpoint LIKE ?
                ORDER BY id DESC LIMIT ?
            """, (search_term, search_term, search_term, search_term, limit))
            w_rows = cursor.fetchall()
            watches = [dict(r) for r in w_rows]

        return MemorySearchResult(query=query, notes=notes, watches=watches)

    @classmethod
    def get_related_memories(cls, tags: List[str], title: str) -> List[dict]:
        """
        Retrieves related past watches or knowledge notes to let the AI quote/reference previous experiences.
        """
        keywords = tags + [word for word in title.split() if len(word) >= 2]
        related = []
        with get_db_connection() as conn:
            cursor = conn.cursor()
            for kw in keywords[:4]:
                cursor.execute("""
                    SELECT bvid, title, viewpoint, learned FROM watch_history
                    WHERE title LIKE ? OR tags LIKE ?
                    LIMIT 2
                """, (f"%{kw}%", f"%{kw}%"))
                for r in cursor.fetchall():
                    if r["title"] != title and not any(x["bvid"] == r["bvid"] for x in related):
                        related.append(dict(r))
        return related[:3]
