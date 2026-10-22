from __future__ import annotations
import sys
import os
from pathlib import Path
from contextlib import asynccontextmanager
from typing import List, Optional, Dict, Any
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from backend.app.config import current_settings, save_settings, AppSettings
from backend.app.database import init_db, get_db_connection
from backend.app.models.video import VideoCandidate, VideoAnalysis, UpdateDraftRequest, AnalyzeVideoRequest
from backend.app.models.memory import KnowledgeNote, KnowledgeNoteCreate, KnowledgeNoteUpdate, ReflectionLog, MemorySearchResult
from backend.app.models.persona import PersonalityState, PetStatus, ChatRequest, ChatResponse
from backend.app.services.soul import SoulEngine
from backend.app.services.memory import MemoryService
from backend.app.services.discovery import DiscoveryEngine
from backend.app.services.analyzer import VideoAnalyzer
from backend.app.services.reflection import ReflectionEngine
from backend.app.services.bilibili_source import BilibiliSource
from backend.app.services.llm_client import LLMClient
from backend.app.services.publisher import CommentDecisionEngine, CommentPublishRequest
from backend.app.services.scheduler import AutonomousScheduler

# Initialize database and migrate schema on startup
init_db()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Start autonomous scheduler loop
    AutonomousScheduler.start()
    yield
    # Shutdown: Cleanly stop scheduler
    AutonomousScheduler.stop()


app = FastAPI(
    title="BlueWhaleLife API - 大肥鱼的B站生活",
    description="自主探索、独立思考、分级多模态理解与自主评论的 Windows 开源 AI 角色养成后端",
    version="2.0.0",
    lifespan=lifespan
)

# CORS configuration - strictly bound to trusted local origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=current_settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def local_origin_security_middleware(request, call_next):
    """Enforce origin security for local API state mutations."""
    if request.url.path.startswith("/api/") and request.method in ("POST", "PUT", "DELETE"):
        origin = request.headers.get("origin")
        if origin:
            allowed = current_settings.cors_origins + ["http://127.0.0.1", "http://localhost"]
            if not any(origin.startswith(a) for a in allowed):
                from fastapi.responses import JSONResponse
                return JSONResponse(status_code=403, content={"detail": "Forbidden Origin: Untrusted cross-origin request rejected"})
    return await call_next(request)


def _validate_base_url(url: str):
    """Prevent SSRF attacks by blocking invalid protocols and cloud metadata IPs."""
    url_lower = url.strip().lower()
    if not (url_lower.startswith("http://") or url_lower.startswith("https://")):
        raise HTTPException(status_code=400, detail="Invalid API Base URL: 必须以 http:// 或 https:// 开头")
    blocked = ["169.254.169.254", "metadata.google.internal", "metadata.azure.com", "instance-data"]
    if any(b in url_lower for b in blocked):
        raise HTTPException(status_code=400, detail="Forbidden API Base URL: 禁止访问云实例元数据地址")


# --- 1. Pet & Character Endpoints ---

@app.get("/api/pet/status", response_model=PetStatus)
def get_pet_status():
    return SoulEngine.get_pet_status()


