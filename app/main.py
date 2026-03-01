import logging
import uuid
from fastapi import FastAPI, Request
from fastapi.concurrency import asynccontextmanager
from app.core.config import settings
from app.core.logging import setup_logging
from app.routes.answer import router as answer_router
from app.routes.ingest import router as ingest_router
# from app.core.db import init_db

setup_logging()
logger = logging.getLogger("main")
# @asynccontextmanager
# async def lifespan(app: FastAPI):
#     logger.info("Initializing database...")
#     init_db()
#     yield

# app = FastAPI(title=settings.app_name, lifespan=lifespan)
app = FastAPI(title=settings.app_name)    
@app.middleware("http")
async def add_request_id(request: Request, call_next):
    request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers["x-request-id"] = request_id
    return response

@app.get("/api/health")
def health():
    return {"status": "ok"}

app.include_router(answer_router, prefix="/api")
app.include_router(ingest_router, prefix="/api")

logger.info(f"Started application: {settings.app_name} || environment = {settings.environment} ")