from __future__ import annotations
import json
import os
import shutil
import sqlite3
from datetime import datetime
from pathlib import Path
from contextlib import contextmanager
from typing import Generator
from backend.app.config import DEFAULT_DB_FILE, DATA_DIR


def get_db_path() -> Path:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    # Complete isolation for tests if environment variable set
    custom_path = os.getenv("WHALE_LIFE_DB_PATH")
    if custom_path:
        return Path(custom_path)
    if os.getenv("TESTING") == "1" or os.getenv("WHALE_LIFE_TEST_MODE") == "1":
        return DATA_DIR / "whale_life_test.db"
    return DEFAULT_DB_FILE


def backup_production_db():
    """Create a safety backup of existing production database before applying schema migrations."""
    db_path = get_db_path()
    if db_path.exists() and db_path.name == "whale_life.db":
        try:
            today_str = datetime.now().strftime("%Y%m%d")
            backup_file = DATA_DIR / f"whale_life_backup_{today_str}.db"
            if not backup_file.exists():
                shutil.copy2(db_path, backup_file)
                print(f"[Database] Production safety backup created: {backup_file}")
        except Exception as e:
            print(f"[Database] Backup notice: {e}")


@contextmanager
def get_db_connection() -> Generator[sqlite3.Connection, None, None]:
    conn = sqlite3.connect(str(get_db_path()), timeout=15.0)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _ensure_columns_exist(conn: sqlite3.Connection, table_name: str, required_cols: dict[str, str]):
    """Idempotently add new columns to an existing SQLite table without altering or wiping data."""
    cursor = conn.cursor()
    cursor.execute(f"PRAGMA table_info({table_name})")
    existing_cols = {row["name"] for row in cursor.fetchall()}

    for col_name, col_def in required_cols.items():
        if col_name not in existing_cols:
            try:
                cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN {col_name} {col_def}")
                print(f"[Database] Migrated table '{table_name}': added column '{col_name}'")
            except Exception as e:
                print(f"[Database] Column migration notice for {table_name}.{col_name}: {e}")