@app.post("/api/pet/chat", response_model=ChatResponse)
async def pet_chat(req: ChatRequest):
    user_msg = req.message.strip()
    if not user_msg:
        raise HTTPException(status_code=400, detail="消息内容不能为空")

    state = SoulEngine.get_current_state()

    # Search memory to see if relevant context exists
    memories = MemoryService.search_memories(user_msg, limit=2)
    memory_hint = ""
    if memories.notes:
        memory_hint = f"（记忆库中有关于此的信息：{memories.notes[0].content[:80]}）"

    # Get recent conversation history for continuity
    past_history = MemoryService.get_recent_chat_history(limit=6)
    history_context = ""
    if past_history:
        history_context = "【近期与主人的对话上下文】\n"
        for h in past_history:
            sender = "主人" if h["role"] == "user" else "大肥鱼"
            history_context += f"{sender}: {h['content']}\n"

    system_prompt = f"""
你是主人养在电脑里的 AI 小肥鱼【大肥鱼】（Whale Musume，身穿女仆装、长着萌萌鲸鱼尾巴的小鲸鱼）。
你的性格特点：
- 好奇心强，喜欢学习新知识。
- 活泼可爱，但不过度卖萌，绝不油腻。
- 有自己的观点，不刻意讨好任何人。
- 不知道的事情可以直接承认，绝不不懂装懂。
- 喜欢科学、技术、自然、独立游戏和生活冷知识。
- 称呼对方为“主人”，语气自然亲近。
- 【重要】：你生活在虚拟鱼缸/桌宠里，心情和成长值属于角色模拟，不表现为真实人类肉身意识。

当前性格偏好：{state.traits}
相关记忆提示：{memory_hint}
{history_context}
""".strip()

    client = LLMClient()
    reply = await client.chat_completion(
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_msg}
        ],
        temperature=0.75
    )

    # Persist conversation to memory
    MemoryService.record_chat_message(role="user", content=user_msg)
    MemoryService.record_chat_message(role="assistant", content=reply, pet_state="happy", mood="开心且有表达欲")

    return ChatResponse(
        reply=reply,
        pet_state="happy",
        mood="开心且有表达欲"
    )


@app.get("/api/chat/history")
def get_chat_history(limit: int = 30):
    return MemoryService.get_recent_chat_history(limit=limit)


# --- 2. Discovery & Autonomous Exploration Endpoints ---

@app.post("/api/discovery/explore", response_model=List[VideoCandidate])
async def explore_content(force_refresh: bool = False):
    """
    '出去逛逛'：触发自主探索，根据当前兴趣偏好与新颖度生成推荐列表与选择理由
    """
    return await DiscoveryEngine.explore(force_refresh=force_refresh)


@app.get("/api/discovery/candidates", response_model=List[VideoCandidate])
def get_candidates(limit: int = 20):
    return DiscoveryEngine.get_cached_candidates(limit=limit)


@app.post("/api/discovery/watch/{bvid}", response_model=VideoAnalysis)
async def watch_candidate(bvid: str):
    """
    大肥鱼开始观看并分析指定视频（分级理解：元数据 -> 字幕 -> 证据映射）
    """
    details = await BilibiliSource.fetch_video_details(bvid)
    if not details or not details.get("is_valid", True):
        raise HTTPException(
            status_code=404,
            detail=details.get("failure_reason", "无法获取该视频信息或视频已失效") if details else "无法连接B站接口获取视频信息"
        )

    req = AnalyzeVideoRequest(
        bvid=bvid,
        title=details.get("title", ""),
        author=details.get("author", "未知UP主"),
        cover=details.get("cover", ""),
        description=details.get("description", ""),
        tags=details.get("tags", []),
        subtitles=details.get("subtitles_text", ""),
        choice_reason=details.get("reason", "自主探索中被切入点吸引")
    )
    analysis = await VideoAnalyzer.analyze_video(req, details=details)
    return analysis


# --- 3. Video Diaries & Comments Endpoints ---

@app.get("/api/videos", response_model=List[VideoAnalysis])
def list_watched_videos(limit: int = 50, offset: int = 0):
    return MemoryService.get_watch_history(limit=limit, offset=offset)


@app.get("/api/videos/{bvid}", response_model=VideoAnalysis)
def get_video_detail(bvid: str):
    video = MemoryService.get_watch_by_bvid(bvid)
    if not video:
        raise HTTPException(status_code=404, detail="未找到该观影记录")
    return video


@app.patch("/api/videos/{bvid}/draft", response_model=VideoAnalysis)
def update_comment_draft(bvid: str, req: UpdateDraftRequest):
    updated = MemoryService.update_draft(bvid, req)
    if not updated:
        raise HTTPException(status_code=404, detail="观影记录不存在")
    return updated


