from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import get_settings
from app.database.session import init_db
from app.routers import auth, me, cameras, incidents, users, ws

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield
    # shutdown if needed


app = FastAPI(
    title=settings.app_name,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(me.router)
app.include_router(users.router)
app.include_router(cameras.router)
app.include_router(incidents.router)
app.include_router(ws.router)

# Snapshot dosyalarını statik olarak sun
# Backend: backend/, snapshot'lar: ../snapshots/ (proje kökü)
_SNAPSHOT_DIR = Path(__file__).resolve().parent.parent.parent / "snapshots"
_SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/snapshots", StaticFiles(directory=str(_SNAPSHOT_DIR)), name="snapshots")


@app.get("/health")
async def health():
    return {"status": "ok"}
