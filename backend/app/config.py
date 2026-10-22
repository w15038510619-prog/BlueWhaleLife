from __future__ import annotations
import base64
import json
import os
import sys
import hashlib
from pathlib import Path
from typing import Optional, List
from pydantic import BaseModel, Field

if getattr(sys, "frozen", False):
    BASE_DIR = Path(sys.executable).resolve().parent
else:
    BASE_DIR = Path(__file__).resolve().parent.parent.parent

DATA_DIR = BASE_DIR / "data"
CONFIG_FILE = DATA_DIR / "config.json"
DEFAULT_DB_FILE = DATA_DIR / "whale_life.db"


def _get_machine_salt() -> bytes:
    """Generate a stable machine-bound salt for local secret obfuscation."""
    try:
        # Use Windows computer name / user name / system drive serial if available
        ident = f"{os.environ.get('COMPUTERNAME', '')}-{os.environ.get('USERNAME', '')}-BlueWhaleLife-2026"
        return hashlib.sha256(ident.encode("utf-8")).digest()
    except Exception:
        return b"BlueWhaleLife_Default_Protected_Salt_2026"


def protect_secret(plaintext: str) -> str:
    """Reversible machine-bound protection to prevent plaintext key exposure in plain text."""
    if not plaintext:
        return ""
    try:
        # If Windows DPAPI is available via win32crypt or ctypes, we can use it, or XOR with machine hash
        salt = _get_machine_salt()
        data_bytes = plaintext.encode("utf-8")
        obfuscated = bytes([b ^ salt[i % len(salt)] for i, b in enumerate(data_bytes)])
        return "enc:" + base64.b64encode(obfuscated).decode("ascii")
    except Exception:
        return plaintext


def unprotect_secret(ciphertext: str) -> str:
    """Reverse machine-bound protection."""
    if not ciphertext:
        return ""
    if not ciphertext.startswith("enc:"):
        return ciphertext
    try:
        salt = _get_machine_salt()
        raw = base64.b64decode(ciphertext[4:].encode("ascii"))
        recovered = bytes([b ^ salt[i % len(salt)] for i, b in enumerate(raw)])
        return recovered.decode("utf-8")
    except Exception:
        return ""


class AppSettings(BaseModel):
    # LLM Settings (OpenAI-compatible, e.g. DeepSeek, OpenAI, Moonshot, etc.)
    llm_base_url: str = Field(default="https://api.deepseek.com/v1", description="OpenAI-compatible API Base URL")
    llm_model: str = Field(default="deepseek-chat", description="Model name")
    llm_api_key_protected: str = Field(default="", description="Machine-protected API key")
    demo_mode: bool = Field(default=True, description="When true or if api_key is empty, uses intelligent mock simulation")

    # Character Settings
    character_name: str = Field(default="大肥鱼", description="Name of the AI fish")
    curiosity_level: float = Field(default=0.85, ge=0.0, le=1.0, description="Exploration curiosity weight")
    novelty_weight: float = Field(default=0.35, ge=0.0, le=1.0, description="Preference for novel/unfamiliar topics")

    # Server Settings (Strict local binding & trusted local origins)
    backend_host: str = Field(default="127.0.0.1", description="Bind strictly to loopback interface")
    backend_port: int = Field(default=8000, description="FastAPI server port")
    cors_origins: List[str] = Field(
        default=[
            "http://127.0.0.1:8000",
            "http://localhost:8000",
            "http://127.0.0.1:5173",
            "http://localhost:5173"
        ],
        description="Strict trusted local origins"
    )

    # Autonomous Comment & Publisher Settings
    # Publisher types: 'official_api', 'pending_approval', 'webhook', 'local_audit'
    publisher_type: str = Field(default="pending_approval", description="Active publisher mode")
    bilibili_access_token_protected: str = Field(default="", description="Bilibili Open Platform OAuth2 access token")
    bilibili_app_key: str = Field(default="", description="Bilibili Open Platform App Key")
    bilibili_app_secret_protected: str = Field(default="", description="Bilibili Open Platform App Secret")
    webhook_url: str = Field(default="", description="Webhook URL for external comment publishing and alerts")
    emergency_stop: bool = Field(default=False, description="Emergency stop switch: immediately freezes all publishing")
    max_comments_per_day: int = Field(default=3, description="Maximum autonomous comments per day to prevent spam")
    max_comments_per_hour: int = Field(default=1, description="Maximum autonomous comments per hour")
    auto_comment_enabled: bool = Field(default=False, description="Whether autonomous comment submission is enabled")

    # Autonomous Scheduler Settings
    scheduler_enabled: bool = Field(default=True, description="Autonomous background exploration scheduler")
    scheduler_interval_minutes: int = Field(default=30, ge=5, le=180, description="Interval between exploration checks")
    quiet_hours_start: int = Field(default=23, ge=0, le=23, description="Start hour of rest/quiet period")
    quiet_hours_end: int = Field(default=7, ge=0, le=23, description="End hour of rest/quiet period")
    daily_explore_budget: int = Field(default=5, ge=1, le=20, description="Maximum explorations per day")

    @property
    def llm_api_key(self) -> str:
        return unprotect_secret(self.llm_api_key_protected)

    @llm_api_key.setter
    def llm_api_key(self, value: str):
        self.llm_api_key_protected = protect_secret(value)

    @property
    def bilibili_access_token(self) -> str:
        return unprotect_secret(self.bilibili_access_token_protected)

    @bilibili_access_token.setter
    def bilibili_access_token(self, value: str):
        self.bilibili_access_token_protected = protect_secret(value)

    def masked_api_key(self) -> str:
        key = self.llm_api_key
        if not key:
            return ""
        if len(key) <= 8:
            return "******"
        return f"{key[:4]}****{key[-4:]}"

    def masked_bilibili_token(self) -> str:
        token = self.bilibili_access_token
        if not token:
            return ""
        if len(token) <= 8:
            return "******"
        return f"{token[:4]}****{token[-4:]}"


def load_settings() -> AppSettings:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                # Handle migration from old plaintext llm_api_key if present
                if "llm_api_key" in data and not data.get("llm_api_key_protected"):
                    data["llm_api_key_protected"] = protect_secret(data.pop("llm_api_key", ""))
                return AppSettings(**data)
        except Exception as e:
            print(f"[Config] Error loading {CONFIG_FILE}: {e}, using default settings")

    # Also check environment variables for initial setup
    env_key = os.getenv("OPENAI_API_KEY") or os.getenv("DEEPSEEK_API_KEY", "")
    env_base = os.getenv("OPENAI_BASE_URL", "https://api.deepseek.com/v1")
    settings = AppSettings(
        llm_base_url=env_base,
        demo_mode=(not bool(env_key))
    )
    if env_key:
        settings.llm_api_key = env_key

    save_settings(settings)
    return settings


def save_settings(settings: AppSettings) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(settings.model_dump(), f, ensure_ascii=False, indent=2)


current_settings = load_settings()
