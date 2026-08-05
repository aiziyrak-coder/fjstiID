"""
FJSTI ID — ideal ma'lumotlar modeli

users              → autentifikatsiya + shaxs (F.I.Sh, tug'ilish, rasm)
identity_documents → pasport / ID karta (1:1)
addresses          → yashash manzili (1:1)
emergency_contacts → favqulodda aloqa (1:1)
student_profiles   → talaba o'quv kartochkasi
staff_profiles     → xodim ish kartochkasi
faculties / study_groups / departments / specialties → tashkilot
roles / user_roles → ko'p-ko'pga rollar
face_biometrics, consents, client_apps, logs, oauth, webhooks
"""

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def new_id() -> str:
    return str(uuid4())


class Role(Base):
    __tablename__ = "roles"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=new_id)
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)  # student|staff|admin|moderator
    name_uz: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(String(255))

    users: Mapped[list["User"]] = relationship(
        "User", secondary="user_roles", back_populates="roles", lazy="selectin"
    )


class UserRole(Base):
    __tablename__ = "user_roles"
    __table_args__ = (UniqueConstraint("user_id", "role_id", name="uq_user_role"),)

    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    role_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True
    )


class Faculty(Base):
    __tablename__ = "faculties"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=new_id)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    code: Mapped[str | None] = mapped_column(String(50), unique=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    departments: Mapped[list["Department"]] = relationship(back_populates="faculty", lazy="selectin")
    specialties: Mapped[list["Specialty"]] = relationship(back_populates="faculty", lazy="selectin")


class Specialty(Base):
    """Yo'nalish / mutaxassislik (ixtiyoriy)."""

    __tablename__ = "specialties"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=new_id)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    code: Mapped[str | None] = mapped_column(String(50), unique=True)
    faculty_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False), ForeignKey("faculties.id", ondelete="SET NULL")
    )

    faculty: Mapped[Faculty | None] = relationship(back_populates="specialties")


class Department(Base):
    """Kafedra / bo'lim — fakultetga birikadi. Xodimlar shu yerda."""

    __tablename__ = "departments"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=new_id)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    code: Mapped[str | None] = mapped_column(String(50), unique=True)
    faculty_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False), ForeignKey("faculties.id", ondelete="SET NULL"), index=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    faculty: Mapped[Faculty | None] = relationship(back_populates="departments", lazy="selectin")
    groups: Mapped[list["StudyGroup"]] = relationship(back_populates="department", lazy="selectin")


class StudyGroup(Base):
    """Guruh — kafedraga birikadi. Talabalar guruhga birikadi. Kurs saqlanmaydi (har yili o'zgaradi)."""

    __tablename__ = "study_groups"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=new_id)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    department_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False), ForeignKey("departments.id", ondelete="SET NULL"), index=True
    )
    specialty_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False), ForeignKey("specialties.id", ondelete="SET NULL")
    )
    academic_year: Mapped[str | None] = mapped_column(String(20))  # 2025/2026

    department: Mapped[Department | None] = relationship(back_populates="groups", lazy="selectin")


class User(Base):
    """Markaziy shaxs + tizim hisobi."""

    __tablename__ = "users"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=new_id)

    # F.I.Sh
    last_name: Mapped[str] = mapped_column(String(120), nullable=False)
    first_name: Mapped[str] = mapped_column(String(120), nullable=False)
    middle_name: Mapped[str | None] = mapped_column(String(120))
    full_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)

    gender: Mapped[str | None] = mapped_column(String(20))  # male|female
    birth_date: Mapped[Date | None] = mapped_column(Date)
    birth_place: Mapped[str | None] = mapped_column(String(255))
    nationality: Mapped[str | None] = mapped_column(String(100))
    citizenship: Mapped[str | None] = mapped_column(String(100))
    marital_status: Mapped[str | None] = mapped_column(String(50))
    blood_type: Mapped[str | None] = mapped_column(String(10))

    # JSHSHIR — asosiy unikal identifikator (shaxs)
    pinfl: Mapped[str | None] = mapped_column(String(14), unique=True, index=True)

    photo_path: Mapped[str | None] = mapped_column(String(512))
    notes: Mapped[str | None] = mapped_column(Text)

    # Auth
    email: Mapped[str | None] = mapped_column(String(255), unique=True, index=True)
    phone: Mapped[str | None] = mapped_column(String(32), index=True)
    phone_additional: Mapped[str | None] = mapped_column(String(32))
    password_hash: Mapped[str | None] = mapped_column(String(255))
    qr_token: Mapped[str | None] = mapped_column(String(64), unique=True)

    status: Mapped[str] = mapped_column(String(30), default="active")  # active|inactive|archived
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False)
    editable_fields: Mapped[list[Any]] = mapped_column(
        JSONB,
        default=lambda: [
            "phone",
            "phone_additional",
            "email",
            "emergency_contact",
        ],
    )

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    roles: Mapped[list[Role]] = relationship(
        "Role", secondary="user_roles", back_populates="users", lazy="selectin"
    )
    document: Mapped["IdentityDocument | None"] = relationship(
        back_populates="user", uselist=False, lazy="selectin", cascade="all, delete-orphan"
    )
    address: Mapped["Address | None"] = relationship(
        back_populates="user", uselist=False, lazy="selectin", cascade="all, delete-orphan"
    )
    emergency_contact: Mapped["EmergencyContact | None"] = relationship(
        back_populates="user", uselist=False, lazy="selectin", cascade="all, delete-orphan"
    )
    student_profile: Mapped["StudentProfile | None"] = relationship(
        back_populates="user", uselist=False, lazy="selectin", cascade="all, delete-orphan"
    )
    staff_profile: Mapped["StaffProfile | None"] = relationship(
        back_populates="user", uselist=False, lazy="selectin", cascade="all, delete-orphan"
    )
    face_biometrics: Mapped[list["FaceBiometric"]] = relationship(
        back_populates="user", lazy="selectin"
    )
    consents: Mapped[list["Consent"]] = relationship(back_populates="user", lazy="selectin")


