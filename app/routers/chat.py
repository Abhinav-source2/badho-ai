from fastapi import APIRouter
from fastapi.responses import StreamingResponse
import asyncio

router = APIRouter()   # ✅ REQUIRED

async def stream():
    yield "event: token\ndata: Hello\n\n"
    await asyncio.sleep(1)
    yield "event: done\ndata: {}\n\n"

@router.post("/chat/stream")
async def chat():
    return StreamingResponse(stream(), media_type="text/event-stream")