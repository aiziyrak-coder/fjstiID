import secrets

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.deps import require_roles
from app.models import ClientApp, User
from app.schemas import ClientAppCreate, ClientAppCreated, ClientAppOut
from app.security import hash_secret
from app.services.users import write_audit

router = APIRouter(prefix="/api/v1/admin/clients", tags=["admin-clients"])


@router.get("", response_model=list[ClientAppOut])
async def list_clients(_: User = Depends(require_roles("admin")), db: AsyncSession = Depends(get_db)):
    return (await db.execute(select(ClientApp).order_by(ClientApp.created_at.desc()))).scalars().all()


@router.post("", response_model=ClientAppCreated, status_code=201)
async def create_client(
    body: ClientAppCreate,
    admin: User = Depends(require_roles("admin")),
    db: AsyncSession = Depends(get_db),
):
    client_id = secrets.token_hex(8)
    client_secret = secrets.token_urlsafe(24)
    api_key = "fjsti_" + secrets.token_hex(20)
    app = ClientApp(
        name=body.name,
        client_id=client_id,
        client_secret_hash=hash_secret(client_secret),
        api_key_hash=hash_secret(api_key),
        allowed_scopes=body.allowed_scopes,
        allowed_fields=body.allowed_fields,
        redirect_uris=body.redirect_uris,
        webhook_url=body.webhook_url,
    )
    db.add(app)
    await db.flush()
    await write_audit(db, admin.id, "create", "client_app", app.id, {"name": app.name})
    out = ClientAppCreated.model_validate(app)
    out.client_secret = client_secret
    out.api_key = api_key
    return out


@router.patch("/{client_id}", response_model=ClientAppOut)
async def update_client(
    client_id: str,
    body: ClientAppCreate,
    admin: User = Depends(require_roles("admin")),
    db: AsyncSession = Depends(get_db),
):
    app = await db.get(ClientApp, client_id)
    if not app:
        raise HTTPException(404, "Client topilmadi")
    for k, v in body.model_dump().items():
        setattr(app, k, v)
    await write_audit(db, admin.id, "update", "client_app", app.id)
    return app


@router.delete("/{client_id}")
async def deactivate_client(
    client_id: str,
    admin: User = Depends(require_roles("admin")),
    db: AsyncSession = Depends(get_db),
):
    app = await db.get(ClientApp, client_id)
    if not app:
        raise HTTPException(404, "Client topilmadi")
    app.is_active = False
    await write_audit(db, admin.id, "delete", "client_app", app.id)
    return {"message": "Deaktivlashtirildi"}
