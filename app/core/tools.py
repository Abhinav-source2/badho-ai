"""
Tool registry for Badho AI Career Coach.
All tools return plain dicts — the agentic loop serializes them to JSON.
"""

import json
import os
import time
from typing import Any

from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()

_client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
MODEL   = os.getenv("PRIMARY_MODEL", "claude-haiku-4-5-20251001")

# ── Salary dataset ─────────────────────────────────────────────────────────────
SALARY_DB: dict[str, dict] = {
    ("ai engineer",      "san francisco") : {"min": 160000, "mid": 210000, "max": 280000, "currency": "USD"},
    ("ai engineer",      "new york")      : {"min": 150000, "mid": 195000, "max": 265000, "currency": "USD"},
    ("ai engineer",      "remote us")     : {"min": 140000, "mid": 185000, "max": 250000, "currency": "USD"},
    ("ai engineer",      "bangalore")     : {"min": 2200000,"mid": 3500000,"max": 6000000,"currency": "INR"},
    ("ai engineer",      "hyderabad")     : {"min": 1800000,"mid": 3000000,"max": 5000000,"currency": "INR"},
    ("ai engineer",      "mumbai")        : {"min": 2000000,"mid": 3200000,"max": 5500000,"currency": "INR"},
    ("ml engineer",      "san francisco") : {"min": 150000, "mid": 195000, "max": 260000, "currency": "USD"},
    ("ml engineer",      "remote us")     : {"min": 130000, "mid": 175000, "max": 235000, "currency": "USD"},
    ("ml engineer",      "bangalore")     : {"min": 2000000,"mid": 3000000,"max": 5000000,"currency": "INR"},
    ("data scientist",   "san francisco") : {"min": 120000, "mid": 160000, "max": 220000, "currency": "USD"},
    ("data scientist",   "bangalore")     : {"min": 1200000,"mid": 2000000,"max": 3500000,"currency": "INR"},
    ("mlops engineer",   "san francisco") : {"min": 145000, "mid": 190000, "max": 255000, "currency": "USD"},
    ("mlops engineer",   "bangalore")     : {"min": 1800000,"mid": 2800000,"max": 4500000,"currency": "INR"},
    ("backend engineer", "san francisco") : {"min": 130000, "mid": 170000, "max": 230000, "currency": "USD"},
    ("backend engineer", "bangalore")     : {"min": 1000000,"mid": 1800000,"max": 3000000,"currency": "INR"},
}

YOE_MULTIPLIERS = {
    range(0, 2) : 0.80,
    range(2, 4) : 0.92,
    range(4, 7) : 1.00,
    range(7, 12): 1.20,
    range(12, 50): 1.40,
}


def _yoe_multiplier(years: int) -> float:
    for r, mult in YOE_MULTIPLIERS.items():
        if years in r:
            return mult
    return 1.0


# ── Tool schemas (Anthropic format) ───────────────────────────────────────────
TOOL_SCHEMAS = [
    {
        "name"       : "lookup_role",
        "description": (
            "Look up detailed information about a specific AI/tech role "
            "including responsibilities, required skills, and typical career path. "
            "Use when user asks about a specific job title or role."
        ),
        "input_schema": {
            "type"      : "object",
            "properties": {
                "role_name": {
                    "type"       : "string",
                    "description": "The job role to look up e.g. 'AI Engineer', 'ML Engineer', 'Data Scientist'",
                }
            },
            "required": ["role_name"],
        },
    },
    {
        "name"       : "estimate_salary_range",
        "description": (
            "Estimate salary range for a role based on location and years of experience. "
            "Use when user asks about compensation, salary, or pay for any tech role."
        ),
        "input_schema": {
            "type"      : "object",
            "properties": {
                "role"               : {"type": "string", "description": "Job role e.g. 'AI Engineer'"},
                "location"           : {"type": "string", "description": "City or region e.g. 'Bangalore', 'San Francisco', 'Remote US'"},
                "years_of_experience": {"type": "integer", "description": "Years of total work experience"},
            },
            "required": ["role", "location", "years_of_experience"],
        },
    },
    {
        "name"       : "score_job_fit",
        "description": (
            "Score how well the user's background fits a target role or job description. "
            "Returns a structured fit score with strengths and gaps. "
            "Use when user wants to know if they are a good fit for a role."
        ),
        "input_schema": {
            "type"      : "object",
            "properties": {
                "user_background"  : {"type": "string", "description": "Summary of user's current skills and experience"},
                "target_role"      : {"type": "string", "description": "The role they want to move into"},
                "job_description"  : {"type": "string", "description": "Optional JD details if provided by user", "default": ""},
            },
            "required": ["user_background", "target_role"],
        },
    },
    {
        "name"       : "generate_career_roadmap",
        "description": (
            "Generate a structured 30/60/90 day career roadmap for transitioning "
            "from current role to target role. Use when user asks for a plan, "
            "roadmap, or step-by-step guide."
        ),
        "input_schema": {
            "type"      : "object",
            "properties": {
                "current_role"     : {"type": "string", "description": "User's current job role"},
                "target_role"      : {"type": "string", "description": "Role they want to reach"},
                "timeline_months"  : {"type": "integer", "description": "How many months they have (default 3)", "default": 3},
                "current_skills"   : {"type": "string", "description": "Brief summary of existing skills"},
            },
            "required": ["current_role", "target_role"],
        },
    },
]


# ── Tool implementations ───────────────────────────────────────────────────────

