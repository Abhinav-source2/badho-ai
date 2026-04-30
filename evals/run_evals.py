import argparse
import json
import os
import time
import uuid
from datetime import datetime

import httpx
from anthropic import Anthropic
from dotenv import load_dotenv

from evals.test_cases import TEST_CASES

load_dotenv()

BASE_URL = "http://localhost:8000"
JUDGE_MODEL = "claude-haiku-4-5-20251001"
_judge_client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))


# ─────────────────────────────────────────────
# SSE TURN RUNNER (FIXED)
# ─────────────────────────────────────────────

def run_turn(session_id: str, message: str, base_url: str) -> dict:
    text = ""
    tools_fired = []
    events = []
    meta = {}

    limits = httpx.Limits(
    max_keepalive_connections=5,
    max_connections=10
    )

    with httpx.Client(limits=limits).stream(
        "POST",
        f"{base_url}/chat/stream",
        json={"session_id": session_id, "message": message},
        timeout=httpx.Timeout(180.0, read=180.0),  # ✅ increased for agent + tools
    ) as r:

        buffer = ""

        for raw in r.iter_bytes():
            buffer += raw.decode()

            parts = buffer.split("\n\n")
            buffer = parts.pop()

            for block in parts:
                lines = block.strip().split("\n")

                evt_type = None
                data_str = None

                for line in lines:
                    if line.startswith("event: "):
                        evt_type = line[7:].strip()
                    elif line.startswith("data: "):
                        data_str = line[6:].strip()

                if not data_str:
                    continue

                try:
                    d = json.loads(data_str)
                except:
                    continue

                events.append({"event": evt_type, "data": d})

                # ── TEXT STREAM ──
                if evt_type == "token":
                    text += d.get("text", "")

                # ── TOOL TRACKING ──
                if evt_type == "tool_called":
                    tools_fired.append(d.get("tool_name"))

                # ✅ FIX: meta comes from __meta__ (not done)
                if evt_type == "__meta__":
                    meta = d

    return {
        "text": text,
        "tools_fired": tools_fired,
        "events": events,
        "cost_usd": meta.get("cost_usd", 0),
        "ttft_ms": meta.get("ttft_ms", 0),
    }


# ─────────────────────────────────────────────
# MULTI TURN
# ─────────────────────────────────────────────

def run_multiturn(turns: list[str], base_url: str):
    session_id = str(uuid.uuid4())
    results = []

    for turn in turns:
        r = run_turn(session_id, turn, base_url)
        results.append(r)
        time.sleep(0.5)

    return results, session_id


# ─────────────────────────────────────────────
# CHECK FUNCTIONS
# ─────────────────────────────────────────────

def check_contains_any(text, targets):
    tl = text.lower()
    return any(t.lower() in tl for t in targets)


def check_not_contains(text, targets):
    tl = text.lower()
    return not any(t.lower() in tl for t in targets)


def check_contains_min(text, targets, min_count):
    tl = text.lower()
    return sum(1 for t in targets if t.lower() in tl) >= min_count


def check_tool_fired(tools_fired, tool_name):
    return tool_name in tools_fired


def run_programmatic_checks(checks, text, tools):
    passed = True
    details = []

    for chk in checks:
        t = chk["type"]

        if t == "contains_any":
            ok = check_contains_any(text, chk["targets"])
        elif t == "not_contains":
            ok = check_not_contains(text, chk["targets"])
        elif t == "contains_min":
            ok = check_contains_min(text, chk["targets"], chk.get("min_count", 1))
        elif t == "tool_fired":
            ok = check_tool_fired(tools, chk["tool_name"])
        else:
            ok = False

        status = "PASS" if ok else "FAIL"
        details.append(f"[{status}] {chk['description']}")

        if not ok:
            passed = False

    return passed, details


# ─────────────────────────────────────────────
# LLM JUDGE (UNCHANGED — already good)
# ─────────────────────────────────────────────

def run_llm_judge(turns, response, criteria):
    conversation = "\n".join(
        f"Turn {i+1}: {t}" for i, t in enumerate(turns)
    )

    resp = _judge_client.messages.create(
        model=JUDGE_MODEL,
        max_tokens=200,
        system="Return ONLY JSON: {'score':0/1,'explanation':'...'}",
        messages=[{
            "role": "user",
            "content": f"{conversation}\n\nResponse:\n{response}\n\nCriteria:\n{criteria}"
        }],
    )

    raw = resp.content[0].text.strip().replace("```json", "").replace("```", "")

    cost = (
        resp.usage.input_tokens * 0.80 / 1_000_000 +
        resp.usage.output_tokens * 4.00 / 1_000_000
    )

    try:
        parsed = json.loads(raw)
        return parsed.get("score", 0) == 1, parsed.get("explanation", ""), cost
    except:
        return False, "Judge parse error", cost


# ─────────────────────────────────────────────
# MAIN RUNNER
# ─────────────────────────────────────────────

def run_all(base_url):

    print(f"\nRunning {len(TEST_CASES)} evals...\n")

    results = []
    total_cost = 0
    passed_count = 0

    for tc in TEST_CASES:

        print(f"→ {tc['id']}")

        try:
            turn_results, _ = run_multiturn(tc["turns"], base_url)

            final = turn_results[-1]
            text = final["text"]

            tools = []
            for tr in turn_results:
                tools.extend(tr["tools_fired"])

            turn_cost = sum(tr["cost_usd"] for tr in turn_results)
            total_cost += turn_cost

            # ── CHECK TYPE ──
            if tc["check_method"] == "programmatic":
                passed, details = run_programmatic_checks(tc["checks"], text, tools)
            else:
                passed, explanation, judge_cost = run_llm_judge(
                    tc["turns"], text, tc["judge_criteria"]
                )
                details = [explanation]
                total_cost += judge_cost

            if passed:
                passed_count += 1

            print("   PASS" if passed else "   FAIL")

            results.append({
                "id": tc["id"],
                "passed": passed,
                "details": details,
                "preview": text[:200],
            })

        except Exception as e:
            print("   ERROR:", e)
            results.append({"id": tc["id"], "passed": False})

    print("\nFINAL SCORE:", passed_count, "/", len(TEST_CASES))
    print("TOTAL COST:", round(total_cost, 4))


# ─────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://localhost:8000")
    args = parser.parse_args()

    run_all(args.base_url)