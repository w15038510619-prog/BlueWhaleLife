from __future__ import annotations
from typing import List, Optional
from pydantic import BaseModel, Field


class KnowledgeNote(BaseModel):
    id: Optional[int] = None
    topic: str
    content: str
    source_bvid: Optional[str] = None
    created_at: str
    importance: int = Field(default=3, ge=1, le=5)
    is_active: bool = True


class KnowledgeNoteCreate(BaseModel):
    topic: str
    content: str
    source_bvid: Optional[str] = None
    importance: int = Field(default=3, ge=1, le=5)


class KnowledgeNoteUpdate(BaseModel):
    topic: Optional[str] = None
    content: Optional[str] = None
    importance: Optional[int] = None
    is_active: Optional[bool] = None


class ReflectionLog(BaseModel):
    id: Optional[int] = None
    date: str
    discoveries_summary: str
    viewpoint_shifts: str
    new_interests: List[str] = Field(default_factory=list)
    pending_doubts: str
    growth_score: int
    mood: str
    created_at: str


class MemorySearchResult(BaseModel):
    query: str
    notes: List[KnowledgeNote] = Field(default_factory=list)
    watches: List[dict] = Field(default_factory=list)