def lookup_role(role_name: str) -> dict[str, Any]:
    """RAG-backed role lookup from corpus."""
    from app.core.rag import retrieve_and_rerank

    result = retrieve_and_rerank(
        query          = f"{role_name} job responsibilities skills requirements",
        top_k_retrieve = 8,
        top_k_rerank   = 3,
    )

    chunks = result["chunks"]
    if not chunks:
        return {"role": role_name, "info": "No specific information found.", "sources": []}

    combined = "\n\n".join(c["text"] for c in chunks)
    sources  = list({c["doc_name"] for c in chunks})

    return {
        "role"       : role_name,
        "description": combined[:1500],
        "sources"    : sources,
    }


def estimate_salary_range(
    role: str,
    location: str,
    years_of_experience: int,
) -> dict[str, Any]:
    key = (role.lower().strip(), location.lower().strip())

    # Exact match first
    if key in SALARY_DB:
        base = SALARY_DB[key]
    else:
        # Fuzzy match on role
        matched = None
        for (r, l), v in SALARY_DB.items():
            if r in role.lower() and l in location.lower():
                matched = v
                break
        if not matched:
            # Default to AI Engineer Bangalore as fallback
            matched = SALARY_DB[("ai engineer", "bangalore")]
        base = matched

    mult     = _yoe_multiplier(years_of_experience)
    currency = base["currency"]
    divisor  = 100000 if currency == "INR" else 1000

    return {
        "role"               : role,
        "location"           : location,
        "years_of_experience": years_of_experience,
        "min"                : round(base["min"] * mult / divisor) * divisor,
        "mid"                : round(base["mid"] * mult / divisor) * divisor,
        "max"                : round(base["max"] * mult / divisor) * divisor,
        "currency"           : currency,
        "source"             : "internal_salary_db_2024",
        "note"               : f"Adjusted {int((mult-1)*100):+d}% for {years_of_experience} YoE" if mult != 1.0 else "Base range for this experience band",
    }


def score_job_fit(
    user_background: str,
    target_role: str,
    job_description: str = "",
) -> dict[str, Any]:
    """LLM-powered structured fit scoring."""
    jd_section = f"\nJob Description:\n{job_description}" if job_description else ""

    resp = _client.messages.create(
        model      = MODEL,
        max_tokens = 500,
        system     = (
            "You are a career assessment expert. Respond ONLY with a valid JSON object. "
            "No markdown, no explanation, just the JSON."
        ),
        messages   = [{
            "role"   : "user",
            "content": (
                f"Assess this candidate's fit for the target role.\n\n"
                f"Candidate Background:\n{user_background}\n\n"
                f"Target Role: {target_role}{jd_section}\n\n"
                f"Respond with exactly this JSON structure:\n"
                f'{{"overall_fit": <int 0-100>, '
                f'"strengths": [<str>, ...], '
                f'"gaps": [<str>, ...], '
                f'"recommendation": "<one sentence>", '
                f'"confidence": "high|medium|low"}}'
            ),
        }],
    )

    raw = resp.content[0].text.strip()
    raw = raw.replace("```json", "").replace("```", "").strip()

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {
            "overall_fit"    : 0,
            "strengths"      : [],
            "gaps"           : ["Could not parse response"],
            "recommendation" : "Please try again with more detail.",
            "confidence"     : "low",
        }


def generate_career_roadmap(
    current_role: str,
    target_role: str,
    timeline_months: int = 3,
    current_skills: str = "",
) -> dict[str, Any]:
    """LLM-powered structured career roadmap."""
    skills_section = f"\nCurrent Skills: {current_skills}" if current_skills else ""

    resp = _client.messages.create(
        model      = MODEL,
        max_tokens = 800,
        system     = (
            "You are a career coach creating actionable plans. "
            "Respond ONLY with a valid JSON object. No markdown."
        ),
        messages   = [{
            "role"   : "user",
            "content": (
                f"Create a {timeline_months}-month career roadmap.\n"
                f"From: {current_role}\n"
                f"To: {target_role}{skills_section}\n\n"
                f"Respond with exactly this JSON structure:\n"
                f'{{"day_30": {{"goals": [<str>], "actions": [<str>]}}, '
                f'"day_60": {{"goals": [<str>], "actions": [<str>]}}, '
                f'"day_90": {{"goals": [<str>], "actions": [<str>]}}, '
                f'"key_milestones": [<str>], '
                f'"recommended_resources": [<str>]}}'
            ),
        }],
    )

    raw = resp.content[0].text.strip()
    raw = raw.replace("```json", "").replace("```", "").strip()

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {
            "day_30"               : {"goals": ["Parse error"], "actions": []},
            "day_60"               : {"goals": [], "actions": []},
            "day_90"               : {"goals": [], "actions": []},
            "key_milestones"       : [],
            "recommended_resources": [],
        }


# ── Tool executor ──────────────────────────────────────────────────────────────
TOOL_MAP = {
    "lookup_role"           : lookup_role,
    "estimate_salary_range" : estimate_salary_range,
    "score_job_fit"         : score_job_fit,
    "generate_career_roadmap": generate_career_roadmap,
}


def execute_tool(tool_name: str, tool_input: dict) -> tuple[Any, float]:
    """
    Execute a tool by name. Returns (result_dict, latency_ms).
    Never raises — wraps errors in result dict.
    """
    t0  = time.perf_counter()
    fn  = TOOL_MAP.get(tool_name)

    if not fn:
        result = {"error": f"Unknown tool: {tool_name}"}
    else:
        try:
            result = fn(**tool_input)
        except Exception as e:
            result = {"error": str(e)}

    ms = round((time.perf_counter() - t0) * 1000, 2)
    return result, ms