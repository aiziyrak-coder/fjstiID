"""Ideal normalized schema

Revision ID: 001_ideal
Revises:
Create Date: 2026-08-04
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

revision: str = "001_ideal"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "roles",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("code", sa.String(50), unique=True, nullable=False),
        sa.Column("name_uz", sa.String(100), nullable=False),
        sa.Column("description", sa.String(255)),
    )
    op.create_table(
        "faculties",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("code", sa.String(50), unique=True),
        sa.Column("is_active", sa.Boolean(), server_default="true"),
    )
    op.create_table(
        "specialties",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("code", sa.String(50), unique=True),
        sa.Column("faculty_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("faculties.id", ondelete="SET NULL")),
    )
    op.create_table(
        "departments",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("code", sa.String(50), unique=True),
        sa.Column("faculty_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("faculties.id", ondelete="SET NULL")),
        sa.Column("is_active", sa.Boolean(), server_default="true"),
    )
    op.create_table(
        "study_groups",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("department_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("departments.id", ondelete="SET NULL")),
        sa.Column("specialty_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("specialties.id", ondelete="SET NULL")),
        sa.Column("academic_year", sa.String(20)),
    )
    op.create_index("ix_study_groups_department_id", "study_groups", ["department_id"])
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("last_name", sa.String(120), nullable=False),
        sa.Column("first_name", sa.String(120), nullable=False),
        sa.Column("middle_name", sa.String(120)),
        sa.Column("full_name", sa.String(255), nullable=False),
        sa.Column("gender", sa.String(20)),
        sa.Column("birth_date", sa.Date()),
        sa.Column("birth_place", sa.String(255)),
        sa.Column("nationality", sa.String(100)),
        sa.Column("citizenship", sa.String(100)),
        sa.Column("marital_status", sa.String(50)),
        sa.Column("blood_type", sa.String(10)),
        sa.Column("pinfl", sa.String(14), unique=True),
        sa.Column("photo_path", sa.String(512)),
        sa.Column("notes", sa.Text()),
        sa.Column("email", sa.String(255), unique=True),
        sa.Column("phone", sa.String(32)),
        sa.Column("phone_additional", sa.String(32)),
        sa.Column("password_hash", sa.String(255)),
        sa.Column("qr_token", sa.String(64), unique=True),
        sa.Column("status", sa.String(30), server_default="active"),
        sa.Column("is_active", sa.Boolean(), server_default="true"),
        sa.Column("is_deleted", sa.Boolean(), server_default="false"),
        sa.Column(
            "editable_fields",
            postgresql.JSONB(),
            server_default='["phone","phone_additional","email","emergency_contact"]',
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_users_full_name", "users", ["full_name"])
    op.create_index("ix_users_pinfl", "users", ["pinfl"])
    op.create_index("ix_users_email", "users", ["email"])
    op.create_index("ix_users_phone", "users", ["phone"])

    op.create_table(
        "user_roles",
        sa.Column("user_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("role_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
        sa.UniqueConstraint("user_id", "role_id", name="uq_user_role"),
    )
    op.create_table(
        "identity_documents",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("users.id", ondelete="CASCADE"), unique=True),
        sa.Column("doc_type", sa.String(30), server_default="passport"),
        sa.Column("series", sa.String(10)),
        sa.Column("number", sa.String(20)),
        sa.Column("issued_by", sa.String(255)),
        sa.Column("issued_at", sa.Date()),
        sa.Column("expires_at", sa.Date()),
    )
    op.create_index("ix_identity_documents_number", "identity_documents", ["number"])

    op.create_table(
        "addresses",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("users.id", ondelete="CASCADE"), unique=True),
        sa.Column("region", sa.String(120)),
        sa.Column("district", sa.String(120)),
        sa.Column("mahalla", sa.String(120)),
        sa.Column("street", sa.String(255)),
        sa.Column("house", sa.String(50)),
        sa.Column("apartment", sa.String(50)),
        sa.Column("full_text", sa.Text()),
    )
    op.create_table(
        "emergency_contacts",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("users.id", ondelete="CASCADE"), unique=True),
        sa.Column("full_name", sa.String(255)),
        sa.Column("relation", sa.String(100)),
        sa.Column("phone", sa.String(32)),
    )
    op.create_table(
        "student_profiles",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("users.id", ondelete="CASCADE"), unique=True),
        sa.Column("student_number", sa.String(50), nullable=False, unique=True),
        sa.Column("faculty_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("faculties.id", ondelete="SET NULL")),
        sa.Column("specialty_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("specialties.id", ondelete="SET NULL")),
        sa.Column("group_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("study_groups.id", ondelete="SET NULL")),
        sa.Column("course", sa.Integer()),
        sa.Column("study_form", sa.String(50)),
        sa.Column("funding", sa.String(50)),
        sa.Column("education_level", sa.String(50)),
        sa.Column("admission_year", sa.Integer()),
        sa.Column("graduation_year", sa.Integer()),
        sa.Column("previous_education", sa.String(255)),
        sa.Column("dormitory", sa.String(100)),
        sa.Column("parent_full_name", sa.String(255)),
        sa.Column("parent_phone", sa.String(32)),
        sa.Column("scholarship", sa.String(100)),
        sa.Column("academic_status", sa.String(50), server_default="active"),
    )
    op.create_index("ix_student_profiles_student_number", "student_profiles", ["student_number"], unique=True)

    op.create_table(
        "staff_profiles",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("users.id", ondelete="CASCADE"), unique=True),
        sa.Column("employee_number", sa.String(50), nullable=False, unique=True),
        sa.Column("department_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("departments.id", ondelete="SET NULL")),
        sa.Column("position", sa.String(255)),
        sa.Column("employment_type", sa.String(50)),
        sa.Column("hire_date", sa.Date()),
        sa.Column("contract_number", sa.String(100)),
        sa.Column("work_experience_years", sa.Float()),
        sa.Column("schedule", sa.Text()),
        sa.Column("academic_degree", sa.String(100)),
        sa.Column("academic_title", sa.String(100)),
        sa.Column("education", sa.String(255)),
        sa.Column("specialty", sa.String(255)),
        sa.Column("work_phone", sa.String(32)),
        sa.Column("cabinet", sa.String(50)),
        sa.Column("staff_status", sa.String(50), server_default="active"),
    )
    op.create_index("ix_staff_profiles_employee_number", "staff_profiles", ["employee_number"], unique=True)

    op.create_table(
        "face_biometrics",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("users.id", ondelete="CASCADE")),
        sa.Column("embedding", Vector(512), nullable=False),
        sa.Column("embedding_encrypted", sa.Text()),
        sa.Column("version", sa.Integer(), server_default="1"),
        sa.Column("enrolled_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("is_active", sa.Boolean(), server_default="true"),
        sa.Column("archived_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_face_biometrics_user_id", "face_biometrics", ["user_id"])

    op.create_table(
        "client_apps",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("client_id", sa.String(64), unique=True, nullable=False),
        sa.Column("client_secret_hash", sa.String(255), nullable=False),
        sa.Column("api_key_hash", sa.String(255)),
        sa.Column("allowed_scopes", postgresql.JSONB(), server_default='["openid","profile","roles","face.verify"]'),
        sa.Column("allowed_fields", postgresql.JSONB(), server_default='["id","full_name","roles","email","student","staff"]'),
        sa.Column("redirect_uris", postgresql.JSONB(), server_default="[]"),
        sa.Column("webhook_url", sa.String(512)),
        sa.Column("is_active", sa.Boolean(), server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_table(
        "access_logs",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("client_app_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("client_apps.id", ondelete="SET NULL")),
        sa.Column("method", sa.String(50), server_default="face"),
        sa.Column("success", sa.Boolean(), server_default="false"),
        sa.Column("device_info", sa.String(255)),
        sa.Column("location", sa.String(255)),
        sa.Column("detail", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_table(
        "admin_audit_logs",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("admin_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("action", sa.String(50), nullable=False),
        sa.Column("entity_type", sa.String(100), nullable=False),
        sa.Column("entity_id", sa.String(64)),
        sa.Column("details", postgresql.JSONB()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_table(
        "consents",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("users.id", ondelete="CASCADE")),
        sa.Column("consent_type", sa.String(50), server_default="biometric"),
        sa.Column("granted", sa.Boolean(), server_default="true"),
        sa.Column("granted_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("revoked_at", sa.DateTime(timezone=True)),
        sa.Column("document_ref", sa.String(255)),
    )
    op.create_table(
        "face_update_requests",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("users.id", ondelete="CASCADE")),
        sa.Column("status", sa.String(30), server_default="pending"),
        sa.Column("note", sa.Text()),
        sa.Column("reviewed_by", postgresql.UUID(as_uuid=False), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("reviewed_at", sa.DateTime(timezone=True)),
    )
    op.create_table(
        "oauth_authorization_codes",
        sa.Column("code", sa.String(128), primary_key=True),
        sa.Column("client_id", sa.String(64), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("users.id", ondelete="CASCADE")),
        sa.Column("redirect_uri", sa.String(512), nullable=False),
        sa.Column("scope", sa.String(512), server_default="openid profile"),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used", sa.Boolean(), server_default="false"),
    )
    op.create_table(
        "webhook_deliveries",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("client_app_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("client_apps.id", ondelete="CASCADE")),
        sa.Column("event", sa.String(100), nullable=False),
        sa.Column("payload", postgresql.JSONB(), nullable=False),
        sa.Column("success", sa.Boolean(), server_default="false"),
        sa.Column("response_code", sa.Integer()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_table(
        "academic_years",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("name", sa.String(20), unique=True, nullable=False),
        sa.Column("is_current", sa.Boolean(), server_default="false"),
        sa.Column("starts_on", sa.Date()),
        sa.Column("ends_on", sa.Date()),
    )
    op.create_table(
        "system_settings",
        sa.Column("key", sa.String(100), primary_key=True),
        sa.Column("value", sa.Text(), nullable=False),
        sa.Column("label", sa.String(255)),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )


def downgrade() -> None:
    for t in [
        "system_settings",
        "academic_years",
        "webhook_deliveries",
        "oauth_authorization_codes",
        "face_update_requests",
        "consents",
        "admin_audit_logs",
        "access_logs",
        "client_apps",
        "face_biometrics",
        "staff_profiles",
        "student_profiles",
        "emergency_contacts",
        "addresses",
        "identity_documents",
        "user_roles",
        "users",
        "study_groups",
        "departments",
        "specialties",
        "faculties",
        "roles",
    ]:
        op.drop_table(t)
