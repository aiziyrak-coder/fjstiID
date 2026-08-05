from __future__ import annotations

import csv
import io
import math
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import HTMLResponse, StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.deps import require_roles
from app.models import (
    Address,
    Consent,
    Department,
    EmergencyContact,
    IdentityDocument,
    Role,
    StaffProfile,
    StudentProfile,
    StudyGroup,
    User,
    UserRole,
)
from app.schemas import (
    BulkActionIn,
    BulkActionOut,
    ImportResult,
    MessageOut,
    PageUsers,
    UserCreate,
    UserOut,
    UserUpdate,
)
from app.security import generate_token, hash_password
from app.services.users import PHOTO_DIR, compose_full_name, user_to_list_item, user_to_out, write_audit
from app.services.webhooks import dispatch_webhooks

router = APIRouter(prefix="/api/v1/admin/users", tags=["admin-users"])

ALLOWED_STATUSES = {"active", "inactive", "suspended", "graduated", "dismissed", "archived"}

LOAD_OPTS = (
    selectinload(User.roles),
    selectinload(User.document),
    selectinload(User.address),
    selectinload(User.emergency_contact),
    selectinload(User.student_profile).selectinload(StudentProfile.faculty),
    selectinload(User.student_profile).selectinload(StudentProfile.specialty),
    selectinload(User.student_profile)
    .selectinload(StudentProfile.group)
    .selectinload(StudyGroup.department)
    .selectinload(Department.faculty),
    selectinload(User.staff_profile).selectinload(StaffProfile.department),
    selectinload(User.face_biometrics),
    selectinload(User.consents),
)


async def _load_user(db: AsyncSession, user_id: str, *, include_deleted: bool = False) -> User:
    stmt = select(User).options(*LOAD_OPTS).where(User.id == user_id)
    if not include_deleted:
        stmt = stmt.where(User.is_deleted.is_(False))
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Foydalanuvchi topilmadi")
    return user


async def _set_roles(db: AsyncSession, user: User, role_codes: list[str]) -> None:
    roles = (await db.execute(select(Role).where(Role.code.in_(role_codes)))).scalars().all()
    found = {r.code for r in roles}
    missing = set(role_codes) - found
    if missing:
        raise HTTPException(status_code=400, detail=f"Noma'lum rollar: {', '.join(missing)}")
    await db.execute(UserRole.__table__.delete().where(UserRole.user_id == user.id))
    for r in roles:
        db.add(UserRole(user_id=user.id, role_id=r.id))


def _apply_person(user: User, person) -> None:
    user.last_name = person.last_name
    user.first_name = person.first_name
    user.middle_name = person.middle_name
    user.full_name = compose_full_name(person.last_name, person.first_name, person.middle_name)
    user.gender = person.gender
    user.birth_date = person.birth_date
    user.birth_place = person.birth_place
    user.nationality = person.nationality
    user.citizenship = person.citizenship
    user.marital_status = person.marital_status
    user.blood_type = person.blood_type
    user.pinfl = person.pinfl
    user.notes = person.notes


def _upsert_document(user: User, doc, db: AsyncSession) -> None:
    if user.document:
        for k, v in doc.model_dump().items():
            setattr(user.document, k, v)
    else:
        db.add(IdentityDocument(user_id=user.id, **doc.model_dump()))


def _upsert_address(user: User, addr, db: AsyncSession) -> None:
    data = addr.model_dump()
    if not data.get("full_text"):
        parts = [data.get("region"), data.get("district"), data.get("mahalla"), data.get("street"), data.get("house")]
        data["full_text"] = ", ".join(p for p in parts if p)
    if user.address:
        for k, v in data.items():
            setattr(user.address, k, v)
    else:
        db.add(Address(user_id=user.id, **data))


def _upsert_emergency(user: User, em, db: AsyncSession) -> None:
    if user.emergency_contact:
        for k, v in em.model_dump().items():
            setattr(user.emergency_contact, k, v)
    else:
        db.add(EmergencyContact(user_id=user.id, **em.model_dump()))


