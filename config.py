"""Application configuration from environment."""
import os
from pathlib import Path

# Load .env so DATABASE_URL etc. are set (skip in tests so conftest's env is used)
try:
    from dotenv import load_dotenv
    if not os.environ.get("TESTING"):
        _env_file = Path(__file__).resolve().parent.parent / ".env"
        load_dotenv(_env_file)
except ImportError:
    pass

BASE_DIR = Path(__file__).resolve().parent


def _get_env(key: str, default: str | None = None) -> str:
    val = os.environ.get(key, default)
    if val is None and key in ("SECRET_KEY", "DATABASE_URL", "JWT_SECRET_KEY"):
        raise ValueError(f"Missing required env: {key}")
    return val or ""


class Config:
    """Base config; env-based, no defaults for secrets in production."""
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-change-me")
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", "postgresql://localhost:5432/bet_db"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True}

    JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY", SECRET_KEY)
    JWT_ACCESS_TOKEN_EXPIRES = int(os.environ.get("JWT_ACCESS_TOKEN_EXPIRES", "3600"))
    JWT_ALGORITHM = "HS256"

    BCRYPT_ROUNDS = 12
