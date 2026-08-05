from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.deps import require_roles
from app.models import AcademicYear, Department, Faculty, Specialty, StaffProfile, StudentProfile, StudyGroup, User
from app.schemas import (
    AcademicYearIn,
    AcademicYearOut,
    DepartmentIn,
    DepartmentOut,
    FacultyIn,
    FacultyOut,
    GroupIn,
    GroupOut,
    SpecialtyIn,
    SpecialtyOut,
)
from app.services.users import write_audit

router = APIRouter(prefix="/api/v1/admin/org", tags=["admin-org"])


# ---------- Fakultetlar ----------

@router.get("/faculties", response_model=list[FacultyOut])
async def list_faculties(_: User = Depends(require_roles("admin", "moderator")), db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(select(Faculty).order_by(Faculty.name))).scalars().all()
    out = []
    for f in rows:
        cnt = await db.scalar(select(func.count()).select_from(Department).where(Department.faculty_id == f.id)) or 0
        item = FacultyOut.model_validate(f)
        item.departments_count = cnt
        out.append(item)
    return out


@router.post("/faculties", response_model=FacultyOut, status_code=201)
async def create_faculty(body: FacultyIn, admin: User = Depends(require_roles("admin")), db: AsyncSession = Depends(get_db)):
    fac = Faculty(**body.model_dump())
    db.add(fac)
    await db.flush()
    await write_audit(db, admin.id, "create", "faculty", fac.id)
    return FacultyOut.model_validate(fac)


@router.patch("/faculties/{faculty_id}", response_model=FacultyOut)
async def update_faculty(
    faculty_id: str, body: FacultyIn, admin: User = Depends(require_roles("admin")), db: AsyncSession = Depends(get_db)
):
    fac = await db.get(Faculty, faculty_id)
    if not fac:
        raise HTTPException(404, "Fakultet topilmadi")
    for k, v in body.model_dump().items():
        setattr(fac, k, v)
    await write_audit(db, admin.id, "update", "faculty", faculty_id)
    return FacultyOut.model_validate(fac)


@router.delete("/faculties/{faculty_id}")
async def delete_faculty(faculty_id: str, admin: User = Depends(require_roles("admin")), db: AsyncSession = Depends(get_db)):
    fac = await db.get(Faculty, faculty_id)
    if not fac:
        raise HTTPException(404, "Fakultet topilmadi")
    await db.delete(fac)
    await write_audit(db, admin.id, "delete", "faculty", faculty_id)
    return {"message": "OK"}


# ---------- Kafedralar ----------

@router.get("/departments", response_model=list[DepartmentOut])
async def list_departments(
    faculty_id: str | None = None,
    _: User = Depends(require_roles("admin", "moderator")),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Department).options(selectinload(Department.faculty)).order_by(Department.name)
    if faculty_id:
        stmt = stmt.where(Department.faculty_id == faculty_id)
    rows = (await db.execute(stmt)).scalars().all()
    out = []
    for d in rows:
        item = DepartmentOut.model_validate(d)
        item.faculty_name = d.faculty.name if d.faculty else None
        item.groups_count = await db.scalar(
            select(func.count()).select_from(StudyGroup).where(StudyGroup.department_id == d.id)
        ) or 0
        item.staff_count = await db.scalar(
            select(func.count()).select_from(StaffProfile).where(StaffProfile.department_id == d.id)
        ) or 0
        out.append(item)
    return out


@router.post("/departments", response_model=DepartmentOut, status_code=201)
async def create_department(
    body: DepartmentIn, admin: User = Depends(require_roles("admin")), db: AsyncSession = Depends(get_db)
):
    if not body.faculty_id:
        raise HTTPException(400, "Kafedra fakultetga biriktirilishi shart")
    d = Department(**body.model_dump())
    db.add(d)
    await db.flush()
    await write_audit(db, admin.id, "create", "department", d.id)
    fac = await db.get(Faculty, body.faculty_id)
    item = DepartmentOut.model_validate(d)
    item.faculty_name = fac.name if fac else None
    return item


