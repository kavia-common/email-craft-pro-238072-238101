import uuid
from typing import AsyncGenerator, Callable

import pytest
from fastapi.testclient import TestClient

from src.api.main import app
from src.core.auth import create_access_token, get_current_user_id


@pytest.fixture()
def user_id() -> uuid.UUID:
    """Deterministic test user id."""
    return uuid.UUID("11111111-1111-1111-1111-111111111111")


@pytest.fixture()
def client() -> TestClient:
    """
    FastAPI test client.

    Note: We avoid overriding DB session globally; tests monkeypatch repo functions
    (create_email/list_emails/delete_email/get_user_by_email/create_user) so the
    endpoints never touch the database.
    """
    return TestClient(app)


@pytest.fixture()
def override_auth(user_id: uuid.UUID) -> AsyncGenerator[None, None]:
    """Override auth dependency so protected endpoints treat requests as authenticated."""
    async def _get_current_user_id_override() -> uuid.UUID:
        return user_id

    app.dependency_overrides[get_current_user_id] = _get_current_user_id_override
    try:
        yield
    finally:
        app.dependency_overrides.pop(get_current_user_id, None)


@pytest.fixture()
def auth_header(user_id: uuid.UUID) -> dict:
    """Build a real JWT header (still validated by get_current_user_id if not overridden)."""
    token = create_access_token(user_id=user_id)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def make_user_row(user_id: uuid.UUID) -> Callable[..., dict]:
    """Factory for a user row dict matching repos/users.py expectations."""
    def _factory(
        *,
        id: uuid.UUID = user_id,
        name: str = "Test User",
        email: str = "test@example.com",
        password_hash: str = "$2b$12$abcdefghijklmnopqrstuv"  # not used unless verify_password is invoked
    ) -> dict:
        return {"id": str(id), "name": name, "email": email, "password_hash": password_hash}

    return _factory


@pytest.fixture()
def make_email_row(user_id: uuid.UUID) -> Callable[..., dict]:
    """Factory for an email row dict matching repos/emails.py expectations."""
    from datetime import datetime, timezone

    def _factory(
        *,
        id: uuid.UUID | None = None,
        subject: str = "Subject",
        content: str = "Body",
        tone: str = "neutral",
        created_at=None,
        updated_at=None,
    ) -> dict:
        now = datetime.now(timezone.utc)
        return {
            "id": str(id or uuid.uuid4()),
            "user_id": str(user_id),
            "subject": subject,
            "content": content,
            "tone": tone,
            "created_at": created_at or now,
            "updated_at": updated_at or now,
        }

    return _factory
