from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.core.config import settings
from app.core.db import db_instance, get_db

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 서버 시작 시 MongoDB 연결 기동
    db_instance.connect()
    yield
    # 서버 종료 시 MongoDB 연결 해제
    db_instance.disconnect()

app = FastAPI(
    title=settings.PROJECT_NAME, 
    version="1.0.0",
    lifespan=lifespan
)

@app.get("/")
def health_check():
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "database": "connected"
    }