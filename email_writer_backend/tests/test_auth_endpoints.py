import uuid

from fastapi import status


def test_register_success(client, monkeypatch, make_user_row):
    async def _get_user_by_email(_session, _email: str):
        return None

    async def _create_user(_session, *, name: str, email: str, password_hash: str):
        assert name == "Ada"
        assert email == "ada@example.com"
        assert isinstance(password_hash, str) and password_hash
        return make_user_row(name=name, email=email)

    monkeypatch.setattr("src.api.main.get_user_by_email", _get_user_by_email)
    monkeypatch.setattr("src.api.main.create_user", _create_user)

    res = client.post(
        "/register",
        json={"name": "Ada", "email": "ada@example.com", "password": "supersecret1"},
    )
    assert res.status_code == status.HTTP_200_OK
    data = res.json()
    assert data["token_type"] == "bearer"
    assert isinstance(data["access_token"], str) and data["access_token"]
    assert data["email"] == "ada@example.com"
    assert data["name"] == "Ada"
    # UUID string
    uuid.UUID(data["user_id"])


def test_register_conflict_email_already_registered(client, monkeypatch, make_user_row):
    async def _get_user_by_email(_session, _email: str):
        return make_user_row(email=_email)

    monkeypatch.setattr("src.api.main.get_user_by_email", _get_user_by_email)

    res = client.post(
        "/register",
        json={"name": "Ada", "email": "ada@example.com", "password": "supersecret1"},
    )
    assert res.status_code == status.HTTP_409_CONFLICT
    assert res.json()["detail"] == "Email already registered"


def test_login_success(client, monkeypatch, make_user_row):
    async def _get_user_by_email(_session, email: str):
        return make_user_row(email=email, password_hash="irrelevant-hash")

    def _verify_password(password: str, password_hash: str) -> bool:
        assert password == "supersecret1"
        assert password_hash == "irrelevant-hash"
        return True

    monkeypatch.setattr("src.api.main.get_user_by_email", _get_user_by_email)
    monkeypatch.setattr("src.api.main.verify_password", _verify_password)

    res = client.post("/login", json={"email": "ada@example.com", "password": "supersecret1"})
    assert res.status_code == status.HTTP_200_OK
    data = res.json()
    assert data["email"] == "ada@example.com"
    assert data["token_type"] == "bearer"
    assert isinstance(data["access_token"], str) and data["access_token"]
    uuid.UUID(data["user_id"])


def test_login_invalid_credentials_returns_401(client, monkeypatch):
    async def _get_user_by_email(_session, _email: str):
        return None

    monkeypatch.setattr("src.api.main.get_user_by_email", _get_user_by_email)

    res = client.post("/login", json={"email": "nope@example.com", "password": "wrongpass"})
    assert res.status_code == status.HTTP_401_UNAUTHORIZED
    assert res.json()["detail"] == "Invalid email or password"
