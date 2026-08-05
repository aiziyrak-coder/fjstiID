from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api import admin_clients, admin_org, admin_settings, admin_users, auth, face, oauth_stats, portal
from app.config import get_settings
from app.services.users import UPLOAD_ROOT

settings = get_settings()

# Ensure media directory exists before StaticFiles mount
UPLOAD_ROOT.mkdir(parents=True, exist_ok=True)
(UPLOAD_ROOT / "photos").mkdir(parents=True, exist_ok=True)


@asynccontextmanager
async def lifespan(_: FastAPI):
    UPLOAD_ROOT.mkdir(parents=True, exist_ok=True)
    (UPLOAD_ROOT / "photos").mkdir(parents=True, exist_ok=True)
    yield


app = FastAPI(
    title=settings.app_name,
    description="Farg'ona Jamoat Salomatligi Tibbiyot Instituti — yagona identifikatsiya va FaceID platformasi",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(admin_users.router)
app.include_router(admin_org.router)
app.include_router(admin_clients.router)
app.include_router(admin_settings.router)
app.include_router(face.router)
app.include_router(portal.router)
app.include_router(oauth_stats.router)

app.mount("/media", StaticFiles(directory=str(UPLOAD_ROOT)), name="media")


@app.get("/health")
async def health():
    return {"status": "ok", "app": settings.app_name}
