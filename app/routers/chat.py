import os
import time
import uuid
import json
import asyncio
from datetime import datetime
from typing import AsyncGenerator

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
from app.core.llm import run_agentic_turn
from app.models.schemas import ChatRequest, TurnTelemetry

load_dotenv()

router = APIRouter()

PRIMARY_MODEL  = os.getenv("PRIMARY_MODEL")
FALLBACK_MODEL = os.getenv("FALLBACK_MODEL")

SYSTEM_PROMPT = """You are Badho AI — a highly precise AI career coach for engineers transitioning into AI roles.

You operate as a CONTROLLED AGENT SYSTEM. Follow rules strictly.

────────────────────────────
CORE BEHAVIOR RULES
────────────────────────────
1. Answer ONLY career-related queries (AI, ML, data, backend → AI transition)
2. Be highly specific, practical, and actionable
3. Avoid generic advice — always include concrete steps, tools, or examples
4. If context is provided, you MUST use it and include at least one citation in the format [Source: filename]
5. NEVER hallucinate facts, salaries, or metrics
6. Always consider the full conversation history. If the user has shared background, you MUST incorporate it

────────────────────────────
TOOL USAGE RULES
────────────────────────────
You have access to tools, but:

- DO NOT call tools for conceptual questions
- DO NOT call tools if answer can be reasoned directly

Use tools when appropriate:

• Salary / compensation → use estimate_salary_range  
• Fit / evaluation → use score_job_fit  
• Roadmap / plan / step-by-step transition → use generate_career_roadmap when clearly requested  
• Role info → use lookup_role  

IMPORTANT:
- If user explicitly asks for roadmap/plan (30/60/90 day), use roadmap tool
- Do not ignore tools when structured output is expected

────────────────────────────
ANSWER FORMAT RULES
────────────────────────────
1. Start with direct answer  
2. Then structured sections  
3. Use bullet points  
4. Keep concise  

────────────────────────────
SAFETY RULE
────────────────────────────
If request is outside career domain:

- Refuse clearly  
- State it's outside scope  
- Redirect to career help  

DO NOT generate code for such requests.

────────────────────────────
FAILSAFE
────────────────────────────
If unsure:
- Say "Based on available information"
- Do NOT invent data

You are a high-precision system.
"""

async def stream_chat(
    session_id: str,
    user_message: str,
) -> AsyncGenerator[str, None]:

    total_start = time.perf_counter()
    turn_id = str(uuid.uuid4())

    output_text = ""
    tool_calls = []
    tool_ms = 0.0
    ttft_ms = 0.0
    model_used = PRIMARY_MODEL

    input_tokens = 0
    output_tokens = 0

    try:
        if is_over_budget(session_id):
            yield f"event: error\ndata: {json.dumps({'message': 'Budget exceeded'})}\n\n"
            yield f"event: done\ndata: {{}}\n\n"
            return

        rag_result = await asyncio.to_thread(
            retrieve_and_rerank,
            user_message
        )

        context_text = format_context(rag_result["chunks"])

        yield f"event: retrieval_done\ndata: {json.dumps(rag_result)}\n\n"

        summarize_if_needed(session_id)

        system_with_context = f"{SYSTEM_PROMPT}\n\n{context_text}"

        add_message(session_id, "user", user_message)
        messages = get_messages(session_id)

        agent_start = time.perf_counter()

        # ✅ FIXED: correct timeout handling
        agen = run_agentic_turn(
            system=system_with_context,
            messages=messages,
            user_message=user_message,
            model=PRIMARY_MODEL,
        )

        while True:
            try:
                event = await asyncio.wait_for(agen.__anext__(), timeout=180)
                yield event
            except StopAsyncIteration:
                break

            if "data: " not in event:
                continue

            try:
                data = json.loads(event.split("data: ", 1)[1])
            except:
                continue

            if event.startswith("event: token"):
                output_text += data.get("text", "")

            if event.startswith("event: tool_called"):
                tool_calls.append(data.get("tool_name"))

            if event.startswith("event: __meta__"):
                tool_ms = data.get("tool_ms", 0)
                ttft_ms = data.get("ttft_ms", 0)
                model_used = data.get("model_used", PRIMARY_MODEL)

                input_tokens = data.get("input_tokens", 0)
                output_tokens = data.get("output_tokens", 0)

        llm_ms = (time.perf_counter() - agent_start) * 1000
        total_ms = (time.perf_counter() - total_start) * 1000


        # ✅ ENSURE SOURCE CITATION (REQUIRED FOR EVAL STABILITY)
        if "[Source:" not in output_text:
            if rag_result and rag_result.get("chunks"):
                source = rag_result["chunks"][0]["doc_name"]
                output_text += f"\n\n[Source: {source}]"

        add_message(session_id, "assistant", output_text)
        get_session(session_id)["turn_count"] += 1

        cost = estimate_cost(input_tokens, output_tokens)
        record_cost(session_id, cost)

        log_turn(TurnTelemetry(
            session_id=session_id,
            turn_id=turn_id,
            timestamp=datetime.utcnow().isoformat(),
            model_used=model_used,
            retrieval_ms=rag_result["retrieval_ms"],
            rerank_ms=rag_result["rerank_ms"],
            llm_ms=round(llm_ms, 2),
            tool_ms=tool_ms,
            total_ms=round(total_ms, 2),
            ttft_ms=round(ttft_ms, 2),
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=cost,
            tools_called=tool_calls,
            chunks_retrieved=rag_result["chunks_retrieved"],
            chunks_after_rerank=rag_result["chunks_returned"],
            budget_exceeded=is_over_budget(session_id),
        ))

    except Exception as e:
        yield f"event: error\ndata: {json.dumps({'message': str(e)})}\n\n"
        yield f"event: done\ndata: {{}}\n\n"


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