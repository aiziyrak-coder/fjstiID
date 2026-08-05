from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.deps import get_current_user, require_roles
from app.models import AccessLog, FaceUpdateRequest, User
from pydantic import BaseModel

from app.schemas import AccessLogOut, FaceUpdateRequestOut, MessageOut, ProfilePatch, UserOut
from app.services.users import user_to_out, write_audit

router = APIRouter(prefix="/api/v1/users", tags=["users"])


class FaceUpdateNote(BaseModel):
    note: str | None = None


@router.get("/me", response_model=UserOut)
async def my_profile(user: User = Depends(get_current_user)):
    return user_to_out(user)


@router.patch("/me", response_model=UserOut)
async def patch_profile(
    body: ProfilePatch,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    allowed = set(user.editable_fields or [])
    data = body.model_dump(exclude_unset=True)
    if "phone" in data:
        if "phone" not in allowed:
            raise HTTPException(403, "Telefon tahrirlanmaydi")
        user.phone = data["phone"]
    if "phone_additional" in data:
        if "phone_additional" not in allowed:
            raise HTTPException(403, "Qo'shimcha telefon tahrirlanmaydi")
        user.phone_additional = data["phone_additional"]
    if "email" in data:
        if "email" not in allowed:
            raise HTTPException(403, "Email tahrirlanmaydi")
        user.email = data["email"]
    if "address_full" in data:
        if user.address:
            user.address.full_text = data["address_full"]
        else:
            from app.models import Address

            db.add(Address(user_id=user.id, full_text=data["address_full"]))
    if "emergency" in data and data["emergency"] is not None:
        if "emergency_contact" not in allowed and "emergency" not in allowed:
            raise HTTPException(403, "Favqulodda aloqa tahrirlanmaydi")
        em = data["emergency"]
        if user.emergency_contact:
            for k, v in em.items():
                setattr(user.emergency_contact, k, v)
        else:
            from app.models import EmergencyContact

            db.add(EmergencyContact(user_id=user.id, **em))
    await db.flush()
    return user_to_out(user)


@router.get("/me/access-logs", response_model=list[AccessLogOut])
async def my_access_logs(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    rows = (
        await db.execute(
            select(AccessLog).where(AccessLog.user_id == user.id).order_by(AccessLog.created_at.desc()).limit(100)
        )
    ).scalars().all()
    return rows


@router.post("/me/face-update-request", response_model=FaceUpdateRequestOut)
async def request_face_update(
    body: FaceUpdateNote | None = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    req = FaceUpdateRequest(user_id=user.id, note=body.note if body else None, status="pending")
    db.add(req)
    await db.flush()
    return req


@router.get("/face-update-requests", response_model=list[FaceUpdateRequestOut])
async def list_face_requests(
    status: str | None = None,
    _: User = Depends(require_roles("admin", "moderator")),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(FaceUpdateRequest).order_by(FaceUpdateRequest.created_at.desc()).limit(200)
    if status:
        stmt = stmt.where(FaceUpdateRequest.status == status)
    rows = (await db.execute(stmt)).scalars().all()
    out = []
    for r in rows:
        u = await db.get(User, r.user_id)
        out.append(
            FaceUpdateRequestOut(
                id=r.id,
                user_id=r.user_id,
                user_name=u.full_name if u else None,
                status=r.status,
                note=r.note,
                created_at=r.created_at,
                reviewed_at=r.reviewed_at,
            )
        )
    return out


@router.post("/face-update-requests/{req_id}/review", response_model=MessageOut)
async def review_face_request(
    req_id: str,
    approve: bool = True,
    admin: User = Depends(require_roles("admin", "moderator")),
    db: AsyncSession = Depends(get_db),
):
    req = await db.get(FaceUpdateRequest, req_id)
    if not req:
        raise HTTPException(404, "So'rov topilmadi")
    req.status = "approved" if approve else "rejected"
    req.reviewed_by = admin.id
    req.reviewed_at = datetime.now(timezone.utc)
    await write_audit(db, admin.id, "review", "face_update_request", req_id, {"approve": approve})
    return MessageOut(message=req.status)
