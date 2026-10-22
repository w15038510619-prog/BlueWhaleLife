from __future__ import annotations
from typing import Optional, List
from pydantic import BaseModel, Field


class VideoCandidate(BaseModel):
    bvid: str = Field(..., description="Bilibili BV ID")
    title: str = Field(..., description="Video title")
    author: str = Field(default="未知UP主", description="Author / UP name")
    cover: str = Field(default="", description="Cover image URL")
    duration: str = Field(default="05:20", description="Duration string")
    pubdate: str = Field(default="", description="Publish date")
    tags: List[str] = Field(default_factory=list, description="Video topic tags")
    description: str = Field(default="", description="Video description / summary")
    reason: str = Field(default="", description="Why Big Chubby Fish chose this video")
    score: float = Field(default=0.8, description="Interest alignment & novelty score")
    status: str = Field(default="discovered", description="'discovered' | 'watched' | 'skipped'")


class VideoAnalysis(BaseModel):
    bvid: str
    title: str
    author: str = "未知UP主"
    cover: str = ""
    description: str = ""
    tags: List[str] = Field(default_factory=list)
    watched_at: str = ""
    choice_reason: str = ""
    summary: str = Field(..., description="内容概述")
    learned: str = Field(..., description="学到了什么新知识")
    viewpoint: str = Field(..., description="大肥鱼自己的独立观点")
    doubts: str = Field(..., description="可能存在的疑问或未解之处")
    worth_commenting: bool = Field(default=False, description="是否值得参与评论")
    comment_draft: str = Field(default="", description="自然、不重复的评论草稿")
    draft_status: str = Field(default="draft", description="'draft' | 'approved' | 'copied' | 'rejected'")
    user_notes: str = Field(default="", description="主人的批注或修改记录")


class UpdateDraftRequest(BaseModel):
    draft_status: Optional[str] = None
    comment_draft: Optional[str] = None
    user_notes: Optional[str] = None


class AnalyzeVideoRequest(BaseModel):
    bvid: str
    title: str
    author: Optional[str] = "未知UP主"
    cover: Optional[str] = ""
    description: Optional[str] = ""
    tags: Optional[List[str]] = Field(default_factory=list)
    subtitles: Optional[str] = None
    choice_reason: Optional[str] = "主人推荐我看这个！"
