"""
data_loader.py
---------------
Central data access layer. Points at local CSVs for the MVP demo; in a
production Databricks deployment these loaders would instead read from
Delta tables (see the commented-out example below) with zero changes
needed in the rest of the app.
"""

from __future__ import annotations
import os
import pandas as pd
import streamlit as st

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")


@st.cache_data(ttl=60)
def load_sop_master() -> pd.DataFrame:
    return pd.read_csv(os.path.join(DATA_DIR, "sop_master.csv"))


@st.cache_data(ttl=60)
def load_process_logs() -> pd.DataFrame:
    return pd.read_csv(os.path.join(DATA_DIR, "process_execution_logs.csv"))


@st.cache_data(ttl=60)
def load_sop_versions() -> pd.DataFrame:
    return pd.read_csv(os.path.join(DATA_DIR, "sop_versions.csv"))


@st.cache_data(ttl=60)
def load_risk_incidents() -> pd.DataFrame:
    return pd.read_csv(os.path.join(DATA_DIR, "risk_incidents.csv"))


def audit_trail_path() -> str:
    return os.path.join(DATA_DIR, "audit_trail.csv")


# ---------------------------------------------------------------------------
# Databricks production wiring (reference only -- not executed in this MVP):
#
#   from databricks import sql
#   def load_process_logs():
#       conn = sql.connect(server_hostname=..., http_path=..., access_token=...)
#       return pd.read_sql("SELECT * FROM process_genome.process_execution_logs", conn)
#
# Swapping the CSV readers above for Delta/SQL reads is the only change
# required to move this MVP from demo mode to a live Databricks Lakehouse.
# ---------------------------------------------------------------------------
