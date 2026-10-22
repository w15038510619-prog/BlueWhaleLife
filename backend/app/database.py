from __future__ import annotations
import json
import sqlite3
from datetime import datetime
from pathlib import Path
from contextlib import contextmanager
from typing import Generator
from backend.app.config import DB_FILE, DATA_DIR


def get_db_path() -> Path:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    return DB_FILE


@contextmanager
def get_db_connection() -> Generator[sqlite3.Connection, None, None]:
    conn = sqlite3.connect(str(get_db_path()), timeout=10.0)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db() -> None:
    get_db_path()
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # 1. 观影记录表
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
        
        # 2. 知识笔记表 (带遗忘和纠错)
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
        
        # 3. 日常反思与成长日志表
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
        
        # 4. 人格与兴趣版本表 (支持回滚与理由追溯)
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
        
        # 5. 发现候选池
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

        # 检查是否已有人格初始版本，若无则初始化版本 1
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
            
        # 检查是否已有初始知识笔记
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
            
        print("[Database] SQLite initialized successfully.")
