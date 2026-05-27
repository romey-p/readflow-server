from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.core.config import settings
from app.core.db import db_instance
from app.routers.analysis_router import router as analysis_router
from app.routers.resource_router import router as resource_router
from app.services.analysis_service import analysis_service

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 서버 시작 시 MongoDB 연결 기동
    db_instance.connect()
    analysis_service.load_model()
    yield
    # 서버 종료 시 MongoDB 연결 해제
    db_instance.disconnect()

app = FastAPI(
    title=settings.PROJECT_NAME, 
    version="1.0.0",
    lifespan=lifespan
)
app.include_router(analysis_router)
app.include_router(resource_router)

@app.get("/")
def health_check():
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "database": "connected"
    }