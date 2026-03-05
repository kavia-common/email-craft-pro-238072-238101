from __future__ import annotations

from typing import List
from uuid import UUID

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.auth import create_access_token, get_current_user_id, hash_password, verify_password
from src.core.config import get_settings
from src.core.db import get_session, init_engine, ping_db
from src.repos.emails import create_email, delete_email, list_emails
from src.repos.users import create_user, get_user_by_email
from src.services.generation import GeneratedEmail, generate_email


openapi_tags = [
    {"name": "Health", "description": "Service health and diagnostics."},
    {"name": "Auth", "description": "User registration and login (JWT)."},
    {"name": "Generation", "description": "AI email generation (guest allowed)."},
    {"name": "Emails", "description": "Authenticated email draft persistence and history."},
]

app = FastAPI(
    title="AI Email Writer Backend",
    description=(
        "FastAPI backend for AI Email Writer. Supports guest generation and authenticated draft persistence.\n\n"
        "Auth: Use `Authorization: Bearer <token>` header for protected endpoints."
    ),
    version="0.2.0",
    openapi_tags=openapi_tags,
)

settings = get_settings()
init_engine(settings)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=settings.allowed_methods,
    allow_headers=settings.allowed_headers,
    max_age=settings.cors_max_age,
)


class HealthResponse(BaseModel):
    message: str = Field(..., description="Health status message.")
    db_ok: bool = Field(..., description="Whether database connectivity check passed.")


class RegisterRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=200, description="User display name.")
    email: EmailStr = Field(..., description="User email address (unique).")
    password: str = Field(..., min_length=8, max_length=128, description="User password (min 8 chars).")


class AuthResponse(BaseModel):
    access_token: str = Field(..., description="JWT access token.")
    token_type: str = Field("bearer", description="Token type.")
    user_id: UUID = Field(..., description="Authenticated user id.")
    name: str = Field(..., description="User name.")
    email: EmailStr = Field(..., description="User email.")


class LoginRequest(BaseModel):
    email: EmailStr = Field(..., description="User email.")
    password: str = Field(..., description="User password.")


class GenerateEmailRequest(BaseModel):
    topic: str = Field(..., min_length=1, max_length=500, description="Email topic / purpose.")
    key_points: str = Field("", max_length=4000, description="Key bullet points or notes to include.")
    tone: str = Field("neutral", max_length=50, description="Tone: formal, friendly, concise, persuasive, neutral.")


class SaveEmailRequest(BaseModel):
    subject: str = Field("", max_length=500, description="Email subject line.")
    content: str = Field(..., min_length=1, max_length=20000, description="Email draft content.")
    tone: str = Field("neutral", max_length=50, description="Tone used for the draft.")


class EmailItem(BaseModel):
    id: UUID = Field(..., description="Email id.")
    user_id: UUID = Field(..., description="Owner user id.")
    subject: str = Field(..., description="Email subject.")
    content: str = Field(..., description="Email content.")
    tone: str = Field(..., description="Tone.")
    created_at: str = Field(..., description="Creation timestamp (ISO).")
    updated_at: str = Field(..., description="Update timestamp (ISO).")


class EmailsResponse(BaseModel):
    items: List[EmailItem] = Field(..., description="Email drafts.")


class DeleteEmailRequest(BaseModel):
    email_id: UUID = Field(..., description="Email id to delete.")


class DeleteEmailResponse(BaseModel):
    deleted: bool = Field(..., description="Whether a draft was deleted.")


@app.get(
    "/",
    tags=["Health"],
    summary="Health check",
    description="Simple service health check.",
    response_model=HealthResponse,
)
async def health_check(session: AsyncSession = Depends(get_session)) -> HealthResponse:
    """Entrypoint: return API health and basic DB connectivity status."""
    db_ok = False
    try:
        db_ok = await ping_db(session)
    except Exception:
        db_ok = False
    return HealthResponse(message="Healthy", db_ok=db_ok)


