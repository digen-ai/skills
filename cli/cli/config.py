"""CLI configuration management.

Stores settings in ~/.digen/skill.yaml (separate from the admin-side
skill-dev CLI, which uses ~/.vidagent/config.yaml).
"""

from pathlib import Path
from typing import Optional
from uuid import uuid4

import yaml

DEFAULT_API_URL = "https://api.digen.ai"
DEFAULT_LOGIN_URL = "https://agent.digen.ai"

CONFIG_DIR = Path.home() / ".digen"
CONFIG_FILE = CONFIG_DIR / "skill.yaml"
SKILL_WORKSPACE_DIR = CONFIG_DIR / "skills"


def _ensure_dirs():
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    SKILL_WORKSPACE_DIR.mkdir(parents=True, exist_ok=True)


def load_config() -> dict:
    _ensure_dirs()
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, "r") as f:
            return yaml.safe_load(f) or {}
    return {}


def save_config(cfg: dict):
    _ensure_dirs()
    with open(CONFIG_FILE, "w") as f:
        yaml.dump(cfg, f, default_flow_style=False, allow_unicode=True)


def get_api_url() -> str:
    return load_config().get("api_url", DEFAULT_API_URL)


def get_login_url() -> str:
    return load_config().get("login_url", DEFAULT_LOGIN_URL)


def get_token() -> Optional[str]:
    return load_config().get("token")


def get_session_id() -> Optional[str]:
    sid = load_config().get("session_id")
    if sid is None or sid == "":
        return None
    return str(sid)


def ensure_session_id() -> str:
    """Return a stable ``digen-sessionid``, creating one if login did not supply it."""
    sid = get_session_id()
    if sid:
        return sid
    sid = str(uuid4())
    cfg = load_config()
    cfg["session_id"] = sid
    save_config(cfg)
    return sid


def get_language() -> str:
    return load_config().get("language") or "en"


def get_token_expires_at() -> Optional[int]:
    raw = load_config().get("token_expires_at")
    if raw is None or raw == "":
        return None
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None


def get_user_id() -> Optional[int]:
    uid = load_config().get("user_id")
    if uid is None:
        return None
    try:
        return int(uid)
    except (TypeError, ValueError):
        return None


def save_login(*, token: str, user_id: Optional[int] = None, name: Optional[str] = None,
                email: Optional[str] = None, language: Optional[str] = None,
                session_id: Optional[str] = None, token_expires_at: Optional[int] = None) -> None:
    """Persist a successful login response into the config file."""
    cfg = load_config()
    cfg["token"] = token
    cfg["session_id"] = session_id or str(uuid4())
    if user_id is not None:
        cfg["user_id"] = user_id
    if name is not None:
        cfg["name"] = name
    if email is not None:
        cfg["email"] = email
    if language is not None:
        cfg["language"] = language
    if token_expires_at is not None:
        cfg["token_expires_at"] = token_expires_at
    save_config(cfg)


def clear_login() -> None:
    cfg = load_config()
    for key in ("token", "user_id", "name", "email", "language", "session_id", "token_expires_at"):
        cfg.pop(key, None)
    save_config(cfg)
