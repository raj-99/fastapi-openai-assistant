import logging
from fastapi import FastAPI
from app.core.config import settings
from app.core.logging import setup_logging
from app.routes.answer import router as answer_router

setup_logging()
logger = logging.getLogger("main")

app = FastAPI(title=settings.app_name)

@app.get("/api/health")
def health():
    return {"status": "ok"}

app.include_router(answer_router, prefix="/api")

logger.info(f"Started application: {settings.app_name} || environment = {settings.environment} ")