@app.post(
    "/register",
    tags=["Auth"],
    summary="Register a new user",
    description="Create a new account with a hashed password, then return a JWT access token.",
    response_model=AuthResponse,
)
async def register(payload: RegisterRequest, session: AsyncSession = Depends(get_session)) -> AuthResponse:
    """Create user in DB; returns JWT token on success."""
    existing = await get_user_by_email(session, str(payload.email))
    if existing:
        raise HTTPException(status_code=409, detail="Email already registered")

    password_hash = hash_password(payload.password)
    user = await create_user(session, name=payload.name, email=str(payload.email), password_hash=password_hash)
    token = create_access_token(user_id=UUID(user["id"]))
    return AuthResponse(
        access_token=token,
        token_type="bearer",
        user_id=UUID(user["id"]),
        name=user["name"],
        email=user["email"],
    )


@app.post(
    "/login",
    tags=["Auth"],
    summary="Login",
    description="Authenticate with email/password and receive a JWT access token.",
    response_model=AuthResponse,
)
async def login(payload: LoginRequest, session: AsyncSession = Depends(get_session)) -> AuthResponse:
    """Validate credentials and issue JWT token."""
    user = await get_user_by_email(session, str(payload.email))
    if not user or not verify_password(payload.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token = create_access_token(user_id=UUID(user["id"]))
    return AuthResponse(
        access_token=token,
        token_type="bearer",
        user_id=UUID(user["id"]),
        name=user["name"],
        email=user["email"],
    )


@app.post(
    "/generate-email",
    tags=["Generation"],
    summary="Generate an email draft",
    description=(
        "Generate an email draft from topic/key points/tone. "
        "This endpoint is available to guest users (no auth required)."
    ),
    response_model=GeneratedEmail,
)
async def generate_email_endpoint(payload: GenerateEmailRequest) -> GeneratedEmail:
    """Generate a draft using a fast deterministic stub (replaceable with AI)."""
    # Keep generation fast and deterministic (no network calls).
    return generate_email(topic=payload.topic, key_points=payload.key_points, tone=payload.tone)


@app.post(
    "/save-email",
    tags=["Emails"],
    summary="Save an email draft",
    description="Persist a draft to the authenticated user's email history.",
    response_model=EmailItem,
)
async def save_email(
    payload: SaveEmailRequest,
    user_id: UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
) -> EmailItem:
    """Save a draft (auth required)."""
    row = await create_email(
        session,
        user_id=user_id,
        subject=payload.subject,
        content=payload.content,
        tone=payload.tone,
    )
    return EmailItem(
        id=UUID(row["id"]),
        user_id=UUID(row["user_id"]),
        subject=row["subject"],
        content=row["content"],
        tone=row["tone"],
        created_at=row["created_at"].isoformat(),
        updated_at=row["updated_at"].isoformat(),
    )


@app.get(
    "/emails",
    tags=["Emails"],
    summary="List email history",
    description="Retrieve authenticated user's saved drafts (most recent first).",
    response_model=EmailsResponse,
)
async def get_emails(
    limit: int = Query(50, ge=1, le=200, description="Max number of items to return."),
    offset: int = Query(0, ge=0, le=10000, description="Offset for pagination."),
    user_id: UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
) -> EmailsResponse:
    """List drafts (auth required)."""
    rows = await list_emails(session, user_id=user_id, limit=limit, offset=offset)
    items = [
        EmailItem(
            id=UUID(r["id"]),
            user_id=UUID(r["user_id"]),
            subject=r["subject"],
            content=r["content"],
            tone=r["tone"],
            created_at=r["created_at"].isoformat(),
            updated_at=r["updated_at"].isoformat(),
        )
        for r in rows
    ]
    return EmailsResponse(items=items)


@app.delete(
    "/delete-email",
    tags=["Emails"],
    summary="Delete an email draft",
    description="Delete a saved draft by id (auth required).",
    response_model=DeleteEmailResponse,
)
async def delete_email_endpoint(
    payload: DeleteEmailRequest,
    user_id: UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
) -> DeleteEmailResponse:
    """Delete a draft (auth required)."""
    deleted = await delete_email(session, user_id=user_id, email_id=payload.email_id)
    if not deleted:
        # Avoid leaking existence of records not owned by the user
        raise HTTPException(status_code=404, detail="Email not found")
    return DeleteEmailResponse(deleted=True)
