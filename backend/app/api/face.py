from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import get_settings
from app.database import get_db
from app.deps import USER_LOAD, bearer, get_client_app, require_roles
from app.models import AccessLog, User
from app.schemas import FaceVerifyResponse, MessageOut
from app.security import create_access_token, decode_token
from app.services.face import get_face_service
from app.services.face_enroll import enroll_face_bytes, ensure_biometric_consent
from app.services.users import user_to_out, write_audit

router = APIRouter(prefix="/api/v1/face", tags=["face"])
settings = get_settings()


@router.post("/enroll", response_model=MessageOut)
async def enroll_face(
    user_id: str = Form(...),
    file: UploadFile = File(...),
    admin: User = Depends(require_roles("admin", "moderator")),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(User)
        .options(selectinload(User.consents), selectinload(User.face_biometrics))
        .where(User.id == user_id, User.is_deleted.is_(False))
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(404, "Foydalanuvchi topilmadi")

    data = await file.read()
    try:
        version = await enroll_face_bytes(db, user, data, ensure_consent=True)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc

    await write_audit(db, admin.id, "enroll", "face_biometric", user.id, {"version": version})
    return MessageOut(message=f"Yuz vektori saqlandi (v{version}) — FaceID tayyor")


async def _resolve_verify_actor(
    db: AsyncSession = Depends(get_db),
    api_client=Depends(get_client_app),
    creds: HTTPAuthorizationCredentials | None = Depends(bearer),
):
    """API kalit YOKI admin/moderator JWT."""
    if api_client is not None:
        return api_client, None
    if creds:
        payload = decode_token(creds.credentials)
        if payload and payload.get("type") == "access":
            uid = payload.get("sub")
            result = await db.execute(
                select(User).options(selectinload(User.roles)).where(User.id == uid, User.is_deleted.is_(False))
            )
            user = result.scalar_one_or_none()
            if user and user.is_active:
                roles = {r.code for r in user.roles}
                if "admin" in roles or "moderator" in roles:
                    return None, user
    raise HTTPException(401, "X-API-Key yoki admin token talab qilinadi")


@router.post("/verify", response_model=FaceVerifyResponse)
async def verify_face(
    file: UploadFile = File(...),
    device_info: str | None = Form(None),
    location: str | None = Form(None),
    db: AsyncSession = Depends(get_db),
    actor=Depends(_resolve_verify_actor),
):
    client, _admin = actor
    data = await file.read()
    try:
        emb = get_face_service().embed_image_bytes(data)
    except ValueError as exc:
        db.add(
            AccessLog(
                method="face",
                success=False,
                device_info=device_info,
                location=location,
                detail=str(exc),
                client_app_id=client.id if client else None,
            )
        )
        raise HTTPException(400, str(exc)) from exc

    emb_literal = "[" + ",".join(str(float(x)) for x in emb.tolist()) + "]"
    q = text(
        """
        SELECT fb.user_id, (fb.embedding <=> CAST(:emb AS vector)) AS distance
        FROM face_biometrics fb
        JOIN users u ON u.id = fb.user_id
        WHERE fb.is_active = true AND fb.archived_at IS NULL AND u.is_active = true AND u.is_deleted = false
        ORDER BY distance ASC
        LIMIT 1
        """
    )
    row = (await db.execute(q, {"emb": emb_literal})).first()
    if not row or row.distance is None or float(row.distance) > settings.face_match_threshold:
        db.add(
            AccessLog(
                method="face",
                success=False,
                device_info=device_info,
                location=location,
                detail=f"no_match dist={getattr(row, 'distance', None)}",
                client_app_id=client.id if client else None,
            )
        )
        return FaceVerifyResponse(matched=False, confidence=None, user=None)

    user_id = str(row.user_id)
    dist = float(row.distance)
    confidence = max(0.0, 1.0 - dist)
    result = await db.execute(select(User).options(*USER_LOAD).where(User.id == user_id))
    user = result.scalar_one()
    db.add(
        AccessLog(
            user_id=user.id,
            method="face",
            success=True,
            device_info=device_info,
            location=location,
            detail=f"dist={dist:.4f}",
            client_app_id=client.id if client else None,
        )
    )
    roles = [r.code for r in user.roles]
    token = create_access_token(user.id, extra={"roles": roles, "auth": "face"})
    return FaceVerifyResponse(matched=True, confidence=confidence, user=user_to_out(user), access_token=token)


@router.post("/verify-qr", response_model=FaceVerifyResponse)
async def verify_qr(
    qr_token: str = Form(...),
    device_info: str | None = Form(None),
    db: AsyncSession = Depends(get_db),
    actor=Depends(_resolve_verify_actor),
):
    client, _ = actor
    result = await db.execute(
        select(User)
        .options(*USER_LOAD)
        .where(User.qr_token == qr_token, User.is_deleted.is_(False), User.is_active.is_(True))
    )
    user = result.scalar_one_or_none()
    db.add(
        AccessLog(
            user_id=user.id if user else None,
            method="qr",
            success=bool(user),
            device_info=device_info,
            client_app_id=client.id if client else None,
        )
    )
    if not user:
        return FaceVerifyResponse(matched=False)
    token = create_access_token(user.id, extra={"roles": [r.code for r in user.roles], "auth": "qr"})
    return FaceVerifyResponse(matched=True, confidence=1.0, user=user_to_out(user), access_token=token)


@router.post("/consent/{user_id}", response_model=MessageOut)
async def grant_consent(
    user_id: str,
    admin: User = Depends(require_roles("admin", "moderator")),
    db: AsyncSession = Depends(get_db),
):
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(404, "Foydalanuvchi topilmadi")
    # need consents loaded lightly
    result = await db.execute(
        select(User).options(selectinload(User.consents)).where(User.id == user_id)
    )
    user = result.scalar_one()
    await ensure_biometric_consent(db, user)
    await write_audit(db, admin.id, "consent", "user", user_id)
    return MessageOut(message="Rozilik qayd etildi")
