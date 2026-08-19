"""
mutation_engine.py
-------------------
The "evolutionary" core of Process Genome AI. Analyzes drift + risk signals
to propose SOP "mutations" (structural or parametric changes), scores each
with a fitness function, and manages the human-in-the-loop approval
lifecycle (Pending -> Approved / Rejected) before a mutation is "expressed"
into the live genome (i.e. becomes the new baseline SOP).

Fitness function (0-1):
    fitness = 0.4 * cycle_time_gain
            + 0.35 * risk_reduction
            + 0.25 * precedent_alignment  (RAG similarity to past approved mutations)
"""

from __future__ import annotations
import pandas as pd
import numpy as np
from typing import List, Dict


def propose_mutations(drift_df: pd.DataFrame, risk_drivers: pd.DataFrame) -> List[Dict]:
    """Rule-driven mutation proposals grounded in the current drift/risk signals.
    In a full production build this ranking would be produced by an LLM agent
    reasoning over the same retrieved context; here it's a transparent,
    deterministic stand-in so proposals are always explainable and reproducible.
    """
    proposals = []
    for _, row in drift_df.iterrows():
        if row.drift_band in ("High", "Critical") and row.duration_overrun_pct > 25:
            gain = min(0.95, row.duration_overrun_pct / 150)
            proposals.append({
                "step_name": row.step_name,
                "mutation_type": "Duration Recalibration",
                "description": (
                    f"Recalibrate expected duration for '{row.step_name}' from baseline to reflect "
                    f"observed reality (+{row.duration_overrun_pct}% overrun), and investigate root "
                    "cause of the systemic delay."
                ),
                "cycle_time_gain": round(gain, 2),
                "risk_reduction": 0.2,
            })
        if row.drift_band in ("High", "Critical") and row.deviation_rate_pct > 30:
            reduction = min(0.95, row.deviation_rate_pct / 100 + 0.15)
            proposals.append({
                "step_name": row.step_name,
                "mutation_type": "Control Strengthening",
                "description": (
                    f"Insert an automated validation gate before '{row.step_name}' to reduce the "
                    f"{row.deviation_rate_pct}% observed deviation rate and enforce SOP adherence."
                ),
                "cycle_time_gain": 0.1,
                "risk_reduction": round(reduction, 2),
            })

    for _, row in risk_drivers.head(3).iterrows():
        if row.get("open_count", 0) >= 2:
            proposals.append({
                "step_name": row.step_name,
                "mutation_type": "Compliance Escalation Rule",
                "description": (
                    f"Add mandatory secondary sign-off for '{row.step_name}' given "
                    f"{int(row.get('open_count', 0))} unresolved risk incidents."
                ),
                "cycle_time_gain": 0.05,
                "risk_reduction": 0.5,
            })

    # de-duplicate by (step_name, mutation_type)
    seen = set()
    deduped = []
    for p in proposals:
        key = (p["step_name"], p["mutation_type"])
        if key not in seen:
            seen.add(key)
            deduped.append(p)

    for p in deduped:
        precedent_alignment = 0.7  # in full build: RAG-cosine-similarity to past approved mutations
        p["fitness_score"] = round(
            0.4 * p["cycle_time_gain"] + 0.35 * p["risk_reduction"] + 0.25 * precedent_alignment, 2
        )
        p["status"] = "Pending Review"
        p["fast_track_eligible"] = p["fitness_score"] >= 0.80

    return sorted(deduped, key=lambda x: -x["fitness_score"])