class IdentityDocument(Base):
    """Pasport yoki ID-karta."""

    __tablename__ = "identity_documents"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"), unique=True
    )
    doc_type: Mapped[str] = mapped_column(String(30), default="passport")  # passport|id_card
    series: Mapped[str | None] = mapped_column(String(10))
    number: Mapped[str | None] = mapped_column(String(20), index=True)
    issued_by: Mapped[str | None] = mapped_column(String(255))
    issued_at: Mapped[Date | None] = mapped_column(Date)
    expires_at: Mapped[Date | None] = mapped_column(Date)

    user: Mapped[User] = relationship(back_populates="document")


class Address(Base):
    __tablename__ = "addresses"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"), unique=True
    )
    region: Mapped[str | None] = mapped_column(String(120))
    district: Mapped[str | None] = mapped_column(String(120))
    mahalla: Mapped[str | None] = mapped_column(String(120))
    street: Mapped[str | None] = mapped_column(String(255))
    house: Mapped[str | None] = mapped_column(String(50))
    apartment: Mapped[str | None] = mapped_column(String(50))
    full_text: Mapped[str | None] = mapped_column(Text)

    user: Mapped[User] = relationship(back_populates="address")


class EmergencyContact(Base):
    __tablename__ = "emergency_contacts"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"), unique=True
    )
    full_name: Mapped[str | None] = mapped_column(String(255))
    relation: Mapped[str | None] = mapped_column(String(100))  # ota, ona, turmush o'rtog'i...
    phone: Mapped[str | None] = mapped_column(String(32))

    user: Mapped[User] = relationship(back_populates="emergency_contact")


class StudentProfile(Base):
    __tablename__ = "student_profiles"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"), unique=True
    )
    student_number: Mapped[str] = mapped_column(String(50), unique=True, index=True)  # Talaba ID
    faculty_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False), ForeignKey("faculties.id", ondelete="SET NULL")
    )
    specialty_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False), ForeignKey("specialties.id", ondelete="SET NULL")
    )
    group_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False), ForeignKey("study_groups.id", ondelete="SET NULL")
    )
    course: Mapped[int | None] = mapped_column(Integer)
    study_form: Mapped[str | None] = mapped_column(String(50))  # kunduzgi|sirtqi|kechki
    funding: Mapped[str | None] = mapped_column(String(50))  # grant|kontrakt
    education_level: Mapped[str | None] = mapped_column(String(50))  # bakalavr|magistr|ordinatura
    admission_year: Mapped[int | None] = mapped_column(Integer)
    graduation_year: Mapped[int | None] = mapped_column(Integer)
    previous_education: Mapped[str | None] = mapped_column(String(255))
    dormitory: Mapped[str | None] = mapped_column(String(100))
    parent_full_name: Mapped[str | None] = mapped_column(String(255))
    parent_phone: Mapped[str | None] = mapped_column(String(32))
    scholarship: Mapped[str | None] = mapped_column(String(100))
    academic_status: Mapped[str] = mapped_column(String(50), default="active")

    user: Mapped[User] = relationship(back_populates="student_profile")
    faculty: Mapped[Faculty | None] = relationship(lazy="selectin")
    specialty: Mapped[Specialty | None] = relationship(lazy="selectin")
    group: Mapped[StudyGroup | None] = relationship(lazy="selectin")


