import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.routes_auth import router as auth_router
from app.api.v1.routes_matchmaker import router as matchmaker_router
from app.api.v1.routes_resources import router as resources_router
from app.api.v1.routes_dashboard import router as dashboard_router
from app.api.v1.routes_tickets import router as tickets_router
from app.api.v1.routes_voice import router as voice_router
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.websockets.connection_manager import router as websocket_router
from app.workers.expiry_worker import expiry_worker_loop

configure_logging()
settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
    stop_event = asyncio.Event()
    worker_task = asyncio.create_task(expiry_worker_loop(stop_event))
    try:
        yield
    finally:
        stop_event.set()
        await worker_task


app = FastAPI(title=settings.app_name, lifespan=lifespan)

# Permit the local static debug client without opening CORS to arbitrary origins.
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:\d+)?",
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)

app.include_router(auth_router, prefix="/api/v1")
app.include_router(voice_router, prefix="/api/v1")
app.include_router(tickets_router, prefix="/api/v1")
app.include_router(matchmaker_router, prefix="/api/v1")
app.include_router(resources_router, prefix="/api/v1")
app.include_router(dashboard_router, prefix="/api/v1")
app.include_router(websocket_router)


@app.get("/health", tags=["health"])
async def health_check() -> dict[str, str]:
    return {"status": "ok"}
