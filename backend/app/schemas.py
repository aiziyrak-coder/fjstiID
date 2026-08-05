from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator


class RoleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    code: str
    name_uz: str
    name: str = ""  # = code (frontend uchun)
    description: str | None = None

    @model_validator(mode="after")
    def fill_name(self):
        if not self.name:
            self.name = self.code
        return self


class DocumentIn(BaseModel):
    doc_type: str = "passport"
    series: str | None = None
    number: str | None = None
    issued_by: str | None = None
    issued_at: date | None = None
    expires_at: date | None = None


class DocumentOut(DocumentIn):
    model_config = ConfigDict(from_attributes=True)
    id: str


class AddressIn(BaseModel):
    region: str | None = None
    district: str | None = None
    mahalla: str | None = None
    street: str | None = None
    house: str | None = None
    apartment: str | None = None
    full_text: str | None = None


class AddressOut(AddressIn):
    model_config = ConfigDict(from_attributes=True)
    id: str


class EmergencyIn(BaseModel):
    full_name: str | None = None
    relation: str | None = None
    phone: str | None = None


class EmergencyOut(EmergencyIn):
    model_config = ConfigDict(from_attributes=True)
    id: str


class StudentIn(BaseModel):
    student_number: str
    faculty_id: str | None = None
    specialty_id: str | None = None
    group_id: str | None = None
    course: int | None = None
    study_form: str | None = None
    funding: str | None = None
    education_level: str | None = None
    admission_year: int | None = None
    graduation_year: int | None = None
    previous_education: str | None = None
    dormitory: str | None = None
    parent_full_name: str | None = None
    parent_phone: str | None = None
    scholarship: str | None = None
    academic_status: str = "active"


class StudentOut(StudentIn):
    model_config = ConfigDict(from_attributes=True)
    id: str
    user_id: str
    faculty_name: str | None = None
    specialty_name: str | None = None
    group_name: str | None = None
    department_id: str | None = None
    department_name: str | None = None


class StaffIn(BaseModel):
    employee_number: str
    department_id: str | None = None
    position: str | None = None
    employment_type: str | None = None
    hire_date: date | None = None
    contract_number: str | None = None
    work_experience_years: float | None = None
    schedule: str | None = None
    academic_degree: str | None = None
    academic_title: str | None = None
    education: str | None = None
    specialty: str | None = None
    work_phone: str | None = None
    cabinet: str | None = None
    staff_status: str = "active"


class StaffOut(StaffIn):
    model_config = ConfigDict(from_attributes=True)
    id: str
    user_id: str
    department_name: str | None = None


class PersonIn(BaseModel):
    last_name: str
    first_name: str
    middle_name: str | None = None
    gender: Literal["male", "female"] | None = None
    birth_date: date | None = None
    birth_place: str | None = None
    nationality: str | None = None
    citizenship: str | None = None
    marital_status: str | None = None
    blood_type: str | None = None
    pinfl: str | None = None
    notes: str | None = None

    @field_validator("pinfl")
    @classmethod
    def pinfl_len(cls, v: str | None) -> str | None:
        if v is None or v == "":
            return None
        v = v.strip()
        if len(v) != 14 or not v.isdigit():
            raise ValueError("JSHSHIR 14 ta raqam bo'lishi kerak")
        return v


class ContactsIn(BaseModel):
    phone: str | None = None
    phone_additional: str | None = None
    email: EmailStr | None = None


class UserCreate(BaseModel):
    person: PersonIn
    contacts: ContactsIn = Field(default_factory=ContactsIn)
    document: DocumentIn | None = None
    address: AddressIn | None = None
    emergency: EmergencyIn | None = None
    student: StudentIn | None = None
    staff: StaffIn | None = None
    role_codes: list[str] = Field(default_factory=list)
    password: str | None = None
    grant_biometric_consent: bool = False

    @model_validator(mode="after")
    def roles_need_profiles(self):
        codes = set(self.role_codes)
        if "student" in codes and not self.student:
            raise ValueError("Talaba roli uchun student (talaba ID) majburiy")
        if "staff" in codes and not self.staff:
            raise ValueError("Xodim roli uchun staff (xodim ID) majburiy")
        return self


class UserUpdate(BaseModel):
    person: PersonIn | None = None
    contacts: ContactsIn | None = None
    document: DocumentIn | None = None
    address: AddressIn | None = None
    emergency: EmergencyIn | None = None
    student: StudentIn | None = None
    staff: StaffIn | None = None
    role_codes: list[str] | None = None
    password: str | None = None
    is_active: bool | None = None
    status: str | None = None


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    last_name: str
    first_name: str
    middle_name: str | None = None
    full_name: str
    gender: str | None = None
    birth_date: date | None = None
    birth_place: str | None = None
    nationality: str | None = None
    citizenship: str | None = None
    marital_status: str | None = None
    blood_type: str | None = None
    pinfl: str | None = None
    notes: str | None = None
    phone: str | None = None
    phone_additional: str | None = None
    email: str | None = None
    photo_url: str | None = None
    status: str = "active"
    is_active: bool
    qr_token: str | None = None
    roles: list[RoleOut] = []
    document: DocumentOut | None = None
    address: AddressOut | None = None
    emergency: EmergencyOut | None = None
    student: StudentOut | None = None
    staff: StaffOut | None = None
    created_at: datetime | None = None
    has_face: bool = False
    has_biometric_consent: bool = False

    # legacy aliases for UI convenience
    @property
    def student_profile(self):
        return self.student

    @property
    def staff_profile(self):
        return self.staff


