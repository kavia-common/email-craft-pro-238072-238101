from __future__ import annotations

from typing import Optional
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


class UserRow(dict):
    """Typed dict-like container for a users table row."""


# PUBLIC_INTERFACE
async def get_user_by_email(session: AsyncSession, email: str) -> Optional[UserRow]:
    """Fetch a user by email (case-insensitive due to CITEXT)."""
    res = await session.execute(
        text(
            """
            SELECT id, name, email, password_hash, created_at, updated_at
            FROM public.users
            WHERE email = :email
            """
        ),
        {"email": email},
    )
    row = res.mappings().first()
    return UserRow(row) if row else None


# PUBLIC_INTERFACE
async def get_user_by_id(session: AsyncSession, user_id: UUID) -> Optional[UserRow]:
    """Fetch a user by id."""
    res = await session.execute(
        text(
            """
            SELECT id, name, email, password_hash, created_at, updated_at
            FROM public.users
            WHERE id = :id
            """
        ),
        {"id": str(user_id)},
    )
    row = res.mappings().first()
    return UserRow(row) if row else None


# PUBLIC_INTERFACE
async def create_user(session: AsyncSession, *, name: str, email: str, password_hash: str) -> UserRow:
    """Create a new user and return the created row."""
    res = await session.execute(
        text(
            """
            INSERT INTO public.users (name, email, password_hash)
            VALUES (:name, :email, :password_hash)
            RETURNING id, name, email, password_hash, created_at, updated_at
            """
        ),
        {"name": name, "email": email, "password_hash": password_hash},
    )
    await session.commit()
    row = res.mappings().one()
    return UserRow(row)