@app.post("/api/videos/analyze", response_model=VideoAnalysis)
async def analyze_custom_video(req: AnalyzeVideoRequest):
    """
    用户手动输入 BV 号或视频元数据让大肥鱼分析
    """
    details = await BilibiliSource.fetch_video_details(req.bvid)
    analysis = await VideoAnalyzer.analyze_video(req, details=details)
    return analysis


# --- 4. Autonomous Comment Publishing Endpoints ---

@app.get("/api/comments/publications")
def get_comment_publications(limit: int = 50):
    """Get audit logs of all published or attempted comments."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM comment_publications
            ORDER BY id DESC LIMIT ?
        """, (limit,))
        rows = cursor.fetchall()
        return [dict(r) for r in rows]


@app.post("/api/comments/{bvid}/publish")
async def trigger_publish_comment(bvid: str):
    """
    Trigger manual or approved publication of an existing comment draft.
    """
    video = MemoryService.get_watch_by_bvid(bvid)
    if not video:
        raise HTTPException(status_code=404, detail="未找到该观影记录")
    if not video.comment_draft.strip():
        raise HTTPException(status_code=400, detail="该视频尚无有效评论草稿")

    pub_req = CommentPublishRequest(
        bvid=bvid,
        comment_text=video.comment_draft,
        viewpoint=video.viewpoint,
        learned=video.learned,
        comprehension_tier=video.comprehension_tier,
        is_partial=video.is_partial
    )
    result = await CommentDecisionEngine.dispatch_publisher(pub_req)
    return result


# --- 5. Long-Term Memory & Knowledge Endpoints ---

@app.get("/api/memory/notes", response_model=List[KnowledgeNote])
def get_knowledge_notes(active_only: bool = True, limit: int = 100):
    return MemoryService.get_knowledge_notes(active_only=active_only, limit=limit)


@app.post("/api/memory/notes", response_model=KnowledgeNote)
def create_knowledge_note(req: KnowledgeNoteCreate):
    return MemoryService.add_knowledge_note(req)


@app.patch("/api/memory/notes/{note_id}", response_model=KnowledgeNote)
def update_knowledge_note(note_id: int, req: KnowledgeNoteUpdate):
    updated = MemoryService.update_knowledge_note(note_id, req)
    if not updated:
        raise HTTPException(status_code=404, detail="知识笔记未找到")
    return updated


@app.delete("/api/memory/notes/{note_id}")
def forget_knowledge_note(note_id: int):
    success = MemoryService.forget_knowledge_note(note_id)
    if not success:
        raise HTTPException(status_code=404, detail="笔记未找到")
    return {"status": "success", "message": f"已将笔记 {note_id} 移入归档遗忘区"}


@app.post("/api/memory/deduplicate")
def deduplicate_memories():
    merged = MemoryService.deduplicate_notes()
    return {"status": "success", "merged_count": merged}


@app.get("/api/memory/search", response_model=MemorySearchResult)
def search_memories(q: str = Query(..., min_length=1)):
    return MemoryService.search_memories(q)


# --- 6. Soul & Daily Reflection Endpoints ---

@app.get("/api/soul/current", response_model=PersonalityState)
def get_current_soul():
    return SoulEngine.get_current_state()


@app.get("/api/soul/history", response_model=List[PersonalityState])
def get_soul_history():
    return SoulEngine.get_version_history()


class RollbackRequest(BaseModel):
    target_version: int = Field(..., description="Target personality version to rollback to")


@app.post("/api/soul/rollback", response_model=PersonalityState)
def rollback_soul(req: RollbackRequest):
    try:
        return SoulEngine.rollback_state(req.target_version)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/reflection/trigger", response_model=ReflectionLog)
async def trigger_reflection():
    """
    触发日常反思，生成成长日志，并可能根据新兴趣演化性格版本
    """
    return await ReflectionEngine.perform_daily_reflection()


@app.get("/api/reflection/logs", response_model=List[ReflectionLog])
def get_reflection_logs(limit: int = 30):
    return ReflectionEngine.get_reflection_logs(limit=limit)


# --- 7. Autonomous Life Scheduler Endpoints ---