def _apply_status(user: User, status: str) -> None:
    if status not in ALLOWED_STATUSES:
        raise HTTPException(400, f"Status ruxsat etilmagan: {status}")
    user.status = status
    user.is_active = status == "active"
    if status == "archived":
        user.is_deleted = True
        user.is_active = False


@router.get("", response_model=PageUsers)
async def list_users(
    q: str | None = None,
    role: str | None = None,
    kind: str | None = None,
    status: str | None = None,
    faculty_id: str | None = None,
    department_id: str | None = None,
    group_id: str | None = None,
    has_face: bool | None = None,
    is_active: bool | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=200),
    admin: User = Depends(require_roles("admin", "moderator")),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(User).options(*LOAD_OPTS).where(User.is_deleted.is_(False)).order_by(User.full_name.asc())
    users = list((await db.execute(stmt)).scalars().unique().all())

    if q:
        ql = q.lower().strip()

        def match(u: User) -> bool:
            blobs = [
                u.full_name,
                u.last_name,
                u.first_name,
                u.email,
                u.phone,
                u.pinfl,
                u.document.number if u.document else None,
                u.document.series if u.document else None,
                u.student_profile.student_number if u.student_profile else None,
                u.staff_profile.employee_number if u.staff_profile else None,
                u.student_profile.group.name if u.student_profile and u.student_profile.group else None,
            ]
            return any(ql in (b or "").lower() for b in blobs)

        users = [u for u in users if match(u)]

    def codes(u: User) -> set[str]:
        return {r.code for r in u.roles}

    if kind == "students":
        users = [u for u in users if "student" in codes(u) and "staff" not in codes(u)]
    elif kind == "staff":
        users = [u for u in users if "staff" in codes(u) and "student" not in codes(u)]
    elif kind == "both":
        users = [u for u in users if "student" in codes(u) and "staff" in codes(u)]
    elif role:
        users = [u for u in users if role in codes(u)]

    if status:
        users = [u for u in users if (u.status or "active") == status]
    if is_active is not None:
        users = [u for u in users if u.is_active is is_active]
    if faculty_id:
        users = [
            u
            for u in users
            if (u.student_profile and u.student_profile.faculty_id == faculty_id)
            or (
                u.staff_profile
                and u.staff_profile.department
                and u.staff_profile.department.faculty_id == faculty_id
            )
        ]
    if department_id:
        users = [
            u
            for u in users
            if (u.staff_profile and u.staff_profile.department_id == department_id)
            or (
                u.student_profile
                and u.student_profile.group
                and u.student_profile.group.department_id == department_id
            )
        ]
    if group_id:
        users = [u for u in users if u.student_profile and u.student_profile.group_id == group_id]
    if has_face is not None:
        users = [
            u
            for u in users
            if any(f.is_active and f.archived_at is None for f in (u.face_biometrics or [])) is has_face
        ]

    admin_roles = {r.code for r in admin.roles}
    if "admin" not in admin_roles and "moderator" in admin_roles:
        dept_id = admin.staff_profile.department_id if admin.staff_profile else None
        fac_id = None
        if dept_id:
            dept = await db.get(Department, dept_id)
            fac_id = dept.faculty_id if dept else None
        if fac_id:
            users = [
                u
                for u in users
                if (u.student_profile and u.student_profile.faculty_id == fac_id)
                or (
                    u.staff_profile
                    and u.staff_profile.department
                    and u.staff_profile.department.faculty_id == fac_id
                )
            ]
        elif dept_id:
            users = [
                u
                for u in users
                if (u.staff_profile and u.staff_profile.department_id == dept_id)
                or (
                    u.student_profile
                    and u.student_profile.group
                    and u.student_profile.group.department_id == dept_id
                )
            ]

    total = len(users)
    pages = max(1, math.ceil(total / page_size))
    start = (page - 1) * page_size
    page_items = users[start : start + page_size]
    return PageUsers(
        items=[user_to_list_item(u) for u in page_items],
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )


@router.post("", response_model=UserOut, status_code=201)
async def create_user(
    body: UserCreate,
    admin: User = Depends(require_roles("admin", "moderator")),
    db: AsyncSession = Depends(get_db),
):
    if body.contacts.email:
        if await db.scalar(select(User).where(User.email == body.contacts.email)):
            raise HTTPException(400, "Email band")
    if body.person.pinfl:
        if await db.scalar(select(User).where(User.pinfl == body.person.pinfl)):
            raise HTTPException(400, "JSHSHIR band")
    if body.student:
        if await db.scalar(select(StudentProfile).where(StudentProfile.student_number == body.student.student_number)):
            raise HTTPException(400, "Talaba ID band")
    if body.staff:
        if await db.scalar(select(StaffProfile).where(StaffProfile.employee_number == body.staff.employee_number)):
            raise HTTPException(400, "Xodim ID band")

    user = User(
        last_name=body.person.last_name,
        first_name=body.person.first_name,
        middle_name=body.person.middle_name,
        full_name=compose_full_name(body.person.last_name, body.person.first_name, body.person.middle_name),
        gender=body.person.gender,
        birth_date=body.person.birth_date,
        birth_place=body.person.birth_place,
        nationality=body.person.nationality,
        citizenship=body.person.citizenship or "O'zbekiston",
        marital_status=body.person.marital_status,
        blood_type=body.person.blood_type,
        pinfl=body.person.pinfl,
        notes=body.person.notes,
        phone=body.contacts.phone,
        phone_additional=body.contacts.phone_additional,
        email=body.contacts.email,
        password_hash=hash_password(body.password) if body.password else None,
        qr_token=generate_token(16),
        status="active",
    )
    db.add(user)
    await db.flush()

    if body.role_codes:
        await _set_roles(db, user, body.role_codes)
    if body.document:
        db.add(IdentityDocument(user_id=user.id, **body.document.model_dump()))
    if body.address:
        _upsert_address(user, body.address, db)
    if body.emergency:
        db.add(EmergencyContact(user_id=user.id, **body.emergency.model_dump()))
    if body.student:
        sp_data = body.student.model_dump()
        if sp_data.get("group_id") and not sp_data.get("faculty_id"):
            g = await db.get(StudyGroup, sp_data["group_id"])
            if g and g.department_id:
                dept = await db.get(Department, g.department_id)
                if dept and dept.faculty_id:
                    sp_data["faculty_id"] = dept.faculty_id
        db.add(StudentProfile(user_id=user.id, **sp_data))
    if body.staff:
        db.add(StaffProfile(user_id=user.id, **body.staff.model_dump()))
    if body.grant_biometric_consent:
        db.add(Consent(user_id=user.id, consent_type="biometric", granted=True))

    await write_audit(db, admin.id, "create", "user", user.id, {"full_name": user.full_name})
    await db.flush()
    user = await _load_user(db, user.id)
    await dispatch_webhooks(db, "user.created", user_to_out(user).model_dump(mode="json"))
    return user_to_out(user)


