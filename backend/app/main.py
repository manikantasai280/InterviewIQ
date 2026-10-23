from fastapi import FastAPI

from backend.app.core.config import settings

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