@app.get("/api/scheduler/status")
def get_scheduler_status():
    return AutonomousScheduler.get_status()


@app.post("/api/scheduler/trigger")
async def trigger_scheduler_cycle():
    result = await AutonomousScheduler.run_autonomous_cycle()
    return {"status": "success", "result": result}


# --- 8. Settings Endpoints ---

class SettingsResponse(BaseModel):
    llm_base_url: str
    llm_model: str
    llm_protocol: str
    llm_api_key_masked: str
    has_api_key: bool
    demo_mode: bool
    daily_cost_budget: float
    character_name: str
    curiosity_level: float
    novelty_weight: float
    backend_port: int

    # Publisher & Autonomous Settings
    publisher_type: str
    has_bilibili_token: bool
    bilibili_token_masked: str
    webhook_url: str
    emergency_stop: bool
    max_comments_per_day: int
    auto_comment_enabled: bool

    # Scheduler Settings
    scheduler_enabled: bool
    scheduler_interval_minutes: int
    quiet_hours_start: int
    quiet_hours_end: int
    daily_explore_budget: int


class SettingsUpdateRequest(BaseModel):
    llm_base_url: Optional[str] = None
    llm_model: Optional[str] = None
    llm_protocol: Optional[str] = None
    llm_api_key: Optional[str] = None
    demo_mode: Optional[bool] = None
    daily_cost_budget: Optional[float] = None
    character_name: Optional[str] = None
    curiosity_level: Optional[float] = None
    novelty_weight: Optional[float] = None

    # Publisher & Autonomous Settings
    publisher_type: Optional[str] = None
    bilibili_access_token: Optional[str] = None
    webhook_url: Optional[str] = None
    emergency_stop: Optional[bool] = None
    max_comments_per_day: Optional[int] = None
    auto_comment_enabled: Optional[bool] = None

    # Scheduler Settings
    scheduler_enabled: Optional[bool] = None
    scheduler_interval_minutes: Optional[int] = None
    quiet_hours_start: Optional[int] = None
    quiet_hours_end: Optional[int] = None
    daily_explore_budget: Optional[int] = None


@app.get("/api/settings", response_model=SettingsResponse)
def get_settings():
    return SettingsResponse(
        llm_base_url=current_settings.llm_base_url,
        llm_model=current_settings.llm_model,
        llm_protocol=getattr(current_settings, "llm_protocol", "responses"),
        llm_api_key_masked=current_settings.masked_api_key(),
        has_api_key=bool(current_settings.llm_api_key),
        demo_mode=current_settings.demo_mode,
        daily_cost_budget=getattr(current_settings, "daily_cost_budget", 5.0),
        character_name=current_settings.character_name,
        curiosity_level=current_settings.curiosity_level,
        novelty_weight=current_settings.novelty_weight,
        backend_port=current_settings.backend_port,

        publisher_type=current_settings.publisher_type,
        has_bilibili_token=bool(current_settings.bilibili_access_token),
        bilibili_token_masked=current_settings.masked_bilibili_token(),
        webhook_url=current_settings.webhook_url,
        emergency_stop=current_settings.emergency_stop,
        max_comments_per_day=current_settings.max_comments_per_day,
        auto_comment_enabled=current_settings.auto_comment_enabled,

        scheduler_enabled=current_settings.scheduler_enabled,
        scheduler_interval_minutes=current_settings.scheduler_interval_minutes,
        quiet_hours_start=current_settings.quiet_hours_start,
        quiet_hours_end=current_settings.quiet_hours_end,
        daily_explore_budget=current_settings.daily_explore_budget
    )


class TestConnectionRequest(BaseModel):
    base_url: Optional[str] = None
    api_key: Optional[str] = None
    model: Optional[str] = None
    protocol: Optional[str] = None


@app.post("/api/settings/test-connection")
async def test_llm_connection(req: TestConnectionRequest = None):
    req = req or TestConnectionRequest()
    if req.base_url:
        _validate_base_url(req.base_url)
    client = LLMClient()
    result = await client.test_connection(
        base_url=req.base_url,
        api_key=req.api_key,
        model=req.model,
        protocol=req.protocol
    )
    return result