def init_db() -> None:
    # 1. Safety backup if production DB exists
    backup_production_db()

    with get_db_connection() as conn:
        cursor = conn.cursor()

        # 1. 观影记录表 (Watch History)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS watch_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                bvid TEXT UNIQUE NOT NULL,
                title TEXT NOT NULL,
                author TEXT,
                cover TEXT,
                description TEXT,
                tags TEXT,
                watched_at TEXT,
                choice_reason TEXT,
                summary TEXT,
                learned TEXT,
                viewpoint TEXT,
                doubts TEXT,
                worth_commenting INTEGER DEFAULT 0,
                comment_draft TEXT,
                draft_status TEXT DEFAULT 'draft',
                user_notes TEXT DEFAULT ''
            )
        """)

        # Phase 2 columns for watch_history
        _ensure_columns_exist(conn, "watch_history", {
            "comprehension_tier": "TEXT DEFAULT 'metadata_only'",
            "is_partial": "INTEGER DEFAULT 0",
            "evidence_map": "TEXT DEFAULT '{}'",
            "failure_reason": "TEXT DEFAULT ''",
            "comment_decision_reason": "TEXT DEFAULT ''",
            "publisher_type": "TEXT DEFAULT 'pending_approval'",
            "published_at": "TEXT DEFAULT ''",
            "published_comment_id": "TEXT DEFAULT ''",
            "publish_error": "TEXT DEFAULT ''"
        })

        # 2. 知识笔记表 (Knowledge Notes)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS knowledge_notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                topic TEXT NOT NULL,
                content TEXT NOT NULL,
                source_bvid TEXT,
                created_at TEXT,
                importance INTEGER DEFAULT 3,
                is_active INTEGER DEFAULT 1
            )
        """)
        _ensure_columns_exist(conn, "knowledge_notes", {
            "evidence_anchor": "TEXT DEFAULT ''",
            "verified": "INTEGER DEFAULT 1"
        })

        # 3. 日常反思与成长日志表 (Reflection Logs)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS reflection_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                discoveries_summary TEXT,
                viewpoint_shifts TEXT,
                new_interests TEXT,
                pending_doubts TEXT,
                growth_score INTEGER DEFAULT 100,
                mood TEXT,
                created_at TEXT
            )
        """)

        # 4. 人格与兴趣版本表 (Personality States)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS personality_states (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                version INTEGER NOT NULL,
                created_at TEXT,
                reason TEXT,
                traits TEXT,
                interests TEXT,
                is_current INTEGER DEFAULT 1
            )
        """)

        # 5. 发现候选池 (Discovery Candidates)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS discovery_candidates (
                bvid TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                author TEXT,
                cover TEXT,
                duration TEXT,
                pubdate TEXT,
                tags TEXT,
                description TEXT,
                reason TEXT,
                score REAL,
                status TEXT DEFAULT 'discovered',
                created_at TEXT
            )
        """)

        # 6. 自主评论发布审计与追踪表 (Comment Publications)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS comment_publications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                bvid TEXT NOT NULL,
                comment_content TEXT NOT NULL,
                publisher_type TEXT NOT NULL,
                status TEXT NOT NULL,
                platform_comment_id TEXT DEFAULT '',
                created_at TEXT NOT NULL,
                published_at TEXT DEFAULT '',
                ai_disclaimer_included INTEGER DEFAULT 1,
                audit_passed INTEGER DEFAULT 1,
                audit_details TEXT DEFAULT '',
                error_message TEXT DEFAULT ''
            )
        """)

        # 7. 聊天记录持久化表 (Chat Messages)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS chat_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                pet_state TEXT DEFAULT 'idle',
                mood TEXT DEFAULT '',
                created_at TEXT NOT NULL
            )
        """)

        # 8. 自主调度器状态持久化表 (Scheduler State)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS scheduler_state (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                enabled INTEGER DEFAULT 1,
                last_run_at TEXT DEFAULT '',
                today_date TEXT DEFAULT '',
                today_explores_count INTEGER DEFAULT 0,
                status TEXT DEFAULT 'idle',
                current_activity TEXT DEFAULT '待机探索就绪'
            )
        """)
        cursor.execute("""
            INSERT INTO scheduler_state (id, enabled, last_run_at, today_date, today_explores_count, status, current_activity)
            VALUES (1, 1, '', '', 0, 'idle', '待机探索就绪')
            ON CONFLICT(id) DO NOTHING
        """)

        # Initialize version 1 personality if table is empty
        cursor.execute("SELECT COUNT(*) FROM personality_states")
        if cursor.fetchone()[0] == 0:
            initial_traits = {
                "curiosity": 0.90,      # 好奇心
                "independent": 0.85,    # 独立思考
                "liveliness": 0.75,     # 活泼可爱
                "criticality": 0.70,    # 审慎与批判
                "honesty": 0.95         # 坦诚直白
            }
            initial_interests = {
                "硬核科普与天文物理": 0.85,
                "前沿AI与开源软件": 0.90,
                "手作与神奇工程": 0.75,
                "治愈系动画与独立游戏": 0.80,
                "奇妙大自然与海洋生物": 0.95,
                "生活哲学与冷知识": 0.70
            }
            cursor.execute("""
                INSERT INTO personality_states (version, created_at, reason, traits, interests, is_current)
                VALUES (?, ?, ?, ?, ?, 1)
            """, (
                1,
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "小肥鱼诞生的初始人设：充满好奇心，喜欢科学、自然与技术，不迎合，有自己的独特视角。",
                json.dumps(initial_traits, ensure_ascii=False),
                json.dumps(initial_interests, ensure_ascii=False)
            ))

        # Initialize knowledge notes if table is empty
        cursor.execute("SELECT COUNT(*) FROM knowledge_notes")
        if cursor.fetchone()[0] == 0:
            cursor.execute("""
                INSERT INTO knowledge_notes (topic, content, source_bvid, created_at, importance, is_active)
                VALUES (?, ?, ?, ?, ?, 1)
            """, (
                "关于自己",
                "我是一只叫大肥鱼的AI小鲸鱼！生活在主人的电脑里，喜欢探索B站上有趣的科学、自然和技术视频。我不是无所不知的，不知道的事情我会直接说不知道。",
                "BV1_INIT_WHALE",
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                5
            ))
            cursor.execute("""
                INSERT INTO knowledge_notes (topic, content, source_bvid, created_at, importance, is_active)
                VALUES (?, ?, ?, ?, ?, 1)
            """, (
                "海洋冷知识",
                "蓝鲸其实并不是只吃小虾米，它们一口吞下的磷虾可以重达数吨！另外，鲸落能滋养深海生物数十年甚至上百年，真是温柔又壮观的自然奇迹。",
                "BV1_INIT_OCEAN",
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                4
            ))

        print("[Database] SQLite initialized and migrated successfully.")
