from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AdminAuditLog, User
from app.schemas import (
    AddressOut,
    DocumentOut,
    EmergencyOut,
    RoleOut,
    StaffOut,
    StudentOut,
    UserListItem,
    UserOut,
)

UPLOAD_ROOT = Path(__file__).resolve().parents[2] / "uploads"
PHOTO_DIR = UPLOAD_ROOT / "photos"


def photo_url(user: User) -> str | None:
    if not user.photo_path:
        return None
    return f"/media/{user.photo_path.replace(chr(92), '/')}"


def compose_full_name(last_name: str, first_name: str, middle_name: str | None = None) -> str:
    parts = [last_name.strip(), first_name.strip()]
    if middle_name and middle_name.strip():
        parts.append(middle_name.strip())
    return " ".join(parts)


def role_out(role) -> RoleOut:
    return RoleOut(id=role.id, code=role.code, name_uz=role.name_uz, name=role.code, description=role.description)


def student_out(sp) -> StudentOut | None:
    if not sp:
        return None
    data = StudentOut.model_validate(sp)
    data.faculty_name = sp.faculty.name if sp.faculty else None
    data.specialty_name = sp.specialty.name if sp.specialty else None
    data.group_name = sp.group.name if sp.group else None
    if sp.group and sp.group.department:
        data.department_id = sp.group.department.id
        data.department_name = sp.group.department.name
        if sp.group.department.faculty and not data.faculty_name:
            data.faculty_name = sp.group.department.faculty.name
            data.faculty_id = sp.group.department.faculty.id
    return data


def staff_out(st) -> StaffOut | None:
    if not st:
        return None
    data = StaffOut.model_validate(st)
    data.department_name = st.department.name if st.department else None
    return data


def user_to_out(user: User) -> UserOut:
    has_face = any(f.is_active and f.archived_at is None for f in (user.face_biometrics or []))
    has_consent = any(
        c.consent_type == "biometric" and c.granted and c.revoked_at is None for c in (user.consents or [])
    )
    return UserOut(
        id=user.id,
        last_name=user.last_name,
        first_name=user.first_name,
        middle_name=user.middle_name,
        full_name=user.full_name,
        gender=user.gender,
        birth_date=user.birth_date,
        birth_place=user.birth_place,
        nationality=user.nationality,
        citizenship=user.citizenship,
        marital_status=user.marital_status,
        blood_type=user.blood_type,
        pinfl=user.pinfl,
        notes=user.notes,
        phone=user.phone,
        phone_additional=user.phone_additional,
        email=user.email,
        photo_url=photo_url(user),
        status=user.status or "active",
        is_active=user.is_active,
        qr_token=user.qr_token,
        roles=[role_out(r) for r in (user.roles or [])],
        document=DocumentOut.model_validate(user.document) if user.document else None,
        address=AddressOut.model_validate(user.address) if user.address else None,
        emergency=EmergencyOut.model_validate(user.emergency_contact) if user.emergency_contact else None,
        student=student_out(user.student_profile),
        staff=staff_out(user.staff_profile),
        created_at=user.created_at,
        has_face=has_face,
        has_biometric_consent=has_consent,
    )


def user_to_list_item(user: User) -> UserListItem:
    doc = user.document
    passport = None
    if doc and (doc.series or doc.number):
        passport = f"{doc.series or ''} {doc.number or ''}".strip()
    fac = dept = grp = None
    if user.student_profile:
        fac = user.student_profile.faculty.name if user.student_profile.faculty else None
        grp = user.student_profile.group.name if user.student_profile.group else None
        if user.student_profile.group and user.student_profile.group.department:
            dept = user.student_profile.group.department.name
            if not fac and user.student_profile.group.department.faculty:
                fac = user.student_profile.group.department.faculty.name
    if user.staff_profile and user.staff_profile.department:
        dept = dept or user.staff_profile.department.name
    return UserListItem(
        id=user.id,
        full_name=user.full_name,
        photo_url=photo_url(user),
        pinfl=user.pinfl,
        phone=user.phone,
        email=user.email,
        roles=[r.code for r in (user.roles or [])],
        student_number=user.student_profile.student_number if user.student_profile else None,
        employee_number=user.staff_profile.employee_number if user.staff_profile else None,
        passport=passport,
        is_active=user.is_active,
        status=user.status or "active",
        has_face=any(f.is_active and f.archived_at is None for f in (user.face_biometrics or [])),
        faculty_name=fac,
        department_name=dept,
        group_name=grp,
    )


async def write_audit(
    db: AsyncSession,
    admin_id: str | None,
    action: str,
    entity_type: str,
    entity_id: str | None = None,
    details: dict | None = None,
) -> None:
    db.add(
        AdminAuditLog(
            admin_id=admin_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            details=details,
        )
    )


def filter_user_fields(user: User, allowed_fields: list) -> dict:
    out = user_to_out(user).model_dump(mode="json")
    if not allowed_fields:
        return out
    allowed = set(allowed_fields) | {"id"}
    return {k: v for k, v in out.items() if k in allowed}
