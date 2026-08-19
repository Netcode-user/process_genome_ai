"""
drift_detection.py
-------------------
Detects "drift" between the baseline Process Genome (SOP as designed) and
what is actually happening on the ground (process execution logs).

Drift signals detected:
  1. Duration drift   - actual step duration significantly exceeds SOP baseline
  2. Frequency drift   - deviation types occurring above a statistical threshold
  3. Structural drift  - steps skipped or reordered relative to genome sequence
  4. Trend drift        - drift rate increasing over time (rolling window)

Each signal is scored into a 0-100 "Drift Severity Index" (DSI) per step,
which feeds the Risk Engine and Predictive Alerts modules.
"""

from __future__ import annotations
import pandas as pd
import numpy as np


def compute_step_drift(logs: pd.DataFrame, sop_master: pd.DataFrame) -> pd.DataFrame:
    """Aggregate per-step drift metrics against SOP baseline expectations."""
    merged = logs.merge(
        sop_master[["step_no", "expected_duration_min", "risk_level"]],
        on="step_no", suffixes=("", "_baseline")
    )
    grp = merged.groupby(["step_no", "step_name"]).agg(
        executions=("log_id", "count"),
        avg_actual_duration=("actual_duration_min", "mean"),
        expected_duration=("expected_duration_min", "first"),
        deviation_count=("deviation_flag", "sum"),
        risk_level=("risk_level", "first"),
    ).reset_index()

    grp["deviation_rate_pct"] = (grp.deviation_count / grp.executions * 100).round(1)
    grp["duration_overrun_pct"] = (
        (grp.avg_actual_duration - grp.expected_duration) / grp.expected_duration * 100
    ).round(1)

    risk_weight = {"Low": 0.6, "Medium": 1.0, "High": 1.5, "Critical": 2.0}
    grp["risk_weight"] = grp.risk_level.map(risk_weight).fillna(1.0)

    # Drift Severity Index (DSI): weighted composite 0-100
    dev_component = grp.deviation_rate_pct.clip(0, 100)
    dur_component = grp.duration_overrun_pct.clip(lower=0).clip(0, 150) / 1.5
    grp["drift_severity_index"] = (
        (0.55 * dev_component + 0.45 * dur_component) * grp.risk_weight
    ).clip(0, 100).round(1)

    def band(v):
        if v >= 60:
            return "Critical"
        if v >= 35:
            return "High"
        if v >= 15:
            return "Moderate"
        return "Stable"
    grp["drift_band"] = grp.drift_severity_index.apply(band)

    return grp.sort_values("drift_severity_index", ascending=False).reset_index(drop=True)


def compute_deviation_breakdown(logs: pd.DataFrame) -> pd.DataFrame:
    dev = logs[logs.deviation_flag == True]
    if dev.empty:
        return pd.DataFrame(columns=["deviation_type", "count", "pct"])
    counts = dev.deviation_type.value_counts().reset_index()
    counts.columns = ["deviation_type", "count"]
    counts["pct"] = (counts["count"] / counts["count"].sum() * 100).round(1)
    return counts


def compute_trend(logs: pd.DataFrame, freq: str = "W") -> pd.DataFrame:
    """Rolling drift-rate trend over time, used for predictive alerting."""
    df = logs.copy()
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df.set_index("timestamp")
    trend = df.resample(freq).agg(
        total_steps=("log_id", "count"),
        deviations=("deviation_flag", "sum"),
    )
    trend["deviation_rate_pct"] = (trend.deviations / trend.total_steps * 100).fillna(0).round(1)
    trend = trend.reset_index()
    return trend


def structural_diff(baseline_sequence: list, observed_case_steps: list) -> dict:
    """Compare an observed case's step order against the baseline genome order."""
    baseline_set = set(baseline_sequence)
    observed_set = set(observed_case_steps)
    skipped = sorted(baseline_set - observed_set)
    added = sorted(observed_set - baseline_set)

    # detect reordering among common steps
    common_baseline = [s for s in baseline_sequence if s in observed_set]
    common_observed = [s for s in observed_case_steps if s in baseline_set]
    reordered = common_baseline != common_observed

    return {
        "skipped_steps": skipped,
        "added_steps": added,
        "reordered": reordered,
        "baseline_order": common_baseline,
        "observed_order": common_observed,
    }
