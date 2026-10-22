from __future__ import annotations
import json
from datetime import datetime
from typing import Dict, Any, List, Optional
from backend.app.database import get_db_connection
from backend.app.models.memory import ReflectionLog
from backend.app.services.llm_client import LLMClient
from backend.app.services.soul import SoulEngine
from backend.app.services.memory import MemoryService


class ReflectionEngine:
    """
    Daily Reflection & Growth Engine.
    Reflects on today's discoveries, shifts in viewpoints, new topics of interest,
    and records versioned personality growth with rollback support.
    """

    @classmethod
    async def perform_daily_reflection(cls) -> ReflectionLog:
        # 1. Fetch recent watch history and recent notes
        recent_watches = MemoryService.get_watch_history(limit=5)
        recent_notes = MemoryService.get_knowledge_notes(active_only=True, limit=5)

        watched_summaries = []
        for w in recent_watches:
            watched_summaries.append(f"- 《{w.title}》：观点【{w.viewpoint}】，学到【{w.learned}】，存疑【{w.doubts}】")

        notes_summaries = [f"- {n.topic}：{n.content}" for n in recent_notes]

        experience_text = "\n".join(watched_summaries) if watched_summaries else "（今天还没观看新视频，主要在回味过去的知识库）"
        notes_text = "\n".join(notes_summaries) if notes_summaries else "（暂无新增笔记）"

        # 2. Prompt LLM for structured reflection
        system_prompt = """
你是生活在电脑里的 AI 小肥鱼【大肥鱼】。
现在是你的日常反思时间。请真诚、坦率、有见地地回顾你最近所接触的信息和经历。
请务必回答以下四个核心问题：
1. 今天发现了什么？
2. 什么知识改变了你原来的看法？
3. 对哪些新话题产生了浓厚兴趣？
4. 哪些观点还需要继续核实与观察？

必须以标准 JSON 格式返回，包含以下字段：
{
  "discoveries_summary": "今天的新发现总结（80-150字）",
  "viewpoint_shifts": "有什么认知或看法发生了改变及原因（60-120字）",
  "new_interests": ["新兴趣点1", "新兴趣点2", "新兴趣点3"],
  "pending_doubts": "仍需继续求证的疑问点（50-100字）",
  "growth_score": 15,
  "mood": "今天反思后的模拟心境（例如：'充实且充满探索欲'）"
}
""".strip()

        user_prompt = f"""
【我最近的观影经历】：
{experience_text}

【我最近记录的知识笔记】：
{notes_text}

请进行今天的反思与总结：
""".strip()

        client = LLMClient()
        response_text = await client.chat_completion(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.7,
            response_json=True
        )

        parsed: Dict[str, Any] = {}
        try:
            clean_json = response_text.strip()
            if clean_json.startswith("```json"):
                clean_json = clean_json[7:]
            if clean_json.startswith("```"):
                clean_json = clean_json[3:]
            if clean_json.endswith("```"):
                clean_json = clean_json[:-3]
            parsed = json.loads(clean_json.strip())
        except Exception as e:
            print(f"[ReflectionEngine] JSON parsing fallback: {e}")
            parsed = {
                "discoveries_summary": "今天穿梭在各种有趣的视频与思考中，对大自然与前沿技术的交汇点有了更立体的认识。",
                "viewpoint_shifts": "原先以为复杂的算法只能解决抽象问题，现在发现它们在模拟自然界生物游动时同样充满诗意。",
                "new_interests": ["仿生算法", "极简生活实验"],
                "pending_doubts": "关于高阶系统的扰动容忍度，仍需寻找更多真实测试案例。",
                "growth_score": 15,
                "mood": "满足且若有所思"
            }

        today_date = datetime.now().strftime("%Y-%m-%d")
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        new_interests = parsed.get("new_interests", [])
        if not isinstance(new_interests, list):
            new_interests = [str(new_interests)]

        # 3. Save reflection log into SQLite
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO reflection_logs (
                    date, discoveries_summary, viewpoint_shifts, new_interests,
                    pending_doubts, growth_score, mood, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                today_date,
                parsed.get("discoveries_summary", ""),
                parsed.get("viewpoint_shifts", ""),
                json.dumps(new_interests, ensure_ascii=False),
                parsed.get("pending_doubts", ""),
                int(parsed.get("growth_score", 15)),
                parsed.get("mood", "充实"),
                now_str
            ))
            log_id = cursor.lastrowid

        # 4. Evolve personality state if new interests appeared
        if new_interests:
            reason = f"【日常反思触发演化】在 {today_date} 的反思中，对话题【{', '.join(new_interests[:3])}】产生了新的好奇与探索欲。"
            SoulEngine.evolve_interests(new_interests[:3], reason)

        return ReflectionLog(
            id=log_id,
            date=today_date,
            discoveries_summary=parsed.get("discoveries_summary", ""),
            viewpoint_shifts=parsed.get("viewpoint_shifts", ""),
            new_interests=new_interests,
            pending_doubts=parsed.get("pending_doubts", ""),
            growth_score=int(parsed.get("growth_score", 15)),
            mood=parsed.get("mood", "充实"),
            created_at=now_str
        )

    @classmethod
    def get_reflection_logs(cls, limit: int = 30) -> List[ReflectionLog]:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM reflection_logs
                ORDER BY id DESC LIMIT ?
            """, (limit,))
            rows = cursor.fetchall()
            result = []
            for r in rows:
                new_interests = json.loads(r["new_interests"]) if r["new_interests"] else []
                result.append(ReflectionLog(
                    id=r["id"],
                    date=r["date"],
                    discoveries_summary=r["discoveries_summary"] or "",
                    viewpoint_shifts=r["viewpoint_shifts"] or "",
                    new_interests=new_interests,
                    pending_doubts=r["pending_doubts"] or "",
                    growth_score=r["growth_score"] or 100,
                    mood=r["mood"] or "平常心",
                    created_at=r["created_at"] or ""
                ))
            return result
