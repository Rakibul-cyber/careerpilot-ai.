# Health check endpoint — used for liveness/readiness probes.

from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health_check() -> dict:
    return {
        "status": "ok",
        "service": "CareerPilot AI",
        "version": "1.0.0",
    }
