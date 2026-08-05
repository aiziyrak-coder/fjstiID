from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Form, HTTPException, Query

from fastapi.responses import HTMLResponse, RedirectResponse

from sqlalchemy import func, select

from sqlalchemy.ext.asyncio import AsyncSession

from sqlalchemy.orm import selectinload

from app.config import get_settings

from app.database import get_db

from app.deps import get_current_user, require_client_app, require_roles

from app.models import (

    AccessLog,

    AcademicYear,

    AdminAuditLog,

    ClientApp,

    Department,

    FaceBiometric,

    FaceUpdateRequest,

    Faculty,

    OAuthAuthorizationCode,

    Role,

    Specialty,

    StaffProfile,

    StudentProfile,

    StudyGroup,

    User,

    UserRole,

)

from app.schemas import (

    AccessLogOut,

    AuditLogOut,

    FacultyBreakdown,

    PageLogs,

    StatsOut,

    StatusBreakdown,

)

from app.security import create_access_token, generate_token, verify_password, verify_secret

from app.services.users import filter_user_fields

router = APIRouter(tags=["oauth-stats"])

settings = get_settings()

@router.get("/api/v1/admin/stats", response_model=StatsOut)

async def stats(_: User = Depends(require_roles("admin", "moderator")), db: AsyncSession = Depends(get_db)):

    total = await db.scalar(select(func.count()).select_from(User).where(User.is_deleted.is_(False))) or 0

    active = await db.scalar(

        select(func.count()).select_from(User).where(User.is_deleted.is_(False), User.is_active.is_(True))

    ) or 0

    inactive = await db.scalar(

        select(func.count()).select_from(User).where(User.is_deleted.is_(False), User.is_active.is_(False))

    ) or 0

    student_role = await db.scalar(select(Role.id).where(Role.code == "student"))

    staff_role = await db.scalar(select(Role.id).where(Role.code == "staff"))

    student_ids = set()

    staff_ids = set()

    if student_role:

        student_ids = set(

            (await db.execute(select(UserRole.user_id).where(UserRole.role_id == student_role))).scalars().all()

        )

    if staff_role:

        staff_ids = set(

            (await db.execute(select(UserRole.user_id).where(UserRole.role_id == staff_role))).scalars().all()

        )

    both = student_ids & staff_ids

    students_only = student_ids - staff_ids

    staff_only = staff_ids - student_ids

    faces = await db.scalar(

        select(func.count()).select_from(FaceBiometric).where(FaceBiometric.is_active.is_(True))

    ) or 0

    face_pending = await db.scalar(

        select(func.count()).select_from(FaceUpdateRequest).where(FaceUpdateRequest.status == "pending")

    ) or 0

    # students without face

    faced_users = set(

        (await db.execute(select(FaceBiometric.user_id).where(FaceBiometric.is_active.is_(True)))).scalars().all()

    )

    no_face_students = len(student_ids - faced_users)

    clients = await db.scalar(select(func.count()).select_from(ClientApp).where(ClientApp.is_active.is_(True))) or 0

    faculties = await db.scalar(select(func.count()).select_from(Faculty)) or 0

    departments = await db.scalar(select(func.count()).select_from(Department)) or 0

    groups = await db.scalar(select(func.count()).select_from(StudyGroup)) or 0

    specialties = await db.scalar(select(func.count()).select_from(Specialty)) or 0

    today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)

    access_today = await db.scalar(

        select(func.count()).select_from(AccessLog).where(AccessLog.created_at >= today, AccessLog.success.is_(True))

    ) or 0

    access_today_fail = await db.scalar(

        select(func.count()).select_from(AccessLog).where(AccessLog.created_at >= today, AccessLog.success.is_(False))

    ) or 0

    access_total = await db.scalar(select(func.count()).select_from(AccessLog)) or 0

    access_face = await db.scalar(select(func.count()).select_from(AccessLog).where(AccessLog.method == "face")) or 0

    access_password = await db.scalar(

        select(func.count()).select_from(AccessLog).where(AccessLog.method == "password")

    ) or 0

    access_qr = await db.scalar(select(func.count()).select_from(AccessLog).where(AccessLog.method == "qr")) or 0

    audit_total = await db.scalar(select(func.count()).select_from(AdminAuditLog)) or 0

    last7 = []

    for i in range(6, -1, -1):

        day = today - timedelta(days=i)

        nxt = day + timedelta(days=1)

        ok = await db.scalar(

            select(func.count())

            .select_from(AccessLog)

            .where(AccessLog.created_at >= day, AccessLog.created_at < nxt, AccessLog.success.is_(True))

        ) or 0

        fail = await db.scalar(

            select(func.count())

            .select_from(AccessLog)

            .where(AccessLog.created_at >= day, AccessLog.created_at < nxt, AccessLog.success.is_(False))

        ) or 0

        last7.append({"date": day.date().isoformat(), "success": ok, "fail": fail})

    last30 = []

    for i in range(29, -1, -1):

        day = today - timedelta(days=i)

        nxt = day + timedelta(days=1)

        ok = await db.scalar(

            select(func.count())

            .select_from(AccessLog)

            .where(AccessLog.created_at >= day, AccessLog.created_at < nxt, AccessLog.success.is_(True))

        ) or 0

        fail = await db.scalar(

            select(func.count())

            .select_from(AccessLog)

            .where(AccessLog.created_at >= day, AccessLog.created_at < nxt, AccessLog.success.is_(False))

        ) or 0

        last30.append({"date": day.date().isoformat(), "success": ok, "fail": fail})

    by_faculty: list[FacultyBreakdown] = []

    for fac in (await db.execute(select(Faculty).order_by(Faculty.name))).scalars().all():

        stu = await db.scalar(

            select(func.count()).select_from(StudentProfile).where(StudentProfile.faculty_id == fac.id)

        ) or 0

        dept_ids = (

            await db.execute(select(Department.id).where(Department.faculty_id == fac.id))

        ).scalars().all()

        stf = 0

        if dept_ids:

            stf = await db.scalar(

                select(func.count()).select_from(StaffProfile).where(StaffProfile.department_id.in_(dept_ids))

            ) or 0

        grp = 0

        if dept_ids:

            grp = await db.scalar(

                select(func.count()).select_from(StudyGroup).where(StudyGroup.department_id.in_(dept_ids))

            ) or 0

        by_faculty.append(

            FacultyBreakdown(

                faculty_id=fac.id,

                faculty_name=fac.name,

                students=stu,

                staff=stf,

                groups=grp,

                departments=len(dept_ids),

            )

        )

    status_rows = (

        await db.execute(

            select(User.status, func.count())

            .where(User.is_deleted.is_(False))

            .group_by(User.status)

        )

    ).all()

    by_status = [StatusBreakdown(status=s or "active", count=c) for s, c in status_rows]

    cur_year = await db.scalar(select(AcademicYear.name).where(AcademicYear.is_current.is_(True)))

    return StatsOut(

        total_users=total,

        students_only=len(students_only),

        staff_only=len(staff_only),

        student_and_staff=len(both),

        students_total=len(student_ids),

        staff_total=len(staff_ids),

        active_users=active,

        inactive_users=inactive,

        face_enrolled=faces,

        face_pending_requests=face_pending,

        no_face_students=no_face_students,

        faculties=faculties,

        departments=departments,

        groups=groups,

        specialties=specialties,

        client_apps=clients,

        access_today=access_today,

        access_today_fail=access_today_fail,

        access_total=access_total,

        access_face=access_face,

        access_password=access_password,

        access_qr=access_qr,

        access_last_7_days=last7,

        access_last_30_days=last30,

        audit_total=audit_total,

        by_faculty=by_faculty,

        by_status=by_status,

        current_academic_year=cur_year,

    )

