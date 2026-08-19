"""
audit.py
--------
Append-only audit trail utilities. In this MVP the trail is persisted to
a CSV for portability/demo purposes; in production this would write to an
immutable store (e.g. append-only Delta table on Databricks with change
data feed enabled, or a WORM-compliant blob container).
"""

from __future__ import annotations
import pandas as pd
from datetime import datetime
import os

AUDIT_COLUMNS = ["audit_id", "timestamp", "user", "action", "entity_type", "entity_id", "details"]


def log_event(audit_path: str, user: str, action: str, entity_type: str, entity_id: str, details: str) -> pd.DataFrame:
    df = pd.read_csv(audit_path) if os.path.exists(audit_path) else pd.DataFrame(columns=AUDIT_COLUMNS)
    next_id = f"AUD-{5000 + len(df) + 1}"
    new_row = {
        "audit_id": next_id,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "user": user,
        "action": action,
        "entity_type": entity_type,
        "entity_id": entity_id,
        "details": details,
    }
    df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
    df.to_csv(audit_path, index=False)
    return df


def load_audit(audit_path: str) -> pd.DataFrame:
    if os.path.exists(audit_path):
        df = pd.read_csv(audit_path)
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        return df.sort_values("timestamp", ascending=False)
    return pd.DataFrame(columns=AUDIT_COLUMNS)