class UserListItem(BaseModel):
    id: str
    full_name: str
    photo_url: str | None = None
    pinfl: str | None = None
    phone: str | None = None
    email: str | None = None
    roles: list[str] = []
    student_number: str | None = None
    employee_number: str | None = None
    passport: str | None = None
    is_active: bool
    status: str = "active"
    has_face: bool = False
    faculty_name: str | None = None
    department_name: str | None = None
    group_name: str | None = None


class PageUsers(BaseModel):
    items: list[UserListItem]
    total: int
    page: int
    page_size: int
    pages: int


class BulkActionIn(BaseModel):
    user_ids: list[str]
    action: Literal["activate", "deactivate", "archive", "set_status", "add_role", "remove_role"]
    status: str | None = None
    role_code: str | None = None


class BulkActionOut(BaseModel):
    updated: int
    message: str


class AcademicYearIn(BaseModel):
    name: str
    is_current: bool = False
    starts_on: date | None = None
    ends_on: date | None = None


class AcademicYearOut(AcademicYearIn):
    model_config = ConfigDict(from_attributes=True)
    id: str


class SettingOut(BaseModel):
    key: str
    value: str
    label: str | None = None


class SettingsPatch(BaseModel):
    items: list[SettingOut]


class ImportResult(BaseModel):
    created: int
    skipped: int
    errors: list[str] = []


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class FacultyIn(BaseModel):
    name: str
    code: str | None = None


class FacultyOut(FacultyIn):
    model_config = ConfigDict(from_attributes=True)
    id: str
    departments_count: int = 0


class SpecialtyIn(BaseModel):
    name: str
    code: str | None = None
    faculty_id: str | None = None


class SpecialtyOut(SpecialtyIn):
    model_config = ConfigDict(from_attributes=True)
    id: str
    faculty_name: str | None = None


class FacultyBreakdown(BaseModel):
    faculty_id: str
    faculty_name: str
    students: int
    staff: int
    groups: int
    departments: int


class StatusBreakdown(BaseModel):
    status: str
    count: int


class GroupIn(BaseModel):
    name: str
    department_id: str | None = None
    specialty_id: str | None = None
    academic_year: str | None = None


class GroupOut(GroupIn):
    model_config = ConfigDict(from_attributes=True)
    id: str
    department_name: str | None = None
    faculty_id: str | None = None
    faculty_name: str | None = None
    students_count: int = 0


class DepartmentIn(BaseModel):
    name: str
    code: str | None = None
    faculty_id: str | None = None


class DepartmentOut(DepartmentIn):
    model_config = ConfigDict(from_attributes=True)
    id: str
    faculty_name: str | None = None
    groups_count: int = 0
    staff_count: int = 0


class ClientAppCreate(BaseModel):
    name: str
    allowed_scopes: list[str] = Field(default_factory=lambda: ["openid", "profile", "roles", "face.verify"])
    allowed_fields: list[str] = Field(
        default_factory=lambda: ["id", "full_name", "roles", "email", "student", "staff"]
    )
    redirect_uris: list[str] = Field(default_factory=list)
    webhook_url: str | None = None


class ClientAppOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    name: str
    client_id: str
    allowed_scopes: list[Any]
    allowed_fields: list[Any]
    redirect_uris: list[Any]
    webhook_url: str | None = None
    is_active: bool
    created_at: datetime | None = None


class ClientAppCreated(ClientAppOut):
    client_secret: str
    api_key: str


class FaceVerifyResponse(BaseModel):
    matched: bool
    confidence: float | None = None
    user: UserOut | None = None
    access_token: str | None = None


class ProfilePatch(BaseModel):
    phone: str | None = None
    phone_additional: str | None = None
    email: EmailStr | None = None
    emergency: EmergencyIn | None = None
    address_full: str | None = None  # maps to address.full_text


class StatsOut(BaseModel):
    total_users: int
    students_only: int
    staff_only: int
    student_and_staff: int
    students_total: int
    staff_total: int
    active_users: int
    inactive_users: int
    face_enrolled: int
    face_pending_requests: int
    no_face_students: int
    faculties: int
    departments: int
    groups: int
    specialties: int
    client_apps: int
    access_today: int
    access_today_fail: int
    access_total: int
    access_face: int
    access_password: int
    access_qr: int
    access_last_7_days: list[dict]
    access_last_30_days: list[dict]
    audit_total: int
    by_faculty: list[FacultyBreakdown] = []
    by_status: list[StatusBreakdown] = []
    current_academic_year: str | None = None


class AccessLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    user_id: str | None
    user_name: str | None = None
    client_app_id: str | None
    method: str
    success: bool
    device_info: str | None
    location: str | None
    detail: str | None
    created_at: datetime | None


class AuditLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    admin_id: str | None
    admin_name: str | None = None
    action: str
    entity_type: str
    entity_id: str | None
    details: dict[str, Any] | None
    created_at: datetime | None


class PageLogs(BaseModel):
    items: list[Any]
    total: int
    page: int
    page_size: int


class FaceUpdateRequestOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    user_id: str
    user_name: str | None = None
    status: str
    note: str | None = None
    created_at: datetime | None = None
    reviewed_at: datetime | None = None


class MessageOut(BaseModel):
    message: str
