# app/core/metrics.py

from collections import defaultdict
import numpy as np

# In-memory store (fine for demo)
_metrics = {
    "ttft_ms": [],
    "cost_usd": [],
    "requests": 0,
}


def record_metrics(ttft_ms: float, cost_usd: float):
    _metrics["requests"] += 1
    _metrics["ttft_ms"].append(ttft_ms)
    _metrics["cost_usd"].append(cost_usd)


def get_metrics():
    ttft = _metrics["ttft_ms"]
    cost = _metrics["cost_usd"]

    if not ttft:
        return {
            "total_requests": 0,
            "p50_ttft_ms": 0,
            "p95_ttft_ms": 0,
            "avg_cost_usd": 0,
            "total_cost_usd": 0,
        }

    return {
        "total_requests": _metrics["requests"],
        "p50_ttft_ms": round(float(np.percentile(ttft, 50)), 2),
        "p95_ttft_ms": round(float(np.percentile(ttft, 95)), 2),
        "avg_cost_usd": round(float(np.mean(cost)), 6),
        "total_cost_usd": round(float(np.sum(cost)), 6),
    }