@router.patch("/departments/{department_id}", response_model=DepartmentOut)
async def update_department(
    department_id: str, body: DepartmentIn, admin: User = Depends(require_roles("admin")), db: AsyncSession = Depends(get_db)
):
    d = await db.get(Department, department_id)
    if not d:
        raise HTTPException(404, "Kafedra topilmadi")
    for k, v in body.model_dump().items():
        setattr(d, k, v)
    await write_audit(db, admin.id, "update", "department", department_id)
    fac = await db.get(Faculty, d.faculty_id) if d.faculty_id else None
    item = DepartmentOut.model_validate(d)
    item.faculty_name = fac.name if fac else None
    return item


@router.delete("/departments/{department_id}")
async def delete_department(
    department_id: str, admin: User = Depends(require_roles("admin")), db: AsyncSession = Depends(get_db)
):
    d = await db.get(Department, department_id)
    if not d:
        raise HTTPException(404, "Kafedra topilmadi")
    await db.delete(d)
    await write_audit(db, admin.id, "delete", "department", department_id)
    return {"message": "OK"}


# ---------- Guruhlar ----------

@router.get("/groups", response_model=list[GroupOut])
async def list_groups(
    department_id: str | None = None,
    faculty_id: str | None = None,
    _: User = Depends(require_roles("admin", "moderator")),
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(StudyGroup)
        .options(selectinload(StudyGroup.department).selectinload(Department.faculty))
        .order_by(StudyGroup.name)
    )
    if department_id:
        stmt = stmt.where(StudyGroup.department_id == department_id)
    rows = (await db.execute(stmt)).scalars().all()
    out = []
    for g in rows:
        if faculty_id and (not g.department or g.department.faculty_id != faculty_id):
            continue
        item = GroupOut.model_validate(g)
        item.department_name = g.department.name if g.department else None
        item.faculty_id = g.department.faculty_id if g.department else None
        item.faculty_name = g.department.faculty.name if g.department and g.department.faculty else None
        item.students_count = await db.scalar(
            select(func.count()).select_from(StudentProfile).where(StudentProfile.group_id == g.id)
        ) or 0
        out.append(item)
    return out


@router.post("/groups", response_model=GroupOut, status_code=201)
async def create_group(body: GroupIn, admin: User = Depends(require_roles("admin")), db: AsyncSession = Depends(get_db)):
    if not body.department_id:
        raise HTTPException(400, "Guruh kafedraga biriktirilishi shart")
    g = StudyGroup(**body.model_dump())
    db.add(g)
    await db.flush()
    await write_audit(db, admin.id, "create", "group", g.id)
    dept = await db.get(Department, body.department_id)
    fac = await db.get(Faculty, dept.faculty_id) if dept and dept.faculty_id else None
    item = GroupOut.model_validate(g)
    item.department_name = dept.name if dept else None
    item.faculty_id = dept.faculty_id if dept else None
    item.faculty_name = fac.name if fac else None
    return item


@router.patch("/groups/{group_id}", response_model=GroupOut)
async def update_group(
    group_id: str, body: GroupIn, admin: User = Depends(require_roles("admin")), db: AsyncSession = Depends(get_db)
):
    g = await db.get(StudyGroup, group_id)
    if not g:
        raise HTTPException(404, "Guruh topilmadi")
    for k, v in body.model_dump().items():
        setattr(g, k, v)
    await write_audit(db, admin.id, "update", "group", group_id)
    dept = await db.get(Department, g.department_id) if g.department_id else None
    fac = await db.get(Faculty, dept.faculty_id) if dept and dept.faculty_id else None
    item = GroupOut.model_validate(g)
    item.department_name = dept.name if dept else None
    item.faculty_id = dept.faculty_id if dept else None
    item.faculty_name = fac.name if fac else None
    return item


@router.delete("/groups/{group_id}")
async def delete_group(group_id: str, admin: User = Depends(require_roles("admin")), db: AsyncSession = Depends(get_db)):
    g = await db.get(StudyGroup, group_id)
    if not g:
        raise HTTPException(404, "Guruh topilmadi")
    await db.delete(g)
    await write_audit(db, admin.id, "delete", "group", group_id)
    return {"message": "OK"}


# ---------- Yo'nalishlar ----------

