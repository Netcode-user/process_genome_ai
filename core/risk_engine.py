"""
risk_engine.py
--------------
Combines drift signals, logged risk incidents, and step-level baseline risk
to produce a unified Process Risk Score, plus per-incident triage.
"""

from __future__ import annotations
import pandas as pd
import numpy as np


SEVERITY_WEIGHT = {"Low": 1, "Medium": 3, "High": 7, "Critical": 12}


def score_incidents(risk_incidents: pd.DataFrame) -> pd.DataFrame:
    df = risk_incidents.copy()
    df["severity_weight"] = df.severity.map(SEVERITY_WEIGHT).fillna(1)
    df["status"] = df.resolved.map(lambda r: "Resolved" if r else "Open")
    return df


def overall_process_risk_score(risk_incidents: pd.DataFrame, drift_df: pd.DataFrame) -> dict:
    """Blend incident severity + live drift severity into a single 0-100 score."""
    open_incidents = risk_incidents[~risk_incidents.resolved]
    incident_component = min(
        100, (open_incidents.severity.map(SEVERITY_WEIGHT).fillna(1).sum()) * 1.8
    ) if len(open_incidents) else 0

    drift_component = drift_df.drift_severity_index.mean() if len(drift_df) else 0

    composite = round(0.5 * incident_component + 0.5 * drift_component, 1)
    if composite >= 70:
        label, color = "Critical", "#dc2626"
    elif composite >= 45:
        label, color = "Elevated", "#f97316"
    elif composite >= 20:
        label, color = "Watch", "#eab308"
    else:
        label, color = "Healthy", "#22c55e"

    return {
        "composite_score": composite,
        "incident_component": round(incident_component, 1),
        "drift_component": round(drift_component, 1),
        "label": label,
        "color": color,
        "open_incidents": len(open_incidents),
    }


def top_risk_drivers(risk_incidents: pd.DataFrame, drift_df: pd.DataFrame, n: int = 5) -> pd.DataFrame:
    """Rank steps by combined incident count + drift severity -- the AI's 'why' behind the score."""
    inc_by_step = risk_incidents.groupby("step_name").agg(
        incident_count=("incident_id", "count"),
        open_count=("resolved", lambda s: (~s).sum()),
        max_severity=("severity", lambda s: s.map(SEVERITY_WEIGHT).max()),
    ).reset_index()

    merged = drift_df.merge(inc_by_step, on="step_name", how="left").fillna(
        {"incident_count": 0, "open_count": 0, "max_severity": 0}
    )
    merged["composite_driver_score"] = (
        merged.drift_severity_index * 0.6 + merged.incident_count * 6 + merged.open_count * 4
    ).round(1)
    return merged.sort_values("composite_driver_score", ascending=False).head(n)