class StaffProfile(Base):
    __tablename__ = "staff_profiles"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"), unique=True
    )
    employee_number: Mapped[str] = mapped_column(String(50), unique=True, index=True)  # Xodim ID
    department_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False), ForeignKey("departments.id", ondelete="SET NULL")
    )
    position: Mapped[str | None] = mapped_column(String(255))
    employment_type: Mapped[str | None] = mapped_column(String(50))
    hire_date: Mapped[Date | None] = mapped_column(Date)
    contract_number: Mapped[str | None] = mapped_column(String(100))
    work_experience_years: Mapped[float | None] = mapped_column(Float)
    schedule: Mapped[str | None] = mapped_column(Text)
    academic_degree: Mapped[str | None] = mapped_column(String(100))
    academic_title: Mapped[str | None] = mapped_column(String(100))
    education: Mapped[str | None] = mapped_column(String(255))
    specialty: Mapped[str | None] = mapped_column(String(255))
    work_phone: Mapped[str | None] = mapped_column(String(32))
    cabinet: Mapped[str | None] = mapped_column(String(50))
    staff_status: Mapped[str] = mapped_column(String(50), default="active")

    user: Mapped[User] = relationship(back_populates="staff_profile")
    department: Mapped[Department | None] = relationship(lazy="selectin")


class FaceBiometric(Base):
    __tablename__ = "face_biometrics"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    embedding: Mapped[Any] = mapped_column(Vector(512), nullable=False)
    embedding_encrypted: Mapped[str | None] = mapped_column(Text)
    version: Mapped[int] = mapped_column(Integer, default=1)
    enrolled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    user: Mapped[User] = relationship(back_populates="face_biometrics")


class ClientApp(Base):
    __tablename__ = "client_apps"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=new_id)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    client_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    client_secret_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    api_key_hash: Mapped[str | None] = mapped_column(String(255))
    allowed_scopes: Mapped[list[Any]] = mapped_column(
        JSONB, default=lambda: ["openid", "profile", "roles", "face.verify"]
    )
    allowed_fields: Mapped[list[Any]] = mapped_column(
        JSONB,
        default=lambda: ["id", "full_name", "roles", "email", "student", "staff"],
    )
    redirect_uris: Mapped[list[Any]] = mapped_column(JSONB, default=list)
    webhook_url: Mapped[str | None] = mapped_column(String(512))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AccessLog(Base):
    __tablename__ = "access_logs"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=new_id)
    user_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False), ForeignKey("users.id", ondelete="SET NULL")
    )
    client_app_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False), ForeignKey("client_apps.id", ondelete="SET NULL")
    )
    method: Mapped[str] = mapped_column(String(50), default="face")
    success: Mapped[bool] = mapped_column(Boolean, default=False)
    device_info: Mapped[str | None] = mapped_column(String(255))
    location: Mapped[str | None] = mapped_column(String(255))
    detail: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AdminAuditLog(Base):
    __tablename__ = "admin_audit_logs"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=new_id)
    admin_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False), ForeignKey("users.id", ondelete="SET NULL")
    )
    action: Mapped[str] = mapped_column(String(50), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(100), nullable=False)
    entity_id: Mapped[str | None] = mapped_column(String(64))
    details: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Consent(Base):
    __tablename__ = "consents"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE")
    )
    consent_type: Mapped[str] = mapped_column(String(50), default="biometric")
    granted: Mapped[bool] = mapped_column(Boolean, default=True)
    granted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    document_ref: Mapped[str | None] = mapped_column(String(255))

    user: Mapped[User] = relationship(back_populates="consents")


class FaceUpdateRequest(Base):
    __tablename__ = "face_update_requests"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE")
    )
    status: Mapped[str] = mapped_column(String(30), default="pending")
    note: Mapped[str | None] = mapped_column(Text)
    reviewed_by: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False), ForeignKey("users.id", ondelete="SET NULL")
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class OAuthAuthorizationCode(Base):
    __tablename__ = "oauth_authorization_codes"

    code: Mapped[str] = mapped_column(String(128), primary_key=True)
    client_id: Mapped[str] = mapped_column(String(64), nullable=False)
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE")
    )
    redirect_uri: Mapped[str] = mapped_column(String(512), nullable=False)
    scope: Mapped[str] = mapped_column(String(512), default="openid profile")
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used: Mapped[bool] = mapped_column(Boolean, default=False)


class WebhookDelivery(Base):
    __tablename__ = "webhook_deliveries"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=new_id)
    client_app_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("client_apps.id", ondelete="CASCADE")
    )
    event: Mapped[str] = mapped_column(String(100), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    success: Mapped[bool] = mapped_column(Boolean, default=False)
    response_code: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AcademicYear(Base):
    """O'quv yili — guruhlar academic_year satri bilan bog'lanadi."""

    __tablename__ = "academic_years"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=new_id)
    name: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)  # 2025/2026
    is_current: Mapped[bool] = mapped_column(Boolean, default=False)
    starts_on: Mapped[Date | None] = mapped_column(Date)
    ends_on: Mapped[Date | None] = mapped_column(Date)


class SystemSetting(Base):
    """Admin panel orqali o'zgartiriladigan sozlamalar."""

    __tablename__ = "system_settings"

    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    label: Mapped[str | None] = mapped_column(String(255))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
