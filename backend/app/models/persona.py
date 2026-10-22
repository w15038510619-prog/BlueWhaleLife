from __future__ import annotations
from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class PersonalityState(BaseModel):
    id: Optional[int] = None
    version: int
    created_at: str
    reason: str
    traits: Dict[str, float] = Field(
        default_factory=lambda: {
            "curiosity": 0.90,      # 好奇心
            "independent": 0.85,    # 独立思考
            "liveliness": 0.75,     # 活泼度
            "criticality": 0.70,    # 批判思考/审慎
            "honesty": 0.95         # 坦诚直白
        }
    )
    interests: Dict[str, float] = Field(
        default_factory=lambda: {
            "硬核科普与天文物理": 0.85,
            "前沿AI与开源软件": 0.90,
            "手作与神奇工程": 0.75,
            "治愈系动画与独立游戏": 0.80,
            "奇妙大自然与海洋生物": 0.95,
            "生活哲学与冷知识": 0.70
        }
    )
    is_current: bool = True


class PetStatus(BaseModel):
    state: str = Field(default="idle", description="idle, thinking, happy, confused, studying, resting")
    mood: str = Field(default="好奇而精神", description="Current simulated mood text")
    growth_score: int = Field(default=100, description="Cumulative experience / growth points")
    current_activity: str = Field(default="正在鱼缸里吐泡泡，思考今天的探索计划...", description="Current activity text")
    bubble_text: str = Field(default="今天有什么新奇事物在等着我们呢？", description="Text shown in speech bubble")
    last_bvid: Optional[str] = None
    last_discovery_title: Optional[str] = None


class ChatRequest(BaseModel):
    message: str = Field(..., description="Message from the user to the fish")


class ChatResponse(BaseModel):
    reply: str
    pet_state: str = "happy"
    mood: str = "愉快"
