import uuid

from fastapi import status


def test_save_email_requires_auth(client):
    res = client.post("/save-email", json={"subject": "S", "content": "Hello", "tone": "friendly"})
    assert res.status_code == status.HTTP_401_UNAUTHORIZED
    assert res.json()["detail"] == "Not authenticated"


def test_save_email_success(client, monkeypatch, override_auth, user_id, make_email_row):
    async def _create_email(_session, *, user_id: uuid.UUID, subject: str, content: str, tone: str):
        assert user_id == user_id  # noqa: B015 - explicit check of param existence
        assert subject == "S"
        assert content == "Hello"
        assert tone == "friendly"
        return make_email_row(subject=subject, content=content, tone=tone)

    monkeypatch.setattr("src.api.main.create_email", _create_email)

    res = client.post("/save-email", json={"subject": "S", "content": "Hello", "tone": "friendly"})
    assert res.status_code == status.HTTP_200_OK
    data = res.json()
    assert data["user_id"] == str(user_id)
    assert data["subject"] == "S"
    assert data["content"] == "Hello"
    assert data["tone"] == "friendly"
    uuid.UUID(data["id"])
    assert isinstance(data["created_at"], str) and data["created_at"]
    assert isinstance(data["updated_at"], str) and data["updated_at"]


def test_list_emails_success(client, monkeypatch, override_auth, make_email_row):
    row1 = make_email_row(subject="A")
    row2 = make_email_row(subject="B")

    async def _list_emails(_session, *, user_id: uuid.UUID, limit: int, offset: int):
        assert limit == 2
        assert offset == 0
        return [row1, row2]

    monkeypatch.setattr("src.api.main.list_emails", _list_emails)

    res = client.get("/emails?limit=2&offset=0")
    assert res.status_code == status.HTTP_200_OK
    data = res.json()
    assert "items" in data
    assert [it["subject"] for it in data["items"]] == ["A", "B"]


def test_delete_email_not_found_returns_404(client, monkeypatch, override_auth):
    async def _delete_email(_session, *, user_id: uuid.UUID, email_id: uuid.UUID) -> bool:
        return False

    monkeypatch.setattr("src.api.main.delete_email", _delete_email)

    res = client.request("DELETE", "/delete-email", json={"email_id": str(uuid.uuid4())})
    assert res.status_code == status.HTTP_404_NOT_FOUND
    assert res.json()["detail"] == "Email not found"


def test_delete_email_success(client, monkeypatch, override_auth):
    async def _delete_email(_session, *, user_id: uuid.UUID, email_id: uuid.UUID) -> bool:
        return True

    monkeypatch.setattr("src.api.main.delete_email", _delete_email)

    res = client.request("DELETE", "/delete-email", json={"email_id": str(uuid.uuid4())})
    assert res.status_code == status.HTTP_200_OK
    assert res.json() == {"deleted": True}