@router.get("/api/v1/admin/access-logs", response_model=PageLogs)

async def access_logs(

    method: str | None = None,

    success: bool | None = None,

    q: str | None = None,

    page: int = Query(1, ge=1),

    page_size: int = Query(50, ge=1, le=200),

    _: User = Depends(require_roles("admin")),

    db: AsyncSession = Depends(get_db),

):

    stmt = select(AccessLog).order_by(AccessLog.created_at.desc())

    if method:

        stmt = stmt.where(AccessLog.method == method)

    if success is not None:

        stmt = stmt.where(AccessLog.success.is_(success))

    rows = list((await db.execute(stmt)).scalars().all())

    items: list[AccessLogOut] = []

    for r in rows:

        name = None

        if r.user_id:

            u = await db.get(User, r.user_id)

            name = u.full_name if u else None

        if q and q.lower() not in (name or "").lower() and q.lower() not in (r.detail or "").lower():

            continue

        items.append(

            AccessLogOut(

                id=r.id,

                user_id=r.user_id,

                user_name=name,

                client_app_id=r.client_app_id,

                method=r.method,

                success=r.success,

                device_info=r.device_info,

                location=r.location,

                detail=r.detail,

                created_at=r.created_at,

            )

        )

    total = len(items)

    start = (page - 1) * page_size

    return PageLogs(items=items[start : start + page_size], total=total, page=page, page_size=page_size)

