from __future__ import annotations

from pydantic import BaseModel, Field


class GeneratedEmail(BaseModel):
    """Output of the email generator."""

    subject: str = Field(..., description="Suggested subject line.")
    content: str = Field(..., description="Generated email body text.")
    tone: str = Field(..., description="Tone used for generation.")


def _tone_guidance(tone: str) -> str:
    t = (tone or "neutral").strip().lower()
    if t == "formal":
        return "Use a professional, polite, and structured tone."
    if t == "friendly":
        return "Use a warm, approachable, and upbeat tone."
    if t == "concise":
        return "Be brief and to the point. Avoid unnecessary filler."
    if t == "persuasive":
        return "Use a convincing tone with clear value and a call-to-action."
    return "Use a clear, neutral, helpful tone."


# PUBLIC_INTERFACE
def generate_email(*, topic: str, key_points: str, tone: str) -> GeneratedEmail:
    """
    Generate an email draft from topic/key points/tone.

    This is a deterministic stub (no external AI call) designed to be fast (<5s)
    and safe for initial integration. It can be replaced with an AI provider later.
    """
    topic_clean = (topic or "").strip()
    key_points_clean = (key_points or "").strip()
    tone_clean = (tone or "neutral").strip().lower()

    guidance = _tone_guidance(tone_clean)

    subject = f"{topic_clean[:80] or 'Regarding our request'}"
    bullets = ""
    if key_points_clean:
        # normalize into bullets
        lines = [ln.strip("•- \t") for ln in key_points_clean.splitlines() if ln.strip()]
        if len(lines) == 1 and "," in lines[0]:
            lines = [p.strip() for p in lines[0].split(",") if p.strip()]
        bullets = "\n".join([f"- {ln}" for ln in lines[:8]])

    body_parts = [
        f"(Tone guidance: {guidance})",
        "",
        "Hi there,",
        "",
        f"I'm reaching out about: {topic_clean or 'the topic you provided'}.",
    ]
    if bullets:
        body_parts += ["", "Key points:", bullets]
    body_parts += [
        "",
        "Thanks,",
        "—",
    ]

    return GeneratedEmail(subject=subject, content="\n".join(body_parts).strip() + "\n", tone=tone_clean)