@router.get("/specialties", response_model=list[SpecialtyOut])
async def list_specialties(
    faculty_id: str | None = None,
    _: User = Depends(require_roles("admin", "moderator")),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Specialty).options(selectinload(Specialty.faculty)).order_by(Specialty.name)
    if faculty_id:
        stmt = stmt.where(Specialty.faculty_id == faculty_id)
    out = []
    for s in (await db.execute(stmt)).scalars().all():
        item = SpecialtyOut.model_validate(s)
        item.faculty_name = s.faculty.name if s.faculty else None
        out.append(item)
    return out


@router.post("/specialties", response_model=SpecialtyOut, status_code=201)
async def create_specialty(
    body: SpecialtyIn, admin: User = Depends(require_roles("admin")), db: AsyncSession = Depends(get_db)
):
    s = Specialty(**body.model_dump())
    db.add(s)
    await db.flush()
    await write_audit(db, admin.id, "create", "specialty", s.id)
    fac = await db.get(Faculty, s.faculty_id) if s.faculty_id else None
    item = SpecialtyOut.model_validate(s)
    item.faculty_name = fac.name if fac else None
    return item


@router.patch("/specialties/{specialty_id}", response_model=SpecialtyOut)
async def update_specialty(
    specialty_id: str, body: SpecialtyIn, admin: User = Depends(require_roles("admin")), db: AsyncSession = Depends(get_db)
):
    s = await db.get(Specialty, specialty_id)
    if not s:
        raise HTTPException(404, "Yo'nalish topilmadi")
    for k, v in body.model_dump().items():
        setattr(s, k, v)
    await write_audit(db, admin.id, "update", "specialty", specialty_id)
    fac = await db.get(Faculty, s.faculty_id) if s.faculty_id else None
    item = SpecialtyOut.model_validate(s)
    item.faculty_name = fac.name if fac else None
    return item


@router.delete("/specialties/{specialty_id}")
async def delete_specialty(
    specialty_id: str, admin: User = Depends(require_roles("admin")), db: AsyncSession = Depends(get_db)
):
    s = await db.get(Specialty, specialty_id)
    if not s:
        raise HTTPException(404, "Yo'nalish topilmadi")
    await db.delete(s)
    await write_audit(db, admin.id, "delete", "specialty", specialty_id)
    return {"message": "OK"}


# ---------- O'quv yillari ----------

@router.get("/academic-years", response_model=list[AcademicYearOut])
async def list_years(_: User = Depends(require_roles("admin", "moderator")), db: AsyncSession = Depends(get_db)):
    return (await db.execute(select(AcademicYear).order_by(AcademicYear.name.desc()))).scalars().all()


@router.post("/academic-years", response_model=AcademicYearOut, status_code=201)
async def create_year(
    body: AcademicYearIn, admin: User = Depends(require_roles("admin")), db: AsyncSession = Depends(get_db)
):
    if body.is_current:
        for y in (await db.execute(select(AcademicYear))).scalars().all():
            y.is_current = False
    y = AcademicYear(**body.model_dump())
    db.add(y)
    await db.flush()
    await write_audit(db, admin.id, "create", "academic_year", y.id)
    return y


@router.patch("/academic-years/{year_id}", response_model=AcademicYearOut)
async def update_year(
    year_id: str, body: AcademicYearIn, admin: User = Depends(require_roles("admin")), db: AsyncSession = Depends(get_db)
):
    y = await db.get(AcademicYear, year_id)
    if not y:
        raise HTTPException(404, "O'quv yili topilmadi")
    if body.is_current:
        for other in (await db.execute(select(AcademicYear))).scalars().all():
            other.is_current = False
    for k, v in body.model_dump().items():
        setattr(y, k, v)
    await write_audit(db, admin.id, "update", "academic_year", year_id)
    return y


@router.delete("/academic-years/{year_id}")
async def delete_year(year_id: str, admin: User = Depends(require_roles("admin")), db: AsyncSession = Depends(get_db)):
    y = await db.get(AcademicYear, year_id)
    if not y:
        raise HTTPException(404, "O'quv yili topilmadi")
    await db.delete(y)
    await write_audit(db, admin.id, "delete", "academic_year", year_id)
    return {"message": "OK"}