@router.get("/api/v1/admin/audit-logs", response_model=PageLogs)

async def audit_logs(

    action: str | None = None,

    entity_type: str | None = None,

    page: int = Query(1, ge=1),

    page_size: int = Query(50, ge=1, le=200),

    _: User = Depends(require_roles("admin")),

    db: AsyncSession = Depends(get_db),

):

    stmt = select(AdminAuditLog).order_by(AdminAuditLog.created_at.desc())

    if action:

        stmt = stmt.where(AdminAuditLog.action == action)

    if entity_type:

        stmt = stmt.where(AdminAuditLog.entity_type == entity_type)

    rows = list((await db.execute(stmt.limit(2000))).scalars().all())

    items: list[AuditLogOut] = []

    for r in rows:

        name = None

        if r.admin_id:

            u = await db.get(User, r.admin_id)

            name = u.full_name if u else None

        items.append(

            AuditLogOut(

                id=r.id,

                admin_id=r.admin_id,

                admin_name=name,

                action=r.action,

                entity_type=r.entity_type,

                entity_id=r.entity_id,

                details=r.details,

                created_at=r.created_at,

            )

        )

    total = len(items)

    start = (page - 1) * page_size

    return PageLogs(items=items[start : start + page_size], total=total, page=page, page_size=page_size)

@router.get("/api/v1/users/{user_id}")

async def get_user_for_client(

    user_id: str,

    client: ClientApp = Depends(require_client_app),

    db: AsyncSession = Depends(get_db),

):

    result = await db.execute(

        select(User)

        .options(

            selectinload(User.roles),

            selectinload(User.student_profile),

            selectinload(User.staff_profile),

            selectinload(User.face_biometrics),

            selectinload(User.consents),

        )

        .where(User.id == user_id, User.is_deleted.is_(False))

    )

    user = result.scalar_one_or_none()

    if not user:

        raise HTTPException(404, "Foydalanuvchi topilmadi")

    return filter_user_fields(user, client.allowed_fields or [])

# --- OAuth2 / OIDC ---

@router.get("/.well-known/openid-configuration")

async def oidc_discovery():

    issuer = settings.oidc_issuer

    return {

        "issuer": issuer,

        "authorization_endpoint": f"{issuer}/oauth/authorize",

        "token_endpoint": f"{issuer}/oauth/token",

        "userinfo_endpoint": f"{issuer}/oauth/userinfo",

        "jwks_uri": f"{issuer}/oauth/jwks",

        "response_types_supported": ["code"],

        "subject_types_supported": ["public"],

        "id_token_signing_alg_values_supported": ["HS256"],

        "scopes_supported": ["openid", "profile", "roles", "email"],

    }

@router.get("/oauth/authorize")

async def oauth_authorize(

    response_type: str,

    client_id: str,

    redirect_uri: str,

    scope: str = "openid profile",

    state: str | None = None,

    db: AsyncSession = Depends(get_db),

):

    if response_type != "code":

        raise HTTPException(400, "Faqat code qo'llab-quvvatlanadi")

    app = await db.scalar(select(ClientApp).where(ClientApp.client_id == client_id, ClientApp.is_active.is_(True)))

    if not app:

        raise HTTPException(400, "Noma'lum client")

    if redirect_uri not in (app.redirect_uris or []):

        raise HTTPException(400, "redirect_uri ruxsat etilmagan")

    html = f"""

    <!DOCTYPE html><html><head><meta charset="utf-8"><title>FJSTI ID — Kirish</title>

    <style>

      body{{font-family:Georgia,serif;background:linear-gradient(160deg,#0b3d2e,#1a5c45);min-height:100vh;display:flex;align-items:center;justify-content:center;margin:0;color:#fff}}

      form{{background:rgba(255,255,255,.08);padding:2rem;border-radius:12px;width:340px;backdrop-filter:blur(8px)}}

      h1{{font-size:1.25rem;margin:0 0 .5rem}} p{{opacity:.8;font-size:.9rem}}

      input{{width:100%;padding:.65rem;margin:.4rem 0;border:0;border-radius:6px;box-sizing:border-box}}

      button{{width:100%;padding:.75rem;margin-top:.8rem;border:0;border-radius:6px;background:#c4a35a;color:#0b3d2e;font-weight:700;cursor:pointer}}

    </style></head><body>

    <form method="post" action="/oauth/authorize">

      <h1>FJSTI ID</h1>

      <p>{app.name} dasturiga kirish</p>

      <input type="hidden" name="client_id" value="{client_id}"/>

      <input type="hidden" name="redirect_uri" value="{redirect_uri}"/>

      <input type="hidden" name="scope" value="{scope}"/>

      <input type="hidden" name="state" value="{state or ''}"/>

      <input name="email" type="email" placeholder="Email" required/>

      <input name="password" type="password" placeholder="Parol" required/>

      <button type="submit">Ruxsat berish</button>

    </form></body></html>

    """

    return HTMLResponse(html)

