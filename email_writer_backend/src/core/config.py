import os
from dataclasses import dataclass
from typing import List


def _split_csv(value: str) -> List[str]:
    return [v.strip() for v in value.split(",") if v.strip()]


@dataclass(frozen=True)
class Settings:
    """Application settings loaded from environment variables."""

    jwt_secret: str
    jwt_algorithm: str
    jwt_exp_minutes: int

    # CORS
    allowed_origins: List[str]
    allowed_methods: List[str]
    allowed_headers: List[str]
    cors_max_age: int

    # Postgres
    postgres_url: str
    postgres_user: str
    postgres_password: str
    postgres_db: str
    postgres_port: str
    postgres_host: str


def get_settings() -> Settings:
    """
    Load settings from environment variables.

    Expected env vars (provided by platform/.env):
    - JWT_SECRET, JWT_ALGORITHM, JWT_EXP_MINUTES
    - ALLOWED_ORIGINS, ALLOWED_METHODS, ALLOWED_HEADERS, CORS_MAX_AGE
    - POSTGRES_URL, POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_DB, POSTGRES_PORT

    POSTGRES_URL may already encode host/port/user/pass/db. We still accept the
    explicit env vars and try to build a SQLAlchemy URL when needed.
    """
    jwt_secret = os.getenv("JWT_SECRET", "")
    if not jwt_secret:
        # IMPORTANT: orchestrator should set JWT_SECRET in .env for production.
        # We use a dev-only fallback to keep local/dev running.
        jwt_secret = "dev-only-insecure-secret"

    jwt_algorithm = os.getenv("JWT_ALGORITHM", "HS256")
    jwt_exp_minutes = int(os.getenv("JWT_EXP_MINUTES", "10080"))  # default: 7 days

    allowed_origins = _split_csv(os.getenv("ALLOWED_ORIGINS", "*")) or ["*"]
    allowed_methods = _split_csv(os.getenv("ALLOWED_METHODS", "*")) or ["*"]
    allowed_headers = _split_csv(os.getenv("ALLOWED_HEADERS", "*")) or ["*"]
    cors_max_age = int(os.getenv("CORS_MAX_AGE", "3600"))

    postgres_url = os.getenv("POSTGRES_URL", "")
    postgres_user = os.getenv("POSTGRES_USER", "")
    postgres_password = os.getenv("POSTGRES_PASSWORD", "")
    postgres_db = os.getenv("POSTGRES_DB", "")
    postgres_port = os.getenv("POSTGRES_PORT", "")

    # Default to the DB container's in-repo connection hint (db_connection.txt uses localhost:5000).
    # Keep host/port overrideable via env for other environments.
    postgres_host = os.getenv("POSTGRES_HOST", "localhost")

    return Settings(
        jwt_secret=jwt_secret,
        jwt_algorithm=jwt_algorithm,
        jwt_exp_minutes=jwt_exp_minutes,
        allowed_origins=allowed_origins,
        allowed_methods=allowed_methods,
        allowed_headers=allowed_headers,
        cors_max_age=cors_max_age,
        postgres_url=postgres_url,
        postgres_user=postgres_user,
        postgres_password=postgres_password,
        postgres_db=postgres_db,
        postgres_port=postgres_port,
        postgres_host=postgres_host,
    )
