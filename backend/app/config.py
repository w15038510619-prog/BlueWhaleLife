from __future__ import annotations
import json
import os
import sys
from pathlib import Path
from pydantic import BaseModel, Field

if getattr(sys, "frozen", False):
    BASE_DIR = Path(sys.executable).resolve().parent
else:
    BASE_DIR = Path(__file__).resolve().parent.parent.parent

DATA_DIR = BASE_DIR / "data"
CONFIG_FILE = DATA_DIR / "config.json"
DB_FILE = DATA_DIR / "whale_life.db"


class AppSettings(BaseModel):
    # LLM Settings (OpenAI-compatible, e.g. DeepSeek, OpenAI, Moonshot, etc.)
    llm_base_url: str = Field(default="https://api.deepseek.com/v1", description="OpenAI-compatible API Base URL")
    llm_model: str = Field(default="deepseek-chat", description="Model name")
    llm_api_key: str = Field(default="", description="Secret API key (never written to git)")
    demo_mode: bool = Field(default=True, description="When true or if api_key is empty, uses intelligent mock simulation")
    
    # Character Settings
    character_name: str = Field(default="大肥鱼", description="Name of the AI fish")
    curiosity_level: float = Field(default=0.85, ge=0.0, le=1.0, description="Exploration curiosity weight")
    novelty_weight: float = Field(default=0.35, ge=0.0, le=1.0, description="Preference for novel/unfamiliar topics")
    
    # Server Settings
    backend_port: int = Field(default=8000, description="FastAPI server port")
    cors_origins: list[str] = Field(default=["http://localhost:5173", "http://127.0.0.1:5173", "*"])

    def masked_api_key(self) -> str:
        if not self.llm_api_key:
            return ""
        if len(self.llm_api_key) <= 8:
            return "******"
        return f"{self.llm_api_key[:4]}****{self.llm_api_key[-4:]}"


def load_settings() -> AppSettings:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return AppSettings(**data)
        except Exception as e:
            print(f"[Config] Error loading {CONFIG_FILE}: {e}, using default settings")
    
    # Also check environment variables
    env_key = os.getenv("OPENAI_API_KEY") or os.getenv("DEEPSEEK_API_KEY", "")
    env_base = os.getenv("OPENAI_BASE_URL", "https://api.deepseek.com/v1")
    settings = AppSettings(
        llm_api_key=env_key,
        llm_base_url=env_base,
        demo_mode=(not bool(env_key))
    )
    save_settings(settings)
    return settings


def save_settings(settings: AppSettings) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(settings.model_dump(), f, ensure_ascii=False, indent=2)


# Global singleton instance
current_settings = load_settings()
