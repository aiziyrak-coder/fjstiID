from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.deps import require_roles
from app.models import SystemSetting, User
from app.schemas import MessageOut, SettingOut, SettingsPatch
from app.services.users import write_audit

router = APIRouter(prefix="/api/v1/admin/settings", tags=["admin-settings"])

DEFAULTS = [
    ("institute_name", "Farg'ona Jamoat Salomatligi Tibbiyot Instituti", "Institut nomi"),
    ("institute_short", "FJSTI", "Qisqa nom"),
    ("institute_address", "Farg'ona shahar, Yangi Turon, 2-a uy", "Manzil"),
    ("institute_phone", "+998 95 062-23-45", "Telefon"),
    ("institute_email", "info@fjsti.uz", "Email"),
    ("institute_website", "https://fjsti.uz", "Rasmiy sayt"),
    ("face_match_threshold", "0.45", "FaceID moslik chegarasi"),
    ("default_password", "ChangeMe123!", "Import uchun default parol"),
    ("id_card_footer", "FJSTI ID - rasmiy identifikatsiya", "ID karta pastki yozuvi"),
    ("support_email", "info@fjsti.uz", "Texnik yordam email"),
    ("allow_self_face_request", "true", "Foydalanuvchi Face yangilash so'rovi"),
]


async def ensure_defaults(db: AsyncSession) -> None:
    for key, value, label in DEFAULTS:
        if not await db.get(SystemSetting, key):
            db.add(SystemSetting(key=key, value=value, label=label))
    await db.flush()


@router.get("", response_model=list[SettingOut])
async def get_settings(_: User = Depends(require_roles("admin")), db: AsyncSession = Depends(get_db)):
    await ensure_defaults(db)
    rows = (await db.execute(select(SystemSetting).order_by(SystemSetting.key))).scalars().all()
    return [SettingOut(key=r.key, value=r.value, label=r.label) for r in rows]


@router.put("", response_model=MessageOut)
async def put_settings(
    body: SettingsPatch,
    admin: User = Depends(require_roles("admin")),
    db: AsyncSession = Depends(get_db),
):
    await ensure_defaults(db)
    for item in body.items:
        row = await db.get(SystemSetting, item.key)
        if row:
            row.value = item.value
            if item.label:
                row.label = item.label
        else:
            db.add(SystemSetting(key=item.key, value=item.value, label=item.label))
    await write_audit(db, admin.id, "update", "settings", None, {"keys": [i.key for i in body.items]})
    return MessageOut(message="Sozlamalar saqlandi")