@router.post("/bulk", response_model=BulkActionOut)
async def bulk_action(
    body: BulkActionIn,
    admin: User = Depends(require_roles("admin")),
    db: AsyncSession = Depends(get_db),
):
    if not body.user_ids:
        raise HTTPException(400, "user_ids bo'sh")
    updated = 0
    for uid in body.user_ids:
        user = await db.get(User, uid)
        if not user or user.is_deleted:
            continue
        if body.action == "activate":
            _apply_status(user, "active")
        elif body.action == "deactivate":
            _apply_status(user, "inactive")
        elif body.action == "archive":
            _apply_status(user, "archived")
            for fb in user.face_biometrics or []:
                fb.is_active = False
                fb.archived_at = datetime.now(timezone.utc)
        elif body.action == "set_status":
            if not body.status:
                raise HTTPException(400, "status kerak")
            _apply_status(user, body.status)
        elif body.action in ("add_role", "remove_role"):
            if not body.role_code:
                raise HTTPException(400, "role_code kerak")
            role = await db.scalar(select(Role).where(Role.code == body.role_code))
            if not role:
                raise HTTPException(400, "Rol topilmadi")
            existing = {r.code for r in (user.roles or [])}
            if body.action == "add_role":
                existing.add(body.role_code)
            else:
                existing.discard(body.role_code)
            await _set_roles(db, user, list(existing) or ["student"])
        updated += 1
    await write_audit(db, admin.id, "bulk", "user", None, {"action": body.action, "count": updated})
    await db.flush()
    return BulkActionOut(updated=updated, message=f"{updated} ta yangilandi")


@router.get("/export.csv")
async def export_users_csv(
    kind: str | None = None,
    faculty_id: str | None = None,
    _: User = Depends(require_roles("admin", "moderator")),
    db: AsyncSession = Depends(get_db),
):
    page = await list_users(
        q=None,
        role=None,
        kind=kind,
        status=None,
        faculty_id=faculty_id,
        department_id=None,
        group_id=None,
        has_face=None,
        is_active=None,
        page=1,
        page_size=200,
        admin=_,
        db=db,
    )
    # export all pages
    all_items = list(page.items)
    for p in range(2, page.pages + 1):
        nxt = await list_users(
            None, None, kind, None, faculty_id, None, None, None, None, p, 200, _, db
        )
        all_items.extend(nxt.items)

    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(
        [
            "full_name",
            "roles",
            "status",
            "pinfl",
            "phone",
            "email",
            "student_number",
            "employee_number",
            "faculty",
            "department",
            "group",
            "has_face",
        ]
    )
    for u in all_items:
        w.writerow(
            [
                u.full_name,
                "|".join(u.roles),
                u.status,
                u.pinfl or "",
                u.phone or "",
                u.email or "",
                u.student_number or "",
                u.employee_number or "",
                u.faculty_name or "",
                u.department_name or "",
                u.group_name or "",
                "1" if u.has_face else "0",
            ]
        )
    data = buf.getvalue().encode("utf-8-sig")
    return StreamingResponse(
        io.BytesIO(data),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=fjsti_users.csv"},
    )


@router.get("/import-template.csv")
async def import_template(_: User = Depends(require_roles("admin"))):
    content = (
        "last_name,first_name,middle_name,gender,pinfl,phone,email,password,"
        "role,student_number,employee_number,group_name,department_code,study_form,funding,position\n"
        "Karimov,Jasur,Aliyevich,male,30101011234567,+998901234567,jasur@fjsti.uz,ChangeMe123!,"
        "student,STU-2025-100,,,DI-101,,kunduzgi,kontrakt,\n"
        "Saidova,Dilnoza,,female,,+998907778899,dilnoza@fjsti.uz,ChangeMe123!,"
        "staff,,EMP-3001,,IT,,,Assistent\n"
    )
    return StreamingResponse(
        io.BytesIO(content.encode("utf-8-sig")),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=import_template.csv"},
    )


