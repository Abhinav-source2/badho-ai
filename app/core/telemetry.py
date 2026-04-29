import sqlite3
import json
import os
from datetime import datetime
from app.models.schemas import TurnTelemetry

DB_PATH = os.getenv("TELEMETRY_DB", "./telemetry.db")


def init_db() -> None:
    con = sqlite3.connect(DB_PATH)
    con.execute("""
        CREATE TABLE IF NOT EXISTS turns (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id          TEXT,
            turn_id             TEXT,
            timestamp           TEXT,
            model_used          TEXT,
            retrieval_ms        REAL,
            rerank_ms           REAL,
            llm_ms              REAL,
            tool_ms             REAL,
            total_ms            REAL,
            ttft_ms             REAL,
            input_tokens        INTEGER,
            output_tokens       INTEGER,
            cost_usd            REAL,
            tools_called        TEXT,
            chunks_retrieved    INTEGER,
            chunks_after_rerank INTEGER,
            budget_exceeded     INTEGER
        )
    """)
    con.commit()
    con.close()


def log_turn(t: TurnTelemetry) -> None:
    con = sqlite3.connect(DB_PATH)
    con.execute("""
        INSERT INTO turns VALUES (
            NULL,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?
        )
    """, (
        t.session_id, t.turn_id, t.timestamp, t.model_used,
        t.retrieval_ms, t.rerank_ms, t.llm_ms, t.tool_ms,
        t.total_ms, t.ttft_ms, t.input_tokens, t.output_tokens,
        t.cost_usd, json.dumps(t.tools_called),
        t.chunks_retrieved, t.chunks_after_rerank,
        int(t.budget_exceeded),
    ))
    con.commit()
    con.close()


def get_aggregate_stats() -> dict:
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()

    cur.execute("SELECT COUNT(*) FROM turns")
    total_turns = cur.fetchone()[0]

    cur.execute("SELECT COUNT(DISTINCT session_id) FROM turns")
    total_sessions = cur.fetchone()[0]

    cur.execute("SELECT COALESCE(SUM(cost_usd),0) FROM turns")
    total_cost = round(cur.fetchone()[0], 6)

    cur.execute("SELECT COALESCE(AVG(cost_usd),0) FROM turns")
    avg_cost_turn = cur.fetchone()[0] or 0

    avg_cost_session = round(
        total_cost / total_sessions if total_sessions else 0, 6
    )

    # p50 / p95 TTFT via SQLite percentile approximation
    cur.execute("SELECT ttft_ms FROM turns ORDER BY ttft_ms")
    ttfts = [r[0] for r in cur.fetchall()]

    def percentile(data, p):
        if not data:
            return 0.0
        idx = int(len(data) * p / 100)
        return round(data[min(idx, len(data)-1)], 2)

    ttft_p50 = percentile(ttfts, 50)
    ttft_p95 = percentile(ttfts, 95)

    cur.execute("SELECT COALESCE(AVG(retrieval_ms),0) FROM turns")
    avg_retrieval_ms = round(cur.fetchone()[0], 2)

    cur.execute("SELECT COALESCE(AVG(llm_ms),0) FROM turns")
    avg_llm_ms = round(cur.fetchone()[0], 2)

    # Most used tools
    cur.execute("SELECT tools_called FROM turns WHERE tools_called != '[]'")
    tool_counts: dict[str, int] = {}
    for (row,) in cur.fetchall():
        for tool in json.loads(row):
            tool_counts[tool] = tool_counts.get(tool, 0) + 1
    most_used = sorted(tool_counts, key=tool_counts.get, reverse=True)[:5]

    con.close()

    status = "healthy" if ttft_p95 < 1500 else "degraded"

    return {
        "total_turns"         : total_turns,
        "total_sessions"      : total_sessions,
        "total_cost_usd"      : total_cost,
        "ttft_p50_ms"         : ttft_p50,
        "ttft_p95_ms"         : ttft_p95,
        "avg_cost_per_session": avg_cost_session,
        "avg_retrieval_ms"    : avg_retrieval_ms,
        "avg_llm_ms"          : avg_llm_ms,
        "most_used_tools"     : most_used,
        "status"              : status,
        "generated_at"        : datetime.utcnow().isoformat(),
    }