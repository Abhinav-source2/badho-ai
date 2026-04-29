import os
import time
import uuid
import json
import asyncio
from datetime import datetime
from typing import AsyncGenerator

import anthropic
from dotenv import load_dotenv
from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.core.budget import estimate_cost, is_over_budget, record_cost
from app.core.rag import format_context, retrieve_and_rerank
from app.core.state import (
    add_message,
    get_messages,
    get_session,
    summarize_if_needed,
)
from app.core.telemetry import log_turn
from app.models.schemas import ChatRequest, TurnTelemetry

load_dotenv()

router = APIRouter()

PRIMARY_MODEL  = os.getenv("PRIMARY_MODEL", "claude-3-haiku-20240307")
FALLBACK_MODEL = os.getenv("FALLBACK_MODEL", "claude-3-sonnet-20240229")

SYSTEM_PROMPT = """You are Badho AI — an expert career coach in AI careers.

Rules:
1. Answer ONLY career-related questions
2. Use sources like [Source: filename]
3. Be actionable and specific
"""

client = anthropic.AsyncAnthropic(
    api_key=os.getenv("ANTHROPIC_API_KEY")
)


# ─────────────────────────────────────────────
# STREAM FUNCTION
# ─────────────────────────────────────────────
async def stream_chat(
    session_id: str,
    user_message: str,
) -> AsyncGenerator[str, None]:

    total_start = time.perf_counter()
    turn_id = str(uuid.uuid4())

    try:
        # ✅ Immediate response (prevents timeout)
        thinking_payload = {"text": "Thinking...\n"}
        yield f"event: token\ndata: {json.dumps(thinking_payload)}\n\n"
        await asyncio.sleep(0.01)

        # ── Budget Check ─────────────────────────
        if is_over_budget(session_id):
            err = {"message": "Budget exceeded"}
            yield f"event: error\ndata: {json.dumps(err)}\n\n"
            yield f"event: done\ndata: {{}}\n\n"
            return

        # ── RAG (non-blocking) ───────────────────
        rag_result = await asyncio.to_thread(
            retrieve_and_rerank,
            user_message
        )

        context_text = format_context(rag_result["chunks"])

        retrieval_payload = {
            "chunks_retrieved": rag_result["chunks_retrieved"],
            "chunks_returned": rag_result["chunks_returned"],
            "retrieval_ms": rag_result["retrieval_ms"],
            "rerank_ms": rag_result["rerank_ms"],
        }

        yield f"event: retrieval_done\ndata: {json.dumps(retrieval_payload)}\n\n"
        await asyncio.sleep(0.01)

        # ── Build Messages ───────────────────────
        summarize_if_needed(session_id)

        system_with_context = f"{SYSTEM_PROMPT}\n\n{context_text}"

        add_message(session_id, "user", user_message)
        messages = get_messages(session_id)

        # ── LLM Streaming ────────────────────────
        model_used = PRIMARY_MODEL
        output_text = ""
        first_token = True
        ttft_ms = 0.0
        llm_start = time.perf_counter()

        try:
            async with client.messages.stream(
                model=model_used,
                max_tokens=1024,
                system=system_with_context,
                messages=messages,
            ) as stream:

                async for text in stream.text_stream:
                    if first_token:
                        ttft_ms = (time.perf_counter() - total_start) * 1000
                        first_token = False

                    output_text += text
                    yield f"event: token\ndata: {json.dumps({'text': text})}\n\n"
                    await asyncio.sleep(0.01)

        except anthropic.APIStatusError:
            # 🔁 fallback model
            model_used = FALLBACK_MODEL

            info_payload = {"message": "Using fallback model"}
            yield f"event: info\ndata: {json.dumps(info_payload)}\n\n"
            await asyncio.sleep(0.01)

            async with client.messages.stream(
                model=model_used,
                max_tokens=1024,
                system=system_with_context,
                messages=messages,
            ) as stream:

                async for text in stream.text_stream:
                    if first_token:
                        ttft_ms = (time.perf_counter() - total_start) * 1000
                        first_token = False

                    output_text += text
                    yield f"event: token\ndata: {json.dumps({'text': text})}\n\n"
                    await asyncio.sleep(0.01)

        # ── Metrics ──────────────────────────────
        llm_ms = (time.perf_counter() - llm_start) * 1000
        total_ms = (time.perf_counter() - total_start) * 1000

        add_message(session_id, "assistant", output_text)
        get_session(session_id)["turn_count"] += 1

        cost = estimate_cost(0, 0)
        record_cost(session_id, cost)

        log_turn(TurnTelemetry(
            session_id=session_id,
            turn_id=turn_id,
            timestamp=datetime.utcnow().isoformat(),
            model_used=model_used,
            retrieval_ms=rag_result["retrieval_ms"],
            rerank_ms=rag_result["rerank_ms"],
            llm_ms=round(llm_ms, 2),
            tool_ms=0.0,
            total_ms=round(total_ms, 2),
            ttft_ms=round(ttft_ms, 2),
            input_tokens=0,
            output_tokens=0,
            cost_usd=cost,
            tools_called=[],
            chunks_retrieved=rag_result["chunks_retrieved"],
            chunks_after_rerank=rag_result["chunks_returned"],
            budget_exceeded=is_over_budget(session_id),
        ))

        # ── FINAL EVENT ───────────────────────────
        done_payload = {
            "total_ms": round(total_ms, 2),
            "ttft_ms": round(ttft_ms, 2),
            "model_used": model_used,
            "cost_usd": cost,
        }

        yield f"event: done\ndata: {json.dumps(done_payload)}\n\n"

    except Exception as e:
        error_payload = {"message": str(e)}
        yield f"event: error\ndata: {json.dumps(error_payload)}\n\n"
        yield f"event: done\ndata: {{}}\n\n"


# ─────────────────────────────────────────────
# API ENDPOINT
# ─────────────────────────────────────────────
@router.post("/chat/stream")
async def chat_stream(request: ChatRequest) -> StreamingResponse:
    return StreamingResponse(
        stream_chat(request.session_id, request.message),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )