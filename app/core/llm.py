import json
import os
import time
import asyncio
from typing import AsyncGenerator

import anthropic
from dotenv import load_dotenv

from app.core.tools import TOOL_SCHEMAS, execute_tool, TOOL_MAP
from app.core.metrics import record_metrics


def normalize_messages(messages):
    normalized = []
    for m in messages:
        if not m.get("content"):
            continue
        if isinstance(m.get("content"), str):
            normalized.append({
                "role": m["role"],
                "content": [{"type": "text", "text": m["content"]}]
            })
        else:
            normalized.append(m)
    return normalized


def reinforce_last_user_message(messages):
    if len(messages) < 2:
        return messages

    facts = []
    for m in messages[:-1]:
        if m["role"] == "user" and isinstance(m.get("content"), str):
            facts.append(m["content"])

    facts = facts[-2:]

    last = messages[-1]
    if last["role"] == "user" and isinstance(last.get("content"), str):
        prefix = "Use this user context if relevant:\n" + "\n".join(facts) + "\n\n"
        messages[-1] = {
            "role": "user",
            "content": prefix + last["content"]
        }

    return messages


load_dotenv()

PRIMARY_MODEL  = os.getenv("PRIMARY_MODEL")
FALLBACK_MODEL = os.getenv("FALLBACK_MODEL")

MAX_ITERATIONS = 5
MAX_TOOL_CALLS = 2


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


def is_tool_result_valid(result: dict) -> bool:
    if not result:
        return False
    if "error" in result:
        return False
    if "min" in result and "max" in result:
        if result["min"] <= 0 or result["max"] <= 0:
            return False
    return True


def should_enable_tools(user_message: str) -> bool:
    msg = user_message.lower()

    if any(k in msg for k in ["salary", "compensation", "pay", "ctc"]):
        return True

    if any(k in msg for k in [
        "roadmap", "plan", "learning plan",
        "30 day", "60 day", "90 day",
        "step by step", "transition plan"
    ]):
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
    
    yield _sse("token", {"text": "Analyzing your request...\n"})

    client = anthropic.AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

    active_model = model or PRIMARY_MODEL
    history = list(messages)

    use_tools = should_enable_tools(user_message)

    force_roadmap = any(k in user_message.lower() for k in [
        "roadmap", "plan", "30 day", "60 day", "90 day",
        "step by step", "transition plan"
    ])

    total_tool_ms = 0.0
    input_tokens = 0
    output_tokens = 0

    tool_call_count = 0
    total_start = time.perf_counter()

    tool_cycle_done = False

    for iteration in range(MAX_ITERATIONS):

        try:
            request_kwargs = {
                "model": active_model,
                "max_tokens": 900,
                "system": system,
                "messages": normalize_messages(reinforce_last_user_message(history)),
                "tools": TOOL_SCHEMAS if use_tools else [],
            }

            # ✅ FIX: correct tool_choice format
            if force_roadmap and not tool_cycle_done:
                request_kwargs["tool_choice"] = {
                    "type": "auto"
                }

            response = await client.messages.create(**request_kwargs)

        except anthropic.APIStatusError:
            active_model = FALLBACK_MODEL
            yield _sse("info", {"message": f"Switched to fallback model: {active_model}"})
            await asyncio.sleep(0.01)

            request_kwargs = {
                "model": active_model,
                "max_tokens": 1024,
                "system": system,
                "messages": normalize_messages(reinforce_last_user_message(history)),
                "tools": TOOL_SCHEMAS if use_tools else [],
            }

            # ✅ FIX here too
            if force_roadmap and not tool_cycle_done:
                request_kwargs["tool_choice"] = {
                    "type": "auto"
                }

            response = await client.messages.create(**request_kwargs)

        input_tokens += response.usage.input_tokens
        output_tokens += response.usage.output_tokens

        if response.stop_reason == "tool_use":

            # ✅ FIX: prevent loop
            if tool_cycle_done:
                use_tools = False
                continue

            tool_cycle_done = True

            if not use_tools:
                break

            if tool_call_count >= MAX_TOOL_CALLS:
                yield _sse("error", {"message": "Tool call limit reached"})
                break

            if response.content:
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

                if not is_tool_result_valid(result):
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

            if tool_results and len(tool_results) > 0:
                history.append({
                    "role": "user",
                    "content": tool_results
                })

            continue

        if response.stop_reason in ["end_turn", "stop", "max_tokens"]:

            first_token = True
            ttft_ms = 0.0

            async with client.messages.stream(
                model=active_model,
                max_tokens=1500,
                system=system,
                messages=normalize_messages(history),

                # ✅ CRITICAL FIX: disable tools here
                tools=[]
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

            cost = (
                input_tokens * 0.80 / 1_000_000 +
                output_tokens * 4.00 / 1_000_000
            )
            record_metrics(ttft_ms, cost)

            yield _sse("__meta__", {
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "tool_ms": round(total_tool_ms, 2),
                "ttft_ms": round(ttft_ms, 2),
                "model_used": active_model,
                "cost_usd": round(cost, 6),
            })

            yield _sse("done", {})
            return

    yield _sse("error", {"message": "Max iterations reached"})
    yield _sse("done", {})