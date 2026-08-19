"""
alerts.py
---------
Predictive alerting: projects near-term drift trajectory using simple
linear trend extrapolation over the rolling deviation-rate trend, and
raises alerts before a step crosses into a critical drift band -- the
"predictive" complement to the reactive drift_detection module.
"""

from __future__ import annotations
import numpy as np
import pandas as pd


def project_trend(trend_df: pd.DataFrame, periods_ahead: int = 4) -> pd.DataFrame:
    """Simple linear regression extrapolation of deviation rate."""
    if len(trend_df) < 2:
        return pd.DataFrame(columns=["timestamp", "deviation_rate_pct", "type"])

    x = np.arange(len(trend_df))
    y = trend_df["deviation_rate_pct"].values
    coeffs = np.polyfit(x, y, 1)
    slope, intercept = coeffs

    future_x = np.arange(len(trend_df), len(trend_df) + periods_ahead)
    future_y = np.clip(slope * future_x + intercept, 0, 100)

    freq = pd.infer_freq(trend_df["timestamp"]) or "W"
    last_ts = trend_df["timestamp"].iloc[-1]
    future_ts = pd.date_range(start=last_ts, periods=periods_ahead + 1, freq=freq)[1:]

    projected = pd.DataFrame({
        "timestamp": future_ts,
        "deviation_rate_pct": future_y,
        "type": "Projected",
    })
    historical = trend_df[["timestamp", "deviation_rate_pct"]].copy()
    historical["type"] = "Historical"
    return pd.concat([historical, projected], ignore_index=True), slope


def generate_predictive_alerts(drift_df: pd.DataFrame, trend_df: pd.DataFrame, slope: float) -> list:
    alerts = []

    # Trend-based alert
    if slope > 0.8:
        alerts.append({
            "severity": "High",
            "title": "Rising Drift Trajectory Detected",
            "message": (
                f"Deviation rate is trending upward at ~{slope:.2f} pts/period. "
                f"At this trajectory, the process may cross into 'Critical' drift territory within "
                f"{max(1, int((70 - trend_df['deviation_rate_pct'].iloc[-1]) / max(slope, 0.01)))} periods "
                "if left uncorrected."
            ),
            "recommended_action": "Schedule a proactive SOP review before the next audit cycle.",
        })
    elif slope > 0.3:
        alerts.append({
            "severity": "Medium",
            "title": "Moderate Upward Drift Trend",
            "message": f"Deviation rate trending up at ~{slope:.2f} pts/period. Monitor over the next 2 cycles.",
            "recommended_action": "Flag for inclusion in next process governance review.",
        })

    # Step-level threshold alerts
    near_critical = drift_df[(drift_df.drift_severity_index >= 45) & (drift_df.drift_severity_index < 60)]
    for _, row in near_critical.iterrows():
        alerts.append({
            "severity": "Medium",
            "title": f"Step Approaching Critical Drift: {row.step_name}",
            "message": f"Drift Severity Index is {row.drift_severity_index}/100, {row.deviation_rate_pct}% deviation rate.",
            "recommended_action": "Investigate root cause before it crosses the Critical (60+) threshold.",
        })

    critical = drift_df[drift_df.drift_severity_index >= 60]
    for _, row in critical.iterrows():
        alerts.append({
            "severity": "Critical",
            "title": f"Critical Drift Active: {row.step_name}",
            "message": f"Drift Severity Index is {row.drift_severity_index}/100 -- immediate attention required.",
            "recommended_action": "Trigger mandatory human review and consider interim manual control.",
        })

    return sorted(alerts, key=lambda a: {"Critical": 0, "High": 1, "Medium": 2, "Low": 3}[a["severity"]])
