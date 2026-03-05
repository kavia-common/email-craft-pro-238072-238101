from __future__ import annotations

from typing import List, Optional
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


class EmailRow(dict):
    """Typed dict-like container for an emails table row."""


# PUBLIC_INTERFACE
async def create_email(
    session: AsyncSession,
    *,
    user_id: UUID,
    subject: str,
    content: str,
    tone: str,
) -> EmailRow:
    """Persist an email draft for a user."""
    res = await session.execute(
        text(
            """
            INSERT INTO public.emails (user_id, subject, content, tone)
            VALUES (:user_id, :subject, :content, :tone)
            RETURNING id, user_id, subject, content, tone, created_at, updated_at
            """
        ),
        {
            "user_id": str(user_id),
            "subject": subject or "",
            "content": content,
            "tone": tone or "neutral",
        },
    )
    await session.commit()
    return EmailRow(res.mappings().one())


# PUBLIC_INTERFACE
async def list_emails(session: AsyncSession, *, user_id: UUID, limit: int = 50, offset: int = 0) -> List[EmailRow]:
    """List a user's email history ordered by most recently updated/created."""
    res = await session.execute(
        text(
            """
            SELECT id, user_id, subject, content, tone, created_at, updated_at
            FROM public.emails
            WHERE user_id = :user_id
            ORDER BY updated_at DESC, created_at DESC
            LIMIT :limit OFFSET :offset
            """
        ),
        {"user_id": str(user_id), "limit": int(limit), "offset": int(offset)},
    )
    return [EmailRow(r) for r in res.mappings().all()]


# PUBLIC_INTERFACE
async def delete_email(session: AsyncSession, *, user_id: UUID, email_id: UUID) -> bool:
    """Delete an email by id for a given user. Returns True if deleted."""
    res = await session.execute(
        text(
            """
            DELETE FROM public.emails
            WHERE id = :email_id AND user_id = :user_id
            """
        ),
        {"email_id": str(email_id), "user_id": str(user_id)},
    )
    await session.commit()
    return (res.rowcount or 0) > 0


# PUBLIC_INTERFACE
async def get_email(session: AsyncSession, *, user_id: UUID, email_id: UUID) -> Optional[EmailRow]:
    """Fetch a single email by id (scoped to the owner)."""
    res = await session.execute(
        text(
            """
            SELECT id, user_id, subject, content, tone, created_at, updated_at
            FROM public.emails
            WHERE id = :email_id AND user_id = :user_id
            """
        ),
        {"email_id": str(email_id), "user_id": str(user_id)},
    )
    row = res.mappings().first()
    return EmailRow(row) if row else None
