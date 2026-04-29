from fastapi import APIRouter

router = APIRouter()

@router.get("/metrics")
async def metrics():
    return {"message": "metrics coming later"}