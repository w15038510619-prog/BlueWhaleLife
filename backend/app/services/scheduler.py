from __future__ import annotations
import asyncio
from datetime import datetime
from typing import Optional, Dict, Any
from backend.app.config import current_settings
from backend.app.database import get_db_connection
from backend.app.services.discovery import DiscoveryEngine
from backend.app.services.bilibili_source import BilibiliSource
from backend.app.services.analyzer import VideoAnalyzer
from backend.app.services.soul import SoulEngine
from backend.app.models.video import AnalyzeVideoRequest


class AutonomousScheduler:
    """
    Autonomous Life Scheduler for Big Chubby Fish.
    Gives the fish autonomy to explore Bilibili, understand content, rest during quiet hours,
    and respect daily request and cost budgets without requiring manual clicking.
    """

    _task: Optional[asyncio.Task] = None
    _is_running: bool = False

    @classmethod
    def start(cls):
        if cls._task is None or cls._task.done():
            cls._is_running = True
            cls._task = asyncio.create_task(cls._loop())
            print("[Scheduler] Autonomous Life loop started.")

    @classmethod
    def stop(cls):
        cls._is_running = False
        if cls._task and not cls._task.done():
            cls._task.cancel()
            cls._task = None
            print("[Scheduler] Autonomous Life loop stopped.")

    @classmethod
    def _is_quiet_hours(cls, current_hour: int) -> bool:
        start = current_settings.quiet_hours_start
        end = current_settings.quiet_hours_end
        if start > end:  # e.g. 23:00 to 07:00
            return current_hour >= start or current_hour < end
        return start <= current_hour < end

    @classmethod
    def get_status(cls) -> Dict[str, Any]:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM scheduler_state WHERE id = 1")
            row = cursor.fetchone()
            if row:
                return {
                    "enabled": bool(row["enabled"]),
                    "last_run_at": row["last_run_at"] or "",
                    "today_date": row["today_date"] or "",
                    "today_explores_count": row["today_explores_count"] or 0,
                    "status": row["status"] or "idle",
                    "current_activity": row["current_activity"] or "待机中",
                    "daily_budget": current_settings.daily_explore_budget,
                    "quiet_hours": f"{current_settings.quiet_hours_start:02d}:00 - {current_settings.quiet_hours_end:02d}:00",
                    "emergency_stop": current_settings.emergency_stop
                }
            return {
                "enabled": True,
                "status": "idle",
                "current_activity": "待机就绪",
                "today_explores_count": 0,
                "daily_budget": current_settings.daily_explore_budget
            }

    @classmethod
    def _update_state(cls, status: str, activity: str, increment_count: bool = False):
        today_str = datetime.now().strftime("%Y-%m-%d")
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT today_date, today_explores_count FROM scheduler_state WHERE id = 1")
            row = cursor.fetchone()
            count = 0
            if row and row["today_date"] == today_str:
                count = row["today_explores_count"]

            if increment_count:
                count += 1

            cursor.execute("""
                UPDATE scheduler_state SET
                    status = ?,
                    current_activity = ?,
                    today_date = ?,
                    today_explores_count = ?,
                    last_run_at = ?
                WHERE id = 1
            """, (status, activity, today_str, count, now_str))

    @classmethod
    async def run_autonomous_cycle(cls) -> Optional[str]:
        """
        Executes a single autonomous exploration & learning cycle.
        """
        now = datetime.now()
        hour = now.hour
        today_str = now.strftime("%Y-%m-%d")

        # 1. Emergency stop check
        if current_settings.emergency_stop:
            cls._update_state("emergency_stop", "紧急停止开关已激活，小肥鱼暂停一切活动")
            return "紧急停止已激活"

        # 2. Quiet hours check
        if cls._is_quiet_hours(hour):
            cls._update_state("sleeping", f"深夜安静时段 ({current_settings.quiet_hours_start}:00-{current_settings.quiet_hours_end}:00)，大肥鱼正在呼呼大睡~")
            return "进入深夜安静时段"

        # 3. Daily exploration budget check
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT today_date, today_explores_count FROM scheduler_state WHERE id = 1")
            row = cursor.fetchone()
            count = 0
            if row and row["today_date"] == today_str:
                count = row["today_explores_count"]
            if count >= current_settings.daily_explore_budget:
                cls._update_state("resting", f"今日自主探索配额已达成 ({count}/{current_settings.daily_explore_budget})，正在静心消化知识")
                return "今日探索预算已达成"

        # 4. Perform Autonomous Exploration
        cls._update_state("exploring", "大肥鱼正游出鱼缸，自主在B站漫游探索新视频...")
        try:
            candidates = await DiscoveryEngine.explore()
            if not candidates:
                cls._update_state("idle", "本次漫游暂未发现新的合适候选视频，稍后再试")
                return "未发现新视频"

            # Pick highest scored candidate
            top_video = candidates[0]
            cls._update_state("watching", f"正在阅读与理解新视频：《{top_video.title[:15]}...》")

            # Fetch multi-tier video details (metadata + subtitles if present)
            details = await BilibiliSource.fetch_video_details(top_video.bvid)
            if not details or not details.get("is_valid", True):
                cls._update_state("idle", f"视频 {top_video.bvid} 无法访问，记录失败原因并跳过")
                return f"视频 {top_video.bvid} 无法访问"

            req = AnalyzeVideoRequest(
                bvid=top_video.bvid,
                title=details.get("title", top_video.title),
                author=details.get("author", top_video.author),
                cover=details.get("cover", top_video.cover),
                description=details.get("description", top_video.description),
                tags=details.get("tags", top_video.tags),
                subtitles=details.get("subtitles_text", ""),
                choice_reason=top_video.reason
            )

            # Analyze video and run comment decision
            analysis = await VideoAnalyzer.analyze_video(req, details=details)

            # Update count and finished status
            cls._update_state("idle", f"已阅毕《{analysis.title[:15]}》：{analysis.learned[:30]}...", increment_count=True)
            return f"成功观影与思考：《{analysis.title}》"
        except Exception as e:
            cls._update_state("error", f"探索周期出现异常: {str(e)}")
            return f"异常: {e}"

    @classmethod
    async def _loop(cls):
        # Initial gentle delay to let server initialize
        await asyncio.sleep(10)
        while cls._is_running:
            if current_settings.scheduler_enabled:
                try:
                    await cls.run_autonomous_cycle()
                except Exception as e:
                    print(f"[Scheduler] Cycle error: {e}")

            # Sleep for configured interval (minutes to seconds)
            interval_sec = max(60, current_settings.scheduler_interval_minutes * 60)
            try:
                await asyncio.sleep(interval_sec)
            except asyncio.CancelledError:
                break
