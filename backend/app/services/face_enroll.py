"""Face enrollment helpers — rasm → embedding → face_biometrics."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Consent, FaceBiometric, User
from app.security import encrypt_bytes
from app.services.face import get_face_service


async def ensure_biometric_consent(db: AsyncSession, user: User) -> None:
    has = any(
        c.consent_type == "biometric" and c.granted and c.revoked_at is None for c in (user.consents or [])
    )
    if not has:
        c = Consent(user_id=user.id, consent_type="biometric", granted=True)
        db.add(c)
        await db.flush()
        if user.consents is not None:
            user.consents.append(c)


async def enroll_face_bytes(
    db: AsyncSession,
    user: User,
    image_bytes: bytes,
    *,
    ensure_consent: bool = True,
) -> int:
    """Rasmdan FaceID embedding yaratib saqlaydi. Yangi version qaytaradi."""
    if ensure_consent:
        await ensure_biometric_consent(db, user)

    emb = get_face_service().embed_image_bytes(image_bytes)

    bios = list(user.face_biometrics or [])
    for fb in bios:
        if fb.is_active:
            fb.is_active = False
            fb.archived_at = datetime.now(timezone.utc)

    version = max((f.version for f in bios), default=0) + 1
    enc = encrypt_bytes(emb.tobytes())
    fb = FaceBiometric(
        user_id=user.id,
        embedding=emb.tolist(),
        embedding_encrypted=enc,
        version=version,
        is_active=True,
    )
    db.add(fb)
    await db.flush()
    if user.face_biometrics is not None:
        user.face_biometrics.append(fb)
    return version
