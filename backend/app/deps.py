from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer, APIKeyHeader
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models import ClientApp, Department, StudentProfile, StaffProfile, StudyGroup, User
from app.security import decode_token, verify_secret

bearer = HTTPBearer(auto_error=False)
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

USER_LOAD = (
    selectinload(User.roles),
    selectinload(User.document),
    selectinload(User.address),
    selectinload(User.emergency_contact),
    selectinload(User.student_profile).selectinload(StudentProfile.faculty),
    selectinload(User.student_profile).selectinload(StudentProfile.specialty),
    selectinload(User.student_profile).selectinload(StudentProfile.group).selectinload(StudyGroup.department).selectinload(Department.faculty),
    selectinload(User.staff_profile).selectinload(StaffProfile.department),
    selectinload(User.face_biometrics),
    selectinload(User.consents),
)


async def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: AsyncSession = Depends(get_db),
) -> User:
    if not creds:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Autentifikatsiya talab qilinadi")
    payload = decode_token(creds.credentials)
    if not payload or payload.get("type") != "access":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Noto'g'ri token")
    user_id = payload.get("sub")
    result = await db.execute(
        select(User)
        .options(*USER_LOAD)
        .where(User.id == user_id, User.is_deleted.is_(False))
    )
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Foydalanuvchi topilmadi")
    return user


def require_roles(*role_names: str):
    async def checker(user: User = Depends(get_current_user)) -> User:
        names = {r.code for r in user.roles}
        if "admin" in names:
            return user
        if not names.intersection(role_names):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Ruxsat yo'q")
        return user

    return checker


async def get_client_app(
    api_key: str | None = Depends(api_key_header),
    db: AsyncSession = Depends(get_db),
) -> ClientApp | None:
    if not api_key:
        return None
    result = await db.execute(select(ClientApp).where(ClientApp.is_active.is_(True)))
    for app in result.scalars().all():
        if app.api_key_hash and verify_secret(api_key, app.api_key_hash):
            return app
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Noto'g'ri API kalit")


async def require_client_app(
    api_key: str | None = Depends(api_key_header),
    db: AsyncSession = Depends(get_db),
) -> ClientApp:
    app = await get_client_app(api_key, db)
    if not app:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="X-API-Key talab qilinadi")
    return app
