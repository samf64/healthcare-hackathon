from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes import router as api_router
from app.config import settings
from app.database import Base, engine
from app.scheduler import start_scheduler, stop_scheduler


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    start_scheduler()
    try:
        yield
    finally:
        stop_scheduler()


app = FastAPI(title=settings.app_name, lifespan=lifespan)
app.include_router(api_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}

