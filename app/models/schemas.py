from pydantic import BaseModel, Field
from typing import Any
from datetime import datetime


class ChatRequest(BaseModel):
    session_id: str = Field(..., description="Unique session identifier")
    message   : str = Field(..., description="User message")


class ChunkInfo(BaseModel):
    text        : str
    source      : str
    doc_name    : str
    score       : float
    rerank_score: float = 0.0


class TurnTelemetry(BaseModel):
    session_id        : str
    turn_id           : str
    timestamp         : str
    model_used        : str
    retrieval_ms      : float
    rerank_ms         : float
    llm_ms            : float
    tool_ms           : float
    total_ms          : float
    ttft_ms           : float
    input_tokens      : int
    output_tokens     : int
    cost_usd          : float
    tools_called      : list[str]
    chunks_retrieved  : int
    chunks_after_rerank: int
    budget_exceeded   : bool


class MetricsResponse(BaseModel):
    total_turns        : int
    total_sessions     : int
    total_cost_usd     : float
    ttft_p50_ms        : float
    ttft_p95_ms        : float
    avg_cost_per_session: float
    avg_retrieval_ms   : float
    avg_llm_ms         : float
    most_used_tools    : list[str]
    status             : str
    generated_at       : str