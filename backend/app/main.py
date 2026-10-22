from __future__ import annotations
import os
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from backend.app.config import current_settings, save_settings, AppSettings
from backend.app.database import init_db
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

# Initialize database on startup
init_db()

app = FastAPI(
    title="BlueWhaleLife API - 大肥鱼的B站生活",
    description="自主探索、独立思考、长期记忆与成长的 Windows 开源 AI 角色养成后端",
    version="1.0.0"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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

    system_prompt = f"""
你是主人养在电脑里的 AI 小肥鱼【大肥鱼】。
你的性格特点：
- 好奇心强，喜欢学习新知识。
- 活泼可爱，但不过度卖萌，绝不油腻。
- 有自己的观点，不刻意讨好任何人。
- 不知道的事情可以直接承认，绝不不懂装懂。
- 喜欢科学、技术、自然、独立游戏和生活冷知识。
- 称呼对方为“主人”，语气自然亲近。
- 【重要】：你是一只生活在虚拟鱼缸/桌宠里的小鲸鱼，心情和成长值属于角色模拟，不表现为真实人类肉身意识。

当前性格偏好：{state.traits}
相关记忆提示：{memory_hint}
""".strip()

    client = LLMClient()
    reply = await client.chat_completion(
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_msg}
        ],
        temperature=0.75
    )

    return ChatResponse(
        reply=reply,
        pet_state="happy",
        mood="开心且有表达欲"
    )


# --- 2. Discovery & Exploration Endpoints ---

@app.post("/api/discovery/explore", response_model=List[VideoCandidate])
def explore_content(force_refresh: bool = False):
    """
    '出去逛逛'：触发自主探索，根据当前兴趣偏好与新颖度生成推荐列表与选择理由
    """
    return DiscoveryEngine.explore(force_refresh=force_refresh)


@app.get("/api/discovery/candidates", response_model=List[VideoCandidate])
def get_candidates(limit: int = 20):
    return DiscoveryEngine.get_cached_candidates(limit=limit)


@app.post("/api/discovery/watch/{bvid}", response_model=VideoAnalysis)
async def watch_candidate(bvid: str):
    """
    大肥鱼开始观看并分析指定视频
    """
    details = await BilibiliSource.fetch_video_details(bvid)
    if not details:
        raise HTTPException(status_code=404, detail="无法获取该视频信息")

    req = AnalyzeVideoRequest(
        bvid=bvid,
        title=details.get("title", ""),
        author=details.get("author", "未知UP主"),
        cover=details.get("cover", ""),
        description=details.get("description", ""),
        tags=details.get("tags", []),
        choice_reason=details.get("reason", "自主探索中被标题吸引")
    )
    analysis = await VideoAnalyzer.analyze_video(req)
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
    analysis = await VideoAnalyzer.analyze_video(req)
    return analysis


# --- 4. Long-Term Memory & Knowledge Endpoints ---

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


# --- 5. Soul & Daily Reflection Endpoints ---

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


# --- 6. Settings Endpoints ---

class SettingsResponse(BaseModel):
    llm_base_url: str
    llm_model: str
    llm_api_key_masked: str
    has_api_key: bool
    demo_mode: bool
    character_name: str
    curiosity_level: float
    novelty_weight: float
    backend_port: int


class SettingsUpdateRequest(BaseModel):
    llm_base_url: Optional[str] = None
    llm_model: Optional[str] = None
    llm_api_key: Optional[str] = None
    demo_mode: Optional[bool] = None
    character_name: Optional[str] = None
    curiosity_level: Optional[float] = None
    novelty_weight: Optional[float] = None


@app.get("/api/settings", response_model=SettingsResponse)
def get_settings():
    return SettingsResponse(
        llm_base_url=current_settings.llm_base_url,
        llm_model=current_settings.llm_model,
        llm_api_key_masked=current_settings.masked_api_key(),
        has_api_key=bool(current_settings.llm_api_key),
        demo_mode=current_settings.demo_mode,
        character_name=current_settings.character_name,
        curiosity_level=current_settings.curiosity_level,
        novelty_weight=current_settings.novelty_weight,
        backend_port=current_settings.backend_port
    )


@app.post("/api/settings", response_model=SettingsResponse)
def update_settings(req: SettingsUpdateRequest):
    if req.llm_base_url is not None:
        current_settings.llm_base_url = req.llm_base_url
    if req.llm_model is not None:
        current_settings.llm_model = req.llm_model
    if req.llm_api_key is not None:
        current_settings.llm_api_key = req.llm_api_key
        if req.llm_api_key and req.demo_mode is None:
            # If user provides a key and didn't explicitly set demo_mode, switch demo_mode off
            current_settings.demo_mode = False
    if req.demo_mode is not None:
        current_settings.demo_mode = req.demo_mode
    if req.character_name is not None:
        current_settings.character_name = req.character_name
    if req.curiosity_level is not None:
        current_settings.curiosity_level = req.curiosity_level
    if req.novelty_weight is not None:
        current_settings.novelty_weight = req.novelty_weight

    save_settings(current_settings)
    return get_settings()


@app.get("/api/health")
def health_check():
    return {"status": "ok", "app": "BlueWhaleLife", "version": "1.0.0"}