@router.post("/import.csv", response_model=ImportResult)
async def import_users_csv(
    file: UploadFile = File(...),
    admin: User = Depends(require_roles("admin")),
    db: AsyncSession = Depends(get_db),
):
    raw = (await file.read()).decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(raw))
    created = skipped = 0
    errors: list[str] = []
    for i, row in enumerate(reader, start=2):
        try:
            last = (row.get("last_name") or "").strip()
            first = (row.get("first_name") or "").strip()
            if not last or not first:
                errors.append(f"Qator {i}: familiya/ism majburiy")
                skipped += 1
                continue
            email = (row.get("email") or "").strip() or None
            pinfl = (row.get("pinfl") or "").strip() or None
            if email and await db.scalar(select(User).where(User.email == email)):
                errors.append(f"Qator {i}: email band ({email})")
                skipped += 1
                continue
            role = (row.get("role") or "student").strip().lower()
            role_codes = [r.strip() for r in role.split("|") if r.strip()]
            if role in ("both", "aralash"):
                role_codes = ["student", "staff"]
            if not role_codes:
                role_codes = ["student"]

            user = User(
                last_name=last,
                first_name=first,
                middle_name=(row.get("middle_name") or "").strip() or None,
                full_name=compose_full_name(last, first, (row.get("middle_name") or "").strip() or None),
                gender=(row.get("gender") or "").strip() or None,
                pinfl=pinfl,
                phone=(row.get("phone") or "").strip() or None,
                email=email,
                password_hash=hash_password((row.get("password") or "ChangeMe123!").strip()),
                qr_token=generate_token(16),
                citizenship="O'zbekiston",
                status="active",
            )
            db.add(user)
            await db.flush()
            await _set_roles(db, user, role_codes)

            if "student" in role_codes:
                sn = (row.get("student_number") or "").strip()
                if not sn:
                    sn = f"STU-IMP-{user.id[:8].upper()}"
                group_name = (row.get("group_name") or "").strip()
                group = None
                if group_name:
                    group = await db.scalar(select(StudyGroup).where(StudyGroup.name == group_name))
                faculty_id = None
                if group and group.department_id:
                    dept = await db.get(Department, group.department_id)
                    faculty_id = dept.faculty_id if dept else None
                db.add(
                    StudentProfile(
                        user_id=user.id,
                        student_number=sn,
                        group_id=group.id if group else None,
                        faculty_id=faculty_id,
                        study_form=(row.get("study_form") or "kunduzgi").strip(),
                        funding=(row.get("funding") or "kontrakt").strip(),
                        education_level="bakalavr",
                    )
                )

            if "staff" in role_codes:
                en = (row.get("employee_number") or "").strip() or f"EMP-IMP-{user.id[:8].upper()}"
                dept_code = (row.get("department_code") or "").strip()
                dept = None
                if dept_code:
                    dept = await db.scalar(select(Department).where(Department.code == dept_code))
                db.add(
                    StaffProfile(
                        user_id=user.id,
                        employee_number=en,
                        department_id=dept.id if dept else None,
                        position=(row.get("position") or "").strip() or None,
                    )
                )

            db.add(Consent(user_id=user.id, consent_type="biometric", granted=True))
            created += 1
        except Exception as exc:  # noqa: BLE001
            errors.append(f"Qator {i}: {exc}")
            skipped += 1
    await write_audit(db, admin.id, "import", "user", None, {"created": created, "skipped": skipped})
    await db.flush()
    return ImportResult(created=created, skipped=skipped, errors=errors[:50])


@router.get("/{user_id}", response_model=UserOut)
async def get_user(
    user_id: str,
    _: User = Depends(require_roles("admin", "moderator")),
    db: AsyncSession = Depends(get_db),
):
    return user_to_out(await _load_user(db, user_id))


