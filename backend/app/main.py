from fastapi import FastAPI

from backend.app.core.config import settings
from backend.app.api.auth import router as auth_router

app = FastAPI(
    title=settings.app_name,
    description="Backend for the InterviewIQ AI Interviewer",
    version=settings.app_version,
)


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "message": "InterviewIQ backend is running!",
        "environment": settings.environment,
    }
app.include_router(auth_router)