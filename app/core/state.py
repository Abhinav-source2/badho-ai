import os
from anthropic import Anthropic

client    = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
MODEL     = os.getenv("PRIMARY_MODEL", "claude-3-5-haiku-20241022")
MAX_TURNS = 12  # summarize after this many messages

_sessions: dict[str, dict] = {}


def get_session(session_id: str) -> dict:
    if session_id not in _sessions:
        _sessions[session_id] = {
            "messages"     : [],
            "summary"      : "",
            "user_profile" : {},
            "budget_used"  : 0.0,
            "turn_count"   : 0,
        }
    return _sessions[session_id]


def add_message(session_id: str, role: str, content) -> None:
    get_session(session_id)["messages"].append(
        {"role": role, "content": content}
    )


def increment_cost(session_id: str, cost: float) -> None:
    get_session(session_id)["budget_used"] += cost


def get_messages(session_id: str) -> list:
    return get_session(session_id)["messages"]


def summarize_if_needed(session_id: str) -> None:
    session  = get_session(session_id)
    messages = session["messages"]

    if len(messages) <= MAX_TURNS:
        return

    to_summarize = messages[:-4]
    keep         = messages[-4:]

    history_text = "\n".join(
        f"{m['role'].upper()}: "
        f"{m['content'] if isinstance(m['content'], str) else '[tool content]'}"
        for m in to_summarize
    )

    summary_resp = client.messages.create(
        model      = MODEL,
        max_tokens = 300,
        messages   = [{
            "role"   : "user",
            "content": (
                f"Summarize this conversation in under 150 words, "
                f"keeping all important career facts:\n\n{history_text}"
            ),
        }],
    )
    summary_text = summary_resp.content[0].text

    session["summary"]  = summary_text
    session["messages"] = [
        {
            "role"   : "user",
            "content": f"[Earlier conversation summary]: {summary_text}",
        },
        {"role": "assistant", "content": "Understood."},
        *keep,
    ]

def extract_profile_facts(session_id: str, turn_text: str) -> None:
    """Extract career facts from user message and merge into user_profile."""
    session = get_session(session_id)

    try:
        resp = client.messages.create(
            model      = MODEL,
            max_tokens = 200,
            system     = (
                "Extract career facts from the user message. "
                "Respond ONLY with a JSON object. "
                "Keys (only include if mentioned): "
                "current_role, years_experience, target_role, "
                "location, skills, education. "
                "If nothing relevant, respond with {}."
            ),
            messages   = [{"role": "user", "content": turn_text}],
        )
        import json
        raw = resp.content[0].text.strip()
        # Strip markdown code fences if model adds them
        raw = raw.replace("```json", "").replace("```", "").strip()
        facts = json.loads(raw)
        session["user_profile"].update(
            {k: v for k, v in facts.items() if v}
        )
    except Exception:
        pass  # Never crash the main chat flow for profile extraction