@router.post("/oauth/authorize")

async def oauth_authorize_post(

    client_id: str = Form(...),

    redirect_uri: str = Form(...),

    scope: str = Form("openid profile"),

    state: str = Form(""),

    email: str = Form(...),

    password: str = Form(...),

    db: AsyncSession = Depends(get_db),

):

    app = await db.scalar(select(ClientApp).where(ClientApp.client_id == client_id, ClientApp.is_active.is_(True)))

    if not app or redirect_uri not in (app.redirect_uris or []):

        raise HTTPException(400, "Client/redirect xato")

    user = await db.scalar(select(User).where(User.email == email, User.is_deleted.is_(False)))

    if not user or not verify_password(password, user.password_hash):

        raise HTTPException(401, "Login xato")

    code = generate_token(24)

    db.add(

        OAuthAuthorizationCode(

            code=code,

            client_id=client_id,

            user_id=user.id,

            redirect_uri=redirect_uri,

            scope=scope,

            expires_at=datetime.now(timezone.utc) + timedelta(minutes=10),

        )

    )

    await db.commit()

    url = f"{redirect_uri}?code={code}"

    if state:

        url += f"&state={state}"

    return RedirectResponse(url, status_code=302)

@router.post("/oauth/token")

async def oauth_token(

    grant_type: str = Form(...),

    code: str | None = Form(None),

    redirect_uri: str | None = Form(None),

    client_id: str = Form(...),

    client_secret: str = Form(...),

    db: AsyncSession = Depends(get_db),

):

    app = await db.scalar(select(ClientApp).where(ClientApp.client_id == client_id, ClientApp.is_active.is_(True)))

    if not app or not verify_secret(client_secret, app.client_secret_hash):

        raise HTTPException(401, "Client autentifikatsiyasi muvaffaqiyatsiz")

    if grant_type == "authorization_code":

        if not code:

            raise HTTPException(400, "code kerak")

        auth = await db.get(OAuthAuthorizationCode, code)

        if not auth or auth.used or auth.client_id != client_id:

            raise HTTPException(400, "Noto'g'ri code")

        if auth.expires_at.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):

            raise HTTPException(400, "Code muddati tugagan")

        if redirect_uri and redirect_uri != auth.redirect_uri:

            raise HTTPException(400, "redirect_uri mos emas")

        auth.used = True

        user = await db.get(User, auth.user_id)

        token = create_access_token(user.id, extra={"roles": [], "client_id": client_id, "scope": auth.scope})

        return {

            "access_token": token,

            "token_type": "bearer",

            "expires_in": settings.access_token_expire_minutes * 60,

            "scope": auth.scope,

        }

    if grant_type == "client_credentials":

        token = create_access_token(app.id, extra={"client_id": client_id, "type": "client"}, minutes=30)

        from jose import jwt

        payload = jwt.decode(token, settings.secret_key, algorithms=["HS256"])

        payload["type"] = "client"

        token = jwt.encode(payload, settings.secret_key, algorithm="HS256")

        return {"access_token": token, "token_type": "bearer", "expires_in": 1800}

    raise HTTPException(400, "grant_type qo'llab-quvvatlanmaydi")

@router.get("/oauth/userinfo")

async def userinfo(user: User = Depends(get_current_user)):

    return {

        "sub": user.id,

        "name": user.full_name,

        "email": user.email,

        "roles": [r.code for r in user.roles],

    }

@router.get("/oauth/jwks")

async def jwks():

    return {"keys": []}

