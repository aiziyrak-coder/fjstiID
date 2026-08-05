from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.deps import USER_LOAD, get_current_user
from app.models import AccessLog, User
from app.schemas import LoginRequest, TokenResponse, UserOut
from app.security import create_access_token, verify_password
from app.services.users import user_to_out

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.get("/login")
async def login_info():
    """Brauzer GET (prefetch) qilsa 405 chiqmasin — kirish faqat POST."""
    return {"ok": True, "message": "Login uchun POST /api/v1/auth/login yuboring", "methods": ["POST"]}


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(User).options(*USER_LOAD).where(User.email == body.email, User.is_deleted.is_(False))
    )
    user = result.scalar_one_or_none()
    ok = user and verify_password(body.password, user.password_hash)
    db.add(
        AccessLog(
            user_id=user.id if user else None,
            method="password",
            success=bool(ok),
            detail="login",
        )
    )
    if not ok:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Email yoki parol noto'g'ri")
    roles = [r.code for r in user.roles]
    token = create_access_token(user.id, extra={"roles": roles, "email": user.email})
    return TokenResponse(access_token=token, user=user_to_out(user))


@router.get("/me", response_model=UserOut)
async def me(user: User = Depends(get_current_user)):
    return user_to_out(user)
