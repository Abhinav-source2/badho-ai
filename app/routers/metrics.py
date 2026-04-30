from fastapi import APIRouter
from app.core.metrics import get_metrics

router = APIRouter()

@router.get("/metrics")
def metrics():
    return get_metrics()