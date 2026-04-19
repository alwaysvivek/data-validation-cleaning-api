"""Health check endpoint."""

from fastapi import APIRouter

from app.config import settings

router = APIRouter(tags=["Health"])


@router.get("/health")
async def health_check():
    """Return service health status, version, and Groq availability."""
    return {
        "status": "healthy",
        "version": settings.APP_VERSION,
        "groq_available": settings.groq_available,
    }
