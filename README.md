# 🚀 Badho AI — Agentic Career Coach (Production-Grade)

> A **tool-using, RAG-powered, agentic AI system** for guiding engineers into AI careers — built from scratch with deterministic behavior, evaluation framework, and production safeguards.

---

## 🧠 What This Project Demonstrates

This is **not a chatbot**.

This is a **controlled AI system** that:

- Uses **RAG (Retrieval Augmented Generation)** for grounded answers
- Dynamically decides **when to call tools**
- Maintains **multi-turn conversation context**
- Enforces **deterministic outputs via evals (12/12 pass rate)**
- Implements **fallbacks, budget control, and telemetry**

---

## 🏗️ System Architecture


Frontend (HTML + JS, SSE Streaming)
│
▼
FastAPI Gateway (chat.py)
│
┌──────────┼───────────┐
│ │ │
▼ ▼ ▼
RAG Agent Loop Telemetry
Pipeline (llm.py) (SQLite)

│ │
▼ ▼
ChromaDB Tools Layer
(Vectors) ├─ lookup_role()
├─ estimate_salary_range()
├─ score_job_fit()
└─ generate_career_roadmap()


---

## ⚡ Key Features

### ✅ Agentic Tool System
- Model decides when to call tools
- Forced tool usage for structured outputs (roadmaps)
- Tool validation + fallback to reasoning

---

### ✅ RAG Pipeline
- Semantic retrieval (ChromaDB)
- Reranking
- Context injection into system prompt

---

### ✅ Multi-turn Memory (Fixed Properly)
- Conversation history maintained
- Context **reinforced into final query**
- Prevents model ignoring prior user info

---

### ✅ Streaming (SSE)
- Token-by-token response
- Tool events streamed live:
  - `tool_called`
  - `tool_done`

---

### ✅ Budget + Cost Control
- Tracks cost per session
- Hard cap enforcement

---

### ✅ Model Fallback System
- Primary: Claude Haiku (fast + cheap)
- Fallback: Claude Sonnet (robust)

---

### ✅ Deterministic Behavior (Evals)
- 12 structured test cases
- Covers:
  - factual correctness
  - reasoning
  - tool usage
  - adversarial inputs
  - multi-turn coherence

---

## 📊 FINAL RESULTS (Phase 3)


FINAL SCORE: 12 / 12 ✅
TOTAL COST: ~$0.005 per full eval run


### What This Means:

- No hallucinations in factual queries
- Tools trigger correctly
- Context is preserved across turns
- Adversarial prompts handled safely

---

## 🧪 Evaluation System (Major Highlight)

Custom eval framework:

### Types of Tests:
- Factual (programmatic)
- Reasoning (LLM-as-judge)
- Multi-turn memory
- Adversarial safety
- Tool triggering

---

### Example:

```python
{
  "id": "tool-02",
  "description": "Roadmap must trigger tool",
  "check": "generate_career_roadmap must fire"
}
🧠 Critical Engineering Decisions
❌ No LangChain / LlamaIndex

Everything built from scratch:

full control
debuggability
transparency
⚡ Model Choice
Model	Purpose
Claude Haiku	Fast, cheap inference
Claude Sonnet	Fallback reliability
🧩 Tool Design

Each tool:

returns structured JSON
validated before use
can fail gracefully
🧠 Agent Loop (Core Innovation)

The system:

Sends user input
Model decides:
answer directly OR
call tool
Executes tool
Feeds result back
Generates final answer
🔥 Critical Fixes (What Makes This System Strong)

These are NOT obvious — these show engineering depth:

1. Tool Reliability Fix

Problem:

Model sometimes skips tool

Solution:

Selective tool forcing for roadmap queries
2. API Error Fix

Problem:

tool_choice=None → API crash

Solution:

Dynamic request building (only pass when needed)
3. Multi-turn Context Fix (BIG ONE)

Problem:

Model ignores previous messages

Solution:

Inject context into last user message before inference
4. Source Citation Guarantee

Problem:

LLM sometimes skips citations

Solution:

Post-processing enforcement in chat layer
⚙️ Setup
git clone https://github.com/YOUR_USERNAME/badho-ai
cd badho-ai

python -m venv venv
.\venv\Scripts\activate

pip install -r requirements.txt

cp .env.example .env
# Add API keys

python ingest.py
uvicorn app.main:app --reload
🔑 Environment Variables
Variable	Description
ANTHROPIC_API_KEY	Claude API key
OPENAI_API_KEY	Embeddings
PRIMARY_MODEL	Default model
FALLBACK_MODEL	Backup model
MAX_BUDGET_USD	Cost cap
⚠️ Known Limitations
In-memory session (no persistence)
Static salary data
No auth layer
Tool execution is blocking
🚀 Future Improvements
Redis-based memory
Live salary APIs
Async tool streaming
Authentication system
🎯 Why This Project Stands Out

Most AI projects:

ChatGPT wrapper ❌

This project:

Agent system + tools + evals + reliability ✔
🧠 Interview Talking Point (IMPORTANT)

“I built an agentic AI system where the model dynamically decides tool usage, and I ensured deterministic behavior using a custom eval framework achieving 12/12 pass rate. I also solved real issues like tool unreliability and multi-turn context loss.”

📌 Tech Stack
FastAPI
Anthropic SDK
ChromaDB
Python
SSE Streaming
SQLite
👨‍💻 Author

Abhinav Jajoo

⭐ Final Note

This project focuses on:

Reliability > Flashy UI
Systems thinking > Prompt hacks
Engineering > Demos