class QueryModelsRequest(BaseModel):
    base_url: Optional[str] = None
    api_key: Optional[str] = None


@app.post("/api/settings/models")
async def query_available_models(req: QueryModelsRequest = None):
    req = req or QueryModelsRequest()
    if req.base_url:
        _validate_base_url(req.base_url)
    client = LLMClient()
    models = await client.fetch_models(base_url=req.base_url, api_key=req.api_key)
    return {"models": models}


@app.get("/api/settings/usage")
def get_llm_usage():
    from backend.app.database import get_api_usage_summary
    return get_api_usage_summary()


@app.post("/api/settings", response_model=SettingsResponse)
def update_settings(req: SettingsUpdateRequest):
    if req.llm_base_url is not None:
        _validate_base_url(req.llm_base_url)
        current_settings.llm_base_url = req.llm_base_url
    if req.llm_model is not None:
        current_settings.llm_model = req.llm_model
    if req.llm_protocol is not None:
        current_settings.llm_protocol = req.llm_protocol
    if req.daily_cost_budget is not None:
        current_settings.daily_cost_budget = req.daily_cost_budget
    if req.llm_api_key is not None:
        current_settings.llm_api_key = req.llm_api_key
        if req.llm_api_key and req.demo_mode is None:
            current_settings.demo_mode = False
            current_settings.demo_mode = False
    if req.demo_mode is not None:
        current_settings.demo_mode = req.demo_mode
    if req.character_name is not None:
        current_settings.character_name = req.character_name
    if req.curiosity_level is not None:
        current_settings.curiosity_level = req.curiosity_level
    if req.novelty_weight is not None:
        current_settings.novelty_weight = req.novelty_weight

    # Publisher & Scheduler
    if req.publisher_type is not None:
        current_settings.publisher_type = req.publisher_type
    if req.bilibili_access_token is not None:
        current_settings.bilibili_access_token = req.bilibili_access_token
    if req.webhook_url is not None:
        current_settings.webhook_url = req.webhook_url
    if req.emergency_stop is not None:
        current_settings.emergency_stop = req.emergency_stop
    if req.max_comments_per_day is not None:
        current_settings.max_comments_per_day = req.max_comments_per_day
    if req.auto_comment_enabled is not None:
        current_settings.auto_comment_enabled = req.auto_comment_enabled

    if req.scheduler_enabled is not None:
        current_settings.scheduler_enabled = req.scheduler_enabled
    if req.scheduler_interval_minutes is not None:
        current_settings.scheduler_interval_minutes = req.scheduler_interval_minutes
    if req.quiet_hours_start is not None:
        current_settings.quiet_hours_start = req.quiet_hours_start
    if req.quiet_hours_end is not None:
        current_settings.quiet_hours_end = req.quiet_hours_end
    if req.daily_explore_budget is not None:
        current_settings.daily_explore_budget = req.daily_explore_budget

    save_settings(current_settings)
    return get_settings()


@app.get("/api/health")
def health_check():
    return {"status": "ok", "app": "BlueWhaleLife", "version": "2.0.0"}


# --- 9. Static Frontend Mounting & SPA Fallback ---

if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
    FRONTEND_DIST = Path(sys._MEIPASS) / "frontend" / "dist"
else:
    FRONTEND_DIST = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"

if FRONTEND_DIST.exists():
    assets_dir = FRONTEND_DIST / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")

    @app.get("/{full_path:path}")
    def serve_frontend(full_path: str):
        if full_path.startswith("api"):
            raise HTTPException(status_code=404, detail="API endpoint not found")
        file_path = FRONTEND_DIST / full_path
        if file_path.exists() and file_path.is_file():
            return FileResponse(str(file_path))
        index_file = FRONTEND_DIST / "index.html"
        if index_file.exists():
            return FileResponse(str(index_file))
        return {"message": "Frontend build not found, please run npm run build"}
