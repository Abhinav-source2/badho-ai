from fastapi import APIRouter
from app.core.telemetry import get_aggregate_stats

router = APIRouter()

@router.get("/metrics")
async def metrics():
    return get_aggregate_stats()