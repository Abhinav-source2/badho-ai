import json
import os
import time
import asyncio
from typing import AsyncGenerator

import anthropic
from dotenv import load_dotenv

from app.core.tools import TOOL_SCHEMAS, execute_tool, TOOL_MAP

load_dotenv()

PRIMARY_MODEL  = os.getenv("PRIMARY_MODEL")
FALLBACK_MODEL = os.getenv("FALLBACK_MODEL")

MAX_ITERATIONS = 5
MAX_TOOL_CALLS = 2


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


# ✅ TOOL VALIDATION
def is_tool_result_valid(result: dict) -> bool:
    if not result:
        return False

    if "error" in result:
        return False

    if "min" in result and "max" in result:
        if result["min"] <= 0 or result["max"] <= 0:
            return False

    return True


# ✅ SMART TOOL DECISION
def should_enable_tools(user_message: str) -> bool:
    msg = user_message.lower()

    if any(k in msg for k in ["salary", "compensation", "pay", "ctc"]):
        return True

    if any(k in msg for k in ["roadmap", "plan", "30 day", "60 day", "90 day"]):
        return True

    if any(k in msg for k in ["fit", "evaluate", "rate me"]):
        return True

    if any(k in msg for k in ["role", "responsibilities", "what does"]):
        return True

    return False


async def run_agentic_turn(
    system: str,
    messages: list[dict],
    user_message: str,
    model: str | None = None,
) -> AsyncGenerator[str, None]:

    client = anthropic.AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

    active_model = model or PRIMARY_MODEL
    history = list(messages)

    use_tools = should_enable_tools(user_message)

    total_tool_ms = 0.0
    input_tokens = 0
    output_tokens = 0

    tool_call_count = 0

    total_start = time.perf_counter()

    for iteration in range(MAX_ITERATIONS):

        try:
            response = await client.messages.create(
                model=active_model,
                max_tokens=700,
                system=system,
                messages=history,
                tools=TOOL_SCHEMAS if use_tools else [],
            )

        except anthropic.APIStatusError:
            active_model = FALLBACK_MODEL
            yield _sse("info", {"message": f"Switched to fallback model: {active_model}"})
            await asyncio.sleep(0.01)

            response = await client.messages.create(
                model=active_model,
                max_tokens=1024,
                system=system,
                messages=history,
                tools=TOOL_SCHEMAS if use_tools else [],
            )

        input_tokens += response.usage.input_tokens
        output_tokens += response.usage.output_tokens

        # ───────── TOOL USE ─────────
        if response.stop_reason == "tool_use":

            if not use_tools:
                break

            if tool_call_count >= MAX_TOOL_CALLS:
                yield _sse("error", {"message": "Tool call limit reached"})
                break

            history.append({
                "role": "assistant",
                "content": response.content
            })

            tool_results = []

            for block in response.content:
                if block.type != "tool_use":
                    continue

                tool_name = block.name
                tool_input = block.input
                tool_use_id = block.id

                if tool_name not in TOOL_MAP:
                    yield _sse("error", {"message": f"Invalid tool: {tool_name}"})
                    continue

                tool_call_count += 1

                print(f"[AGENT] Calling tool: {tool_name}")
                print(f"[AGENT] Input: {tool_input}")

                # ✅ ADDED (ONLY CHANGE)
                yield _sse("info", {
                    "message": f"Looking up {tool_name.replace('_', ' ')}..."
                })

                yield _sse("tool_called", {
                    "tool_name": tool_name,
                    "tool_input": tool_input,
                })
                await asyncio.sleep(0.01)

                try:
                    result, tool_ms = execute_tool(tool_name, tool_input)
                except Exception as e:
                    result = {"error": str(e)}
                    tool_ms = 0.0

                total_tool_ms += tool_ms

                print(f"[AGENT] Tool result: {result}")

                if not is_tool_result_valid(result):
                    print("[AGENT] Invalid tool result → fallback")

                    yield _sse("info", {
                        "message": f"Tool {tool_name} failed, using reasoning"
                    })
                    await asyncio.sleep(0.01)

                    continue

                yield _sse("tool_done", {
                    "tool_name": tool_name,
                    "latency_ms": tool_ms,
                })
                await asyncio.sleep(0.01)

                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": tool_use_id,
                    "content": json.dumps(result),
                })

            if tool_results:
                history.append({
                    "role": "user",
                    "content": tool_results
                })

            continue

        # ───────── FINAL RESPONSE ─────────
        if response.stop_reason == "end_turn":

            first_token = True
            ttft_ms = 0.0

            try:
                async with client.messages.stream(
                    model=active_model,
                    max_tokens=1024,
                    system=system,
                    messages=history,
                    tools=TOOL_SCHEMAS if use_tools else [],
                ) as stream:

                    async for text in stream.text_stream:

                        if first_token and "Thinking..." in text:
                            continue

                        if first_token:
                            ttft_ms = (time.perf_counter() - total_start) * 1000
                            first_token = False

                        yield _sse("token", {"text": text})
                        await asyncio.sleep(0.01)

                    final = await stream.get_final_message()
                    input_tokens += final.usage.input_tokens
                    output_tokens += final.usage.output_tokens

            except anthropic.APIStatusError:
                active_model = FALLBACK_MODEL

                yield _sse("info", {"message": f"Fallback stream: {active_model}"})
                await asyncio.sleep(0.01)

                async with client.messages.stream(
                    model=active_model,
                    max_tokens=1024,
                    system=system,
                    messages=history,
                    tools=TOOL_SCHEMAS if use_tools else [],
                ) as stream:

                    async for text in stream.text_stream:
                        yield _sse("token", {"text": text})
                        await asyncio.sleep(0.01)

                    final = await stream.get_final_message()
                    input_tokens += final.usage.input_tokens
                    output_tokens += final.usage.output_tokens

            yield _sse("__meta__", {
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "tool_ms": round(total_tool_ms, 2),
                "ttft_ms": round(ttft_ms, 2),
                "model_used": active_model,
            })

            yield _sse("done", {})
            return

    yield _sse("error", {"message": "Max iterations reached"})
    yield _sse("done", {})