@router.get("/{user_id}/id-card", response_class=HTMLResponse)
async def id_card(
    user_id: str,
    _: User = Depends(require_roles("admin", "moderator")),
    db: AsyncSession = Depends(get_db),
):
    user = await _load_user(db, user_id)
    roles = ", ".join(r.name_uz for r in user.roles) or "—"
    sid = user.student_profile.student_number if user.student_profile else None
    eid = user.staff_profile.employee_number if user.staff_profile else None
    id_label = sid or eid or user.pinfl or user.id[:8]
    fac = ""
    grp = ""
    if user.student_profile:
        fac = user.student_profile.faculty.name if user.student_profile.faculty else ""
        grp = user.student_profile.group.name if user.student_profile.group else ""
    dept = user.staff_profile.department.name if user.staff_profile and user.staff_profile.department else ""
    from app.config import get_settings as _gs

    base = _gs().oidc_issuer.rstrip("/")
    photo = f"{base}/media/{user.photo_path}" if user.photo_path else ""
    html = f"""<!DOCTYPE html>
<html lang="uz"><head><meta charset="utf-8"><title>ID — {user.full_name}</title>
<style>
@page {{ size: 85.6mm 53.98mm; margin: 0 }}
body {{ margin:0; font-family: Georgia, 'Times New Roman', serif; background:#e8eee9 }}
.card {{ width:85.6mm; height:53.98mm; background:linear-gradient(135deg,#0b3d2e 0%,#1a5c45 55%,#0b3d2e 100%);
  color:#fff; border-radius:4mm; padding:3.5mm; box-sizing:border-box; position:relative;
  box-shadow:0 8px 24px rgba(0,0,0,.25); display:grid; grid-template-columns:18mm 1fr; gap:3mm }}
.photo {{ width:18mm; height:22mm; background:#123; border:1px solid #c4a35a; border-radius:2mm;
  object-fit:cover; background-size:cover }}
.brand {{ font-size:7pt; letter-spacing:.08em; color:#c4a35a; text-transform:uppercase }}
.name {{ font-size:11pt; font-weight:700; margin:.5mm 0; line-height:1.15 }}
.meta {{ font-size:7.5pt; opacity:.9; line-height:1.35 }}
.qr {{ position:absolute; right:3.5mm; bottom:3.5mm; font-size:6.5pt; background:rgba(255,255,255,.12);
  padding:1.5mm 2mm; border-radius:1.5mm; max-width:28mm; word-break:break-all }}
.badge {{ display:inline-block; background:#c4a35a; color:#0b3d2e; font-size:6.5pt; font-weight:700;
  padding:.8mm 2mm; border-radius:1mm; margin-top:1mm }}
@media print {{ body {{ background:#fff }} .card {{ box-shadow:none }} .noprint {{ display:none }} }}
.noprint {{ margin:16px; font-family:system-ui }}
button {{ padding:10px 16px; background:#0b3d2e; color:#fff; border:0; border-radius:8px; cursor:pointer }}
</style></head><body>
<div class="noprint"><button onclick="window.print()">Chop etish / PDF</button></div>
<div class="card">
  <div>{'<img class="photo" src="'+photo+'"/>' if photo else '<div class="photo"></div>'}</div>
  <div>
    <div class="brand">FJSTI ID</div>
    <div class="name">{user.full_name}</div>
    <div class="meta">
      ID: <strong>{id_label}</strong><br/>
      {roles}<br/>
      {f'Fakultet: {fac}<br/>' if fac else ''}
      {f'Guruh: {grp}<br/>' if grp else ''}
      {f'Bo‘lim: {dept}<br/>' if dept else ''}
    </div>
    <span class="badge">{(user.status or 'active').upper()}</span>
  </div>
  <div class="qr">QR: {user.qr_token or '—'}</div>
</div>
</body></html>"""
    return HTMLResponse(html)


@router.patch("/{user_id}", response_model=UserOut)
async def update_user(
    user_id: str,
    body: UserUpdate,
    admin: User = Depends(require_roles("admin", "moderator")),
    db: AsyncSession = Depends(get_db),
):
    user = await _load_user(db, user_id)
    if body.person:
        _apply_person(user, body.person)
    if body.contacts:
        user.phone = body.contacts.phone if body.contacts.phone is not None else user.phone
        user.phone_additional = (
            body.contacts.phone_additional if body.contacts.phone_additional is not None else user.phone_additional
        )
        user.email = body.contacts.email if body.contacts.email is not None else user.email
    if body.document is not None:
        _upsert_document(user, body.document, db)
    if body.address is not None:
        _upsert_address(user, body.address, db)
    if body.emergency is not None:
        _upsert_emergency(user, body.emergency, db)
    if body.student is not None:
        if user.student_profile:
            for k, v in body.student.model_dump().items():
                setattr(user.student_profile, k, v)
        else:
            db.add(StudentProfile(user_id=user.id, **body.student.model_dump()))
    if body.staff is not None:
        if user.staff_profile:
            for k, v in body.staff.model_dump().items():
                setattr(user.staff_profile, k, v)
        else:
            db.add(StaffProfile(user_id=user.id, **body.staff.model_dump()))
    if body.role_codes is not None:
        await _set_roles(db, user, body.role_codes)
    if body.password:
        user.password_hash = hash_password(body.password)
    if body.status is not None:
        _apply_status(user, body.status)
    elif body.is_active is not None:
        user.is_active = body.is_active
        user.status = "active" if body.is_active else "inactive"

    await write_audit(db, admin.id, "update", "user", user.id)
    await db.flush()
    user = await _load_user(db, user.id)
    await dispatch_webhooks(db, "user.updated", user_to_out(user).model_dump(mode="json"))
    return user_to_out(user)


@router.post("/{user_id}/reset-password", response_model=MessageOut)
async def reset_password(
    user_id: str,
    password: str = Query(..., min_length=8),
    admin: User = Depends(require_roles("admin")),
    db: AsyncSession = Depends(get_db),
):
    user = await _load_user(db, user_id)
    user.password_hash = hash_password(password)
    await write_audit(db, admin.id, "reset_password", "user", user.id)
    return MessageOut(message="Parol yangilandi")


@router.post("/{user_id}/restore", response_model=UserOut)
async def restore_user(
    user_id: str,
    admin: User = Depends(require_roles("admin")),
    db: AsyncSession = Depends(get_db),
):
    user = await _load_user(db, user_id, include_deleted=True)
    user.is_deleted = False
    _apply_status(user, "active")
    await write_audit(db, admin.id, "restore", "user", user.id)
    await db.flush()
    return user_to_out(await _load_user(db, user.id))


@router.post("/{user_id}/photo", response_model=UserOut)
async def upload_photo(
    user_id: str,
    file: UploadFile = File(...),
    enroll_face: bool = True,
    admin: User = Depends(require_roles("admin", "moderator")),
    db: AsyncSession = Depends(get_db),
):
    user = await _load_user(db, user_id)
    content = await file.read()
    if len(content) > 8 * 1024 * 1024:
        raise HTTPException(400, "Rasm 8MB dan oshmasin")
    ext = Path(file.filename or "photo.jpg").suffix.lower() or ".jpg"
    if ext not in {".jpg", ".jpeg", ".png", ".webp"}:
        raise HTTPException(400, "Faqat jpg/png/webp")
    PHOTO_DIR.mkdir(parents=True, exist_ok=True)
    fname = f"{user.id}_{uuid.uuid4().hex[:8]}{ext}"
    (PHOTO_DIR / fname).write_bytes(content)
    user.photo_path = f"photos/{fname}"

    face_note = None
    if enroll_face:
        from app.services.face_enroll import enroll_face_bytes

        # reload with face/consent relationships
        user = await _load_user(db, user_id)
        try:
            version = await enroll_face_bytes(db, user, content, ensure_consent=True)
            face_note = f"face_v{version}"
        except ValueError as exc:
            # rasm saqlanadi, lekin FaceID enroll bo'lmadi
            face_note = f"face_fail:{exc}"

    await write_audit(db, admin.id, "photo", "user", user.id, {"face": face_note})
    await db.flush()
    out = user_to_out(await _load_user(db, user.id))
    return out


@router.delete("/{user_id}", response_model=MessageOut)
async def delete_user(
    user_id: str,
    admin: User = Depends(require_roles("admin")),
    db: AsyncSession = Depends(get_db),
):
    user = await _load_user(db, user_id)
    _apply_status(user, "archived")
    for fb in user.face_biometrics:
        fb.is_active = False
        fb.archived_at = datetime.now(timezone.utc)
    await write_audit(db, admin.id, "delete", "user", user.id)
    return MessageOut(message="Foydalanuvchi arxivlandi")
