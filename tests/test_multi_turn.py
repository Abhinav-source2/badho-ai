import httpx, json

BASE = "http://127.0.0.1:8000"
SID  = "multitest-001"

turns = [
    "I have 3 years of Python backend experience.",
    "I want to move into AI engineering.",
    "What skills am I missing based on what I told you?",
    "Which of those skills should I learn first?",
    "Can you give me a 30 day plan based on my background?",
]

for i, msg in enumerate(turns, 1):
    print(f"\n--- Turn {i} ---")
    print(f"User: {msg}")

    response = b""

    with httpx.stream(
        "POST",
        f"{BASE}/chat/stream",
        json={"session_id": SID, "message": msg},
        timeout=httpx.Timeout(120.0)
    ) as r:
        for chunk in r.iter_bytes():
            response += chunk

    # Extract streamed text
    text = ""
    for line in response.decode().split("\n"):
        if line.startswith("data: "):
            try:
                d = json.loads(line[6:])
                if "text" in d:
                    text += d["text"]
            except:
                pass

    print(f"AI: {text[:200]}...")

print("\nMulti-turn test complete.")