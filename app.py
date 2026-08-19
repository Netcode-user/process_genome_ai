""" 
Process Genome AI 
EXL Enterprise Process Intelligence & Dynamic SOP Governance 
Streamlit MVP - Enhanced Interactive Enterprise Edition 

Features 
-------- 
- Enterprise dashboard 
- Process Genome Explorer 
- 3D process landscape 
- AI SOP Generator 
- RAG-based Process Genome Q&A 
- SOP drift detection 
- Risk & explainability 
- Human-in-the-loop mutation approval 
- Real-time process simulation 
- Dynamic predictive alerts 
- Process/genome comparison 
- Training generator 
- Audit trail 
- Online / Offline LLM indicator 
- Interactive orange / purple / teal enterprise UI 
"""
import os

from dotenv import load_dotenv

load_dotenv()
import random
import textwrap
from datetime import datetime, timedelta

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from core.alerts import generate_predictive_alerts, project_trend
from core.audit import load_audit, log_event
from core.drift_detection import (compute_deviation_breakdown,
                                  compute_step_drift, compute_trend,
                                  structural_diff)
from core.explainability import explain_drift_row, explain_mutation
from core.genome import ProcessGenome
from core.mutation_engine import propose_mutations
from core.rag_engine import RAGEngine
from core.risk_engine import (overall_process_risk_score, score_incidents,
                              top_risk_drivers)
from core.training_generator import generate_quiz, generate_training_deck
from utils.data_loader import (audit_trail_path, load_process_logs,
                               load_risk_incidents, load_sop_master,
                               load_sop_versions)

# =============================================================================
# PAGE CONFIG
# =============================================================================

st.set_page_config(
    page_title="Process Genome AI | EXL Enterprise Intelligence",
    page_icon="🧬",
    layout="wide",
    initial_sidebar_state="expanded",
)


# =============================================================================
# BRAND COLORS
# =============================================================================

PRIMARY = "#14B8A6"
PRIMARY_DARK = "#0F766E"

PURPLE = "#8B5CF6"
PURPLE_DARK = "#6D28D9"

BLUE = "#2563EB"
PINK = "#EC4899"

ORANGE = "#F97316"
ORANGE_LIGHT = "#FB923C"

GREEN = "#22C55E"
RED = "#EF4444"
YELLOW = "#EAB308"

BG = "#050816"
CARD = "#0B1424"
CARD_2 = "#101B2E"
BORDER = "#26364D"

TEXT = "#F8FAFC"
MUTED = "#94A3B8"


# =============================================================================
# DEMO DATA GENERATOR
# =============================================================================

def get_demo_values(sop_name: str) -> dict:
    """
    Return deterministic demo metrics for a given SOP name so the UI
    shows unique, industry-oriented values when the user selects different SOPs.
    """
    if not sop_name:
        sop_name = "Loan Underwriting SOP"

    seed = sum(ord(c) for c in sop_name)
    r = random.Random(seed)

    annual_savings = round(1.5 + r.random() * 4.5, 2)  # millions
    processes_monitored = 700 + r.randint(0, 400)
    compliance = 82 + r.randint(0, 18)
    high_risk = r.randint(5, 30)
    ai_applied = 50 + r.randint(0, 40)

    process_risk_score = round(40 + r.random() * 40, 1)
    active_sop_genes = 8 + r.randint(0, 20)
    executions_logged = 1000 + r.randint(0, 10000)
    open_incidents = r.randint(0, 120)
    critical_steps = r.randint(0, 6)

    drift_pct = round(5 + r.random() * 25, 1)
    drift_slope = round(-0.5 + r.random() * 1.5, 2)

    skipped_steps = r.randint(0, 4)
    unexpected_steps = r.randint(0, 4)
    reordered = "Yes" if r.random() > 0.8 else "No"

    return {
        "annual_savings_m": annual_savings,
        "processes_monitored": processes_monitored,
        "compliance_pct": compliance,
        "high_risk_processes": high_risk,
        "ai_applied_pct": ai_applied,
        "process_risk_score": process_risk_score,
        "active_sop_genes": active_sop_genes,
        "executions_logged": executions_logged,
        "open_incidents": open_incidents,
        "critical_steps": critical_steps,
        "drift_pct": drift_pct,
        "drift_slope": drift_slope,
        "skipped_steps": skipped_steps,
        "unexpected_steps": unexpected_steps,
        "reordered": reordered,
    }


def get_selected_template_name() -> str:
    return st.session_state.get("selected_template", "Loan Underwriting SOP")


def apply_template_impact_to_trend(trend_df):
    """Adjust the trend so each SOP produces a unique predictive forecast."""
    if trend_df is None or trend_df.empty:
        return trend_df

    df = trend_df.copy()
    if "deviation_rate_pct" not in df.columns:
        return df

    template_values = get_demo_values(get_selected_template_name())
    drift_bias = template_values["drift_pct"] / 8.0
    slope_bias = template_values["drift_slope"] * 1.5

    rates = pd.to_numeric(df["deviation_rate_pct"], errors="coerce").fillna(0)
    seq = pd.Series(range(len(rates)), index=df.index)
    adjusted = rates + drift_bias + slope_bias * (seq / max(1, len(rates) - 1))
    df["deviation_rate_pct"] = adjusted.round(2)
    return df


# =============================================================================
# SAFE HTML RENDERER
# =============================================================================

def render_html(html: str):
    """
    Render custom HTML safely.
    Uses st.html where available and markdown fallback otherwise.
    """

    html = textwrap.dedent(html).strip()

    try:
        st.html(html)
    except Exception:
        st.markdown(
            html,
            unsafe_allow_html=True,
        )


# =============================================================================
# GLOBAL CSS
# =============================================================================

CUSTOM_CSS = f"""
<style>

/* ============================================================
   GLOBAL APPLICATION
   ============================================================ */

.stApp {{
    background:
        radial-gradient(
            circle at 8% 12%,
            rgba(249,115,22,0.18),
            transparent 28%
        ),
        radial-gradient(
            circle at 88% 15%,
            rgba(139,92,246,0.18),
            transparent 28%
        ),
        radial-gradient(
            circle at 50% 92%,
            rgba(20,184,166,0.15),
            transparent 30%
        ),
        linear-gradient(
            135deg,
            #030712 0%,
            #07101e 35%,
            #0b1020 65%,
            #100b18 100%
        );
    color: {TEXT};
    min-height: 100vh;
}}


/* ============================================================
   ANIMATED BACKGROUND
   ============================================================ */

.stApp::before {{
    content: "";
    position: fixed;
    inset: 0;
    pointer-events: none;
    z-index: 0;

    background:
        linear-gradient(
            120deg,
            rgba(249,115,22,0.05),
            rgba(139,92,246,0.05),
            rgba(20,184,166,0.05),
            rgba(249,115,22,0.05)
        );

    background-size: 300% 300%;

    animation:
        enterpriseGradient 18s ease infinite;
}}

@keyframes enterpriseGradient {{
    0% {{
        background-position: 0% 50%;
    }}

    50% {{
        background-position: 100% 50%;
    }}

    100% {{
        background-position: 0% 50%;
    }}
}}


/* ============================================================
   MAIN CONTENT
   ============================================================ */

.main .block-container {{
    position: relative;
    z-index: 2;

    padding-top: 1.2rem;
    padding-bottom: 3rem;
    max-width: 1550px;
}}


/* ============================================================
   SIDEBAR
   ============================================================ */

section[data-testid="stSidebar"] {{
    background:
        linear-gradient(
            180deg,
            rgba(7,13,27,0.98),
            rgba(10,16,31,0.98)
        );

    border-right:
        1px solid
        rgba(139,92,246,0.25);

    box-shadow:
        10px 0 40px rgba(0,0,0,0.35);
}}


/* ============================================================
   SIDEBAR NAVIGATION
   ============================================================ */

section[data-testid="stSidebar"] .stRadio label {{
    color: #CBD5E1 !important;
    font-weight: 650;
    padding: 7px 4px;
    border-radius: 10px;
}}

section[data-testid="stSidebar"] .stRadio label:hover {{
    background:
        linear-gradient(
            90deg,
            rgba(249,115,22,0.15),
            rgba(139,92,246,0.12)
        );
    color: white !important;
}}


/* ============================================================
   HERO
   ============================================================ */

.hero-card {{
    position: relative;
    overflow: hidden;

    padding: 38px;

    border-radius: 26px;

    background:
        linear-gradient(
            135deg,
            rgba(20,184,166,0.14),
            rgba(139,92,246,0.16),
            rgba(249,115,22,0.14)
        );

    border:
        1px solid
        rgba(255,255,255,0.12);

    box-shadow:
        0 30px 80px rgba(0,0,0,0.42),
        inset 0 1px 0 rgba(255,255,255,0.08);

    backdrop-filter: blur(20px);

    transform: translateZ(0);
}}

.hero-card::before {{
    content: "";
    position: absolute;

    width: 260px;
    height: 260px;

    right: -80px;
    top: -100px;

    background:
        radial-gradient(
            circle,
            rgba(249,115,22,0.45),
            transparent 70%
        );

    filter: blur(10px);
}}

.hero-brand {{
    position: relative;

    color: #5EEAD4;
    font-size: 11px;
    font-weight: 900;

    letter-spacing: 2px;

    margin-bottom: 10px;
}}

.hero-title {{
    position: relative;

    font-size: clamp(38px, 5vw, 70px);
    line-height: 1;

    font-weight: 950;

    background:
        linear-gradient(
            90deg,
            #5EEAD4,
            #C4B5FD,
            #FDBA74
        );

    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;

    margin-bottom: 18px;
}}

.hero-subtitle {{
    position: relative;

    max-width: 900px;

    color: #CBD5E1;
    font-size: 15px;
    line-height: 1.8;
}}

.hero-metrics {{
    position: relative;

    display: flex;
    flex-wrap: wrap;

    gap: 10px;

    margin-top: 26px;
}}

.hero-chip {{
    padding: 8px 13px;

    border-radius: 999px;

    font-size: 10px;
    font-weight: 900;

    letter-spacing: .6px;

    border: 1px solid rgba(255,255,255,.12);

    background: rgba(0,0,0,.25);

    box-shadow:
        inset 0 1px 0 rgba(255,255,255,.08),
        0 8px 25px rgba(0,0,0,.18);
}}

.chip-teal {{
    color: #5EEAD4;
}}

.chip-purple {{
    color: #C4B5FD;
}}

.chip-orange {{
    color: #FDBA74;
}}

.chip-pink {{
    color: #F9A8D4;
}}

.chip-blue {{
    color: #93C5FD;
}}


/* ============================================================
   CARDS
   ============================================================ */

.executive-card {{
    min-height: 180px;

    padding: 22px;

    border-radius: 20px;

    background:
        linear-gradient(
            145deg,
            rgba(15,23,42,.92),
            rgba(11,20,36,.80)
        );

    border:
        1px solid rgba(255,255,255,.08);

    box-shadow:
        0 18px 40px rgba(0,0,0,.30),
        inset 0 1px 0 rgba(255,255,255,.05);

    transition:
        transform .25s ease,
        box-shadow .25s ease;
}}

.executive-card:hover {{
    transform:
        translateY(-6px)
        scale(1.01);

    box-shadow:
        0 28px 60px rgba(0,0,0,.40);
}}

.executive-card.teal {{
    border-top:
        3px solid {PRIMARY};
}}

.executive-card.purple {{
    border-top:
        3px solid {PURPLE};
}}

.executive-card.pink {{
    border-top:
        3px solid {PINK};
}}

.executive-icon {{
    font-size: 30px;
    margin-bottom: 10px;
}}

.executive-title {{
    font-size: 16px;
    font-weight: 850;
    color: white;
}}

.executive-text {{
    margin-top: 10px;
    color: #94A3B8;
    line-height: 1.65;
    font-size: 13px;
}}


/* ============================================================
   GENOME CARD
   ============================================================ */

.genome-card {{
    position: relative;

    overflow: hidden;

    padding: 28px;

    margin: 10px 0 25px;

    border-radius: 22px;

    background:
        linear-gradient(
            135deg,
            rgba(20,184,166,.12),
            rgba(139,92,246,.10),
            rgba(249,115,22,.08)
        );

    border:
        1px solid
        rgba(255,255,255,.10);

    box-shadow:
        0 20px 55px rgba(0,0,0,.35);
}}

.dna-sequence {{
    display: flex;
    flex-wrap: wrap;

    gap: 5px;

    margin: 25px 0;

    font-size: 20px;
    font-weight: 900;
    letter-spacing: 3px;
}}

.base-A,
.base-T,
.base-G,
.base-C {{
    display: inline-flex;

    align-items: center;
    justify-content: center;

    width: 32px;
    height: 32px;

    border-radius: 9px;

    background: rgba(0,0,0,.35);

    box-shadow:
        inset 0 1px 0 rgba(255,255,255,.1),
        0 5px 15px rgba(0,0,0,.25);
}}

.base-A {{
    color: #FB923C;
    border: 1px solid rgba(251,146,60,.35);
}}

.base-T {{
    color: #EAB308;
    border: 1px solid rgba(234,179,8,.35);
}}

.base-G {{
    color: #22C55E;
    border: 1px solid rgba(34,197,94,.35);
}}

.base-C {{
    color: #EF4444;
    border: 1px solid rgba(239,68,68,.35);
}}


/* ============================================================
   STATUS BADGES
   ============================================================ */

.approval-approved,
.approval-rejected,
.approval-pending {{
    padding: 13px 16px;

    border-radius: 14px;

    margin: 10px 0;

    font-size: 12px;
    font-weight: 850;

    letter-spacing: .4px;
}}

.approval-approved {{
    color: #BBF7D0;

    background:
        linear-gradient(
            90deg,
            rgba(34,197,94,.15),
            rgba(20,184,166,.08)
        );

    border:
        1px solid rgba(34,197,94,.35);
}}

.approval-rejected {{
    color: #FECACA;

    background:
        rgba(239,68,68,.10);

    border:
        1px solid rgba(239,68,68,.30);
}}

.approval-pending {{
    color: #FED7AA;

    background:
        rgba(249,115,22,.10);

    border:
        1px solid rgba(249,115,22,.30);
}}


/* ============================================================
   METRICS
   ============================================================ */

div[data-testid="stMetric"] {{
    background:
        linear-gradient(
            145deg,
            rgba(15,23,42,.82),
            rgba(11,20,36,.70)
        );

    border:
        1px solid rgba(255,255,255,.07);

    padding: 15px;

    border-radius: 16px;

    box-shadow:
        0 12px 30px rgba(0,0,0,.20);
}}

div[data-testid="stMetricLabel"] {{
    color: #94A3B8 !important;
}}

div[data-testid="stMetricValue"] {{
    color: #F8FAFC !important;
    font-weight: 850;
}}


/* ============================================================
   BUTTONS
   ============================================================ */

.stButton > button {{
    border-radius: 12px;

    border:
        1px solid rgba(255,255,255,.12);

    background:
        linear-gradient(
            135deg,
            rgba(20,184,166,.20),
            rgba(139,92,246,.20)
        );

    color: white;

    font-weight: 800;

    transition:
        all .2s ease;

    box-shadow:
        0 8px 20px rgba(0,0,0,.22);
}}

.stButton > button:hover {{
    transform:
        translateY(-2px);

    border-color:
        rgba(249,115,22,.55);

    box-shadow:
        0 12px 30px rgba(249,115,22,.16);
}}


/* ============================================================
   INPUTS
   ============================================================ */

.stTextInput input,
.stTextArea textarea,
.stSelectbox div,
.stMultiSelect div {{
    background-color:
        rgba(7,13,27,.78) !important;

    border-radius: 12px !important;

    border:
        1px solid rgba(255,255,255,.10) !important;

    color: white !important;
}}


/* ============================================================
   EXPANDERS
   ============================================================ */

.streamlit-expanderHeader {{
    background:
        rgba(15,23,42,.60) !important;

    border-radius: 12px !important;

    color: #E2E8F0 !important;
}}


/* ============================================================
   TABLES
   ============================================================ */

[data-testid="stDataFrame"] {{
    border-radius: 14px;
    overflow: hidden;

    box-shadow:
        0 15px 35px rgba(0,0,0,.22);
}}


/* ============================================================
   SECTION LABEL
   ============================================================ */

.section-label {{
    margin-top: 24px;

    color: #64748B;

    font-size: 10px;
    font-weight: 900;

    letter-spacing: 2px;
}}


/* ============================================================
   SCROLLBAR
   ============================================================ */

::-webkit-scrollbar {{
    width: 8px;
}}

::-webkit-scrollbar-track {{
    background: #050816;
}}

::-webkit-scrollbar-thumb {{
    background:
        linear-gradient(
            #14B8A6,
            #8B5CF6,
            #F97316
        );

    border-radius: 10px;
}}

</style>
"""

render_html(CUSTOM_CSS)


# =============================================================================
# CONSTANTS
# =============================================================================

INDUSTRY_TEMPLATES = {
    "Banking": [
        "Loan Underwriting SOP",
        "Customer Onboarding SOP",
        "KYC Validation SOP",
    ],
    "Insurance": [
        "Claims Processing SOP",
        "Fraud Review SOP",
        "Policy Servicing SOP",
    ],
    "Healthcare": [
        "Prior Authorization SOP",
        "Claims Adjudication SOP",
        "Member Support SOP",
    ],
    "Finance & Accounting": [
        "Invoice Processing SOP",
        "Accounts Payable SOP",
        "Reconciliation SOP",
    ],
    "Supply Chain": [
        "Procurement SOP",
        "Vendor Management SOP",
        "Inventory Control SOP",
    ],
}

TEMPLATE_METADATA = {
    "Loan Underwriting SOP": {
        "industry": "Banking",
        "title": "Loan Underwriting",
        "sop_id": "SOP-LU-001",
        "version": "v3.2",
        "embeddings": "sentence-transformers(all-MiniLM-L6-v2, local)",
        "vector_store": "FAISS (IndexFlatL2)",
        "llm_detail": "Anthropic Claude",
    },
    "Customer Onboarding SOP": {
        "industry": "Banking",
        "title": "Customer Onboarding",
        "sop_id": "SOP-CO-002",
        "version": "v2.7",
        "embeddings": "sentence-transformers(all-MiniLM-L6-v2, local)",
        "vector_store": "FAISS (IndexFlatL2)",
        "llm_detail": "Anthropic Claude",
    },
    "KYC Validation SOP": {
        "industry": "Banking",
        "title": "KYC Validation",
        "sop_id": "SOP-KYC-003",
        "version": "v2.9",
        "embeddings": "sentence-transformers(all-MiniLM-L6-v2, local)",
        "vector_store": "FAISS (IndexFlatL2)",
        "llm_detail": "Anthropic Claude",
    },
    "Claims Processing SOP": {
        "industry": "Insurance",
        "title": "Claims Processing",
        "sop_id": "SOP-CP-011",
        "version": "v3.1",
        "embeddings": "sentence-transformers(all-MiniLM-L6-v2, local)",
        "vector_store": "FAISS (IndexFlatL2)",
        "llm_detail": "Anthropic Claude",
    },
    "Fraud Review SOP": {
        "industry": "Insurance",
        "title": "Fraud Review",
        "sop_id": "SOP-FR-014",
        "version": "v2.8",
        "embeddings": "sentence-transformers(all-MiniLM-L6-v2, local)",
        "vector_store": "FAISS (IndexFlatL2)",
        "llm_detail": "Anthropic Claude",
    },
    "Policy Servicing SOP": {
        "industry": "Insurance",
        "title": "Policy Servicing",
        "sop_id": "SOP-PS-018",
        "version": "v3.0",
        "embeddings": "sentence-transformers(all-MiniLM-L6-v2, local)",
        "vector_store": "FAISS (IndexFlatL2)",
        "llm_detail": "Anthropic Claude",
    },
    "Prior Authorization SOP": {
        "industry": "Healthcare",
        "title": "Prior Authorization",
        "sop_id": "SOP-PA-021",
        "version": "v2.6",
        "embeddings": "sentence-transformers(all-MiniLM-L6-v2, local)",
        "vector_store": "FAISS (IndexFlatL2)",
        "llm_detail": "Anthropic Claude",
    },
    "Claims Adjudication SOP": {
        "industry": "Healthcare",
        "title": "Claims Adjudication",
        "sop_id": "SOP-CA-023",
        "version": "v3.3",
        "embeddings": "sentence-transformers(all-MiniLM-L6-v2, local)",
        "vector_store": "FAISS (IndexFlatL2)",
        "llm_detail": "Anthropic Claude",
    },
    "Member Support SOP": {
        "industry": "Healthcare",
        "title": "Member Support",
        "sop_id": "SOP-MS-027",
        "version": "v3.2",
        "embeddings": "sentence-transformers(all-MiniLM-L6-v2, local)",
        "vector_store": "FAISS (IndexFlatL2)",
        "llm_detail": "Anthropic Claude",
    },
    "Invoice Processing SOP": {
        "industry": "Finance & Accounting",
        "title": "Invoice Processing",
        "sop_id": "SOP-IP-031",
        "version": "v3.2",
        "embeddings": "sentence-transformers(all-MiniLM-L6-v2, local)",
        "vector_store": "FAISS (IndexFlatL2)",
        "llm_detail": "Anthropic Claude",
    },
    "Accounts Payable SOP": {
        "industry": "Finance & Accounting",
        "title": "Accounts Payable",
        "sop_id": "SOP-AP-033",
        "version": "v2.9",
        "embeddings": "sentence-transformers(all-MiniLM-L6-v2, local)",
        "vector_store": "FAISS (IndexFlatL2)",
        "llm_detail": "Anthropic Claude",
    },
    "Reconciliation SOP": {
        "industry": "Finance & Accounting",
        "title": "Reconciliation",
        "sop_id": "SOP-RC-036",
        "version": "v3.0",
        "embeddings": "sentence-transformers(all-MiniLM-L6-v2, local)",
        "vector_store": "FAISS (IndexFlatL2)",
        "llm_detail": "Anthropic Claude",
    },
    "Procurement SOP": {
        "industry": "Supply Chain",
        "title": "Procurement",
        "sop_id": "SOP-PC-041",
        "version": "v3.1",
        "embeddings": "sentence-transformers(all-MiniLM-L6-v2, local)",
        "vector_store": "FAISS (IndexFlatL2)",
        "llm_detail": "Anthropic Claude",
    },
    "Vendor Management SOP": {
        "industry": "Supply Chain",
        "title": "Vendor Management",
        "sop_id": "SOP-VM-044",
        "version": "v2.8",
        "embeddings": "sentence-transformers(all-MiniLM-L6-v2, local)",
        "vector_store": "FAISS (IndexFlatL2)",
        "llm_detail": "Anthropic Claude",
    },
    "Inventory Control SOP": {
        "industry": "Supply Chain",
        "title": "Inventory Control",
        "sop_id": "SOP-IC-047",
        "version": "v3.0",
        "embeddings": "sentence-transformers(all-MiniLM-L6-v2, local)",
        "vector_store": "FAISS (IndexFlatL2)",
        "llm_detail": "Anthropic Claude",
    },
}

SEV_ICON = {
    "Critical": "🔴",
    "High": "🟠",
    "Medium": "🟡",
    "Low": "🟢",
}

CURRENT_USER = "N.Fernandes (Process Owner)"

SOP_ID = "SOP-LU-001"


# =============================================================================
# HELPERS
# =============================================================================

def safe_float(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def badge(band: str) -> str:

    colors = {
        "Critical": RED,
        "High": ORANGE,
        "Moderate": YELLOW,
        "Stable": GREEN,
    }

    color = colors.get(
        band,
        GREEN,
    )

    return f"""
    <span style=" 
        display:inline-block; 
        padding:5px 10px; 
        border-radius:999px; 
        background:{color}20; 
        border:1px solid {color}55; 
        color:{color}; 
        font-size:11px; 
        font-weight:800; 
    "> 
        {band} 
    </span> 
    """


def status_badge(status: str):

    if status == "Approved":
        return """
        <div class="approval-approved">
            ✅ APPROVED · HUMAN GOVERNANCE COMPLETE
        </div>
        """

    if status == "Rejected":
        return """
        <div class="approval-rejected">
            ❌ REJECTED · MUTATION NOT IMPLEMENTED
        </div>
        """

    return """
    <div class="approval-pending">
        ⏳ PENDING HUMAN REVIEW
    </div>
    """


def mutation_key(proposal):

    return (
        f"{proposal.get('step_name', '')}"
        f"::{proposal.get('mutation_type', '')}"
    )


def get_live_deviation_rate():

    events = st.session_state.get(
        "live_feed",
        [],
    )

    if not events:
        return 0.0

    total = len(events)

    deviations = sum(
        1
        for event in events
        if "Deviation"
        in str(event.get("Status", ""))
    )

    return (
        deviations / total * 100
        if total
        else 0.0
    )

# =============================================================================
# LLM STATUS
# =============================================================================

def get_llm_status(rag):

    anthropic_key = os.getenv("ANTHROPIC_API_KEY")

    backend = str(
        getattr(
            rag,
            "llm_backend",
            "",
        )
    ).lower()

    if anthropic_key:

        return {
            "online": True,
            "label": "ONLINE",
            "detail": "Anthropic Claude",
            "color": GREEN,
            "icon": "🟢",
        }

    
def render_llm_indicator(rag):

    status = get_llm_status(rag)

    render_html(
        f"""
        <div style=" 
            margin-top:14px; 
            padding:12px 14px; 
            border-radius:14px; 

            background: 
                linear-gradient( 
                    135deg, 
                    {status['color']}12, 
                    rgba(15,23,42,.65) 
                ); 

            border: 
                1px solid {status['color']}45; 

            box-shadow: 
                0 10px 25px rgba(0,0,0,.20); 
        "> 

            <div style=" 
                color:{status['color']}; 
                font-size:12px; 
                font-weight:900; 
                letter-spacing:.6px; 
            "> 
                {status['icon']} 
                LLM {status['label']} 
            </div> 

            <div style=" 
                color:#94A3B8; 
                font-size:10px; 
                margin-top:4px; 
            "> 
                {status['detail']} 
            </div> 

        </div> 
        """
    )


# =============================================================================
# DYNAMIC TREND
# =============================================================================

def build_dynamic_trend(base_trend):

    """
    Adds simulated live events to the historical trend.
    """

    if base_trend is None or base_trend.empty:
        return base_trend

    result = base_trend.copy()

    if "timestamp" not in result.columns:
        return result

    result["timestamp"] = pd.to_datetime(
        result["timestamp"],
        errors="coerce",
    )

    result = result.dropna(
        subset=["timestamp"]
    )

    if result.empty:
        return result

    live_events = st.session_state.get(
        "live_feed",
        [],
    )

    if not live_events:
        return result

    live_rate = get_live_deviation_rate()

    last_timestamp = result["timestamp"].max()

    tick = st.session_state.get(
        "sim_tick",
        0,
    )

    latest_rate = safe_float(
        result.iloc[-1].get(
            "deviation_rate_pct",
            0,
        )
    )

    dynamic_rate = (
        latest_rate * 0.55
        + live_rate * 0.45
        + tick * 0.25
    )

    new_row = pd.DataFrame(
        [
            {
                "timestamp":
                    last_timestamp
                    + timedelta(
                        minutes=max(
                            1,
                            tick,
                        )
                    ),
                "deviation_rate_pct":
                    dynamic_rate,
            }
        ]
    )

    result = pd.concat(
        [
            result[
                [
                    "timestamp",
                    "deviation_rate_pct",
                ]
            ],
            new_row,
        ],
        ignore_index=True,
    )

    return result


# =============================================================================
# 3D PROCESS LANDSCAPE
# =============================================================================

def create_process_3d(genome, drift_df):

    rows = []

    risk_map = {
        "Low": 1,
        "Medium": 2,
        "High": 3,
        "Critical": 4,
    }

    for gene in genome.genes:

        matching = drift_df[
            drift_df["step_no"]
            == gene.step_no
        ] if not drift_df is None else pd.DataFrame()

        drift_value = 0

        if not matching.empty:

            drift_value = safe_float(
                matching.iloc[0].get(
                    "drift_severity_index",
                    0,
                )
            )

        rows.append(
            {
                "Step": gene.step_no,
                "Step Name": gene.step_name,
                "Risk": risk_map.get(
                    gene.risk_level,
                    1,
                ),
                "Drift": drift_value,
                "Risk Level": gene.risk_level,
            }
        )

    df = pd.DataFrame(rows)

    if df.empty:
        return None

    fig = go.Figure()

    colors = {
        "Low": GREEN,
        "Medium": YELLOW,
        "High": ORANGE,
        "Critical": RED,
    }

    for risk_level in df[
        "Risk Level"
    ].unique():

        subset = df[
            df["Risk Level"]
            == risk_level
        ]

        fig.add_trace(
            go.Scatter3d(
                x=subset["Step"],
                y=subset["Risk"],
                z=subset["Drift"],
                mode="markers+lines",
                name=risk_level,
                text=subset["Step Name"],
                hovertemplate=(
                    "<b>%{text}</b><br>"
                    "Step: %{x}<br>"
                    "Risk Tier: "
                    + risk_level
                    + "<br>"
                    "Drift: %{z:.1f}"
                    "<extra></extra>"
                ),
                marker=dict(
                    size=11,
                    color=colors.get(
                        risk_level,
                        PRIMARY,
                    ),
                    opacity=0.95,
                    line=dict(
                        width=2,
                        color="white",
                    ),
                ),
                line=dict(
                    width=5,
                    color=colors.get(
                        risk_level,
                        PRIMARY,
                    ),
                ),
            )
        )

    fig.update_layout(
        height=620,
        template="plotly_dark",

        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",

        scene=dict(
            xaxis_title="Process Sequence",
            yaxis_title="Risk Tier",
            zaxis_title="Drift Severity",

            bgcolor="rgba(0,0,0,0)",

            camera=dict(
                eye=dict(
                    x=1.65,
                    y=1.65,
                    z=1.25,
                )
            ),

            xaxis=dict(
                gridcolor="#26364D",
                backgroundcolor="rgba(10,18,32,.45)",
            ),

            yaxis=dict(
                gridcolor="#26364D",
                backgroundcolor="rgba(10,18,32,.35)",
            ),

            zaxis=dict(
                gridcolor="#26364D",
                backgroundcolor="rgba(10,18,32,.25)",
            ),
        ),

        legend=dict(
            bgcolor="rgba(7,17,31,.65)",
        ),

        margin=dict(
            l=0,
            r=0,
            t=20,
            b=0,
        ),
    )

    return fig


# =============================================================================
# DATA INITIALIZATION
# =============================================================================

sop_master = load_sop_master()

process_logs = load_process_logs()

sop_versions = load_sop_versions()

risk_incidents_raw = load_risk_incidents()

AUDIT_PATH = audit_trail_path()


genome = ProcessGenome.from_dataframe(
    sop_master,
    SOP_ID,
    version="v3.2",
)


# =============================================================================
# SESSION STATE
# =============================================================================

if "rag_engine" not in st.session_state:

    st.session_state.rag_engine = RAGEngine(
        genome
    )


if "mutation_decisions" not in st.session_state:

    st.session_state.mutation_decisions = {}


if "mutation_proposals" not in st.session_state:

    st.session_state.mutation_proposals = None


if "live_feed" not in st.session_state:

    st.session_state.live_feed = []


if "sim_tick" not in st.session_state:

    st.session_state.sim_tick = 0


if "approved_mutations" not in st.session_state:

    st.session_state.approved_mutations = []


if "rejected_mutations" not in st.session_state:

    st.session_state.rejected_mutations = []


if "audit_logged_once" not in st.session_state:

    st.session_state.audit_logged_once = False


rag = st.session_state.rag_engine


# =============================================================================
# ANALYTICS
# =============================================================================

drift_df = compute_step_drift(
    process_logs,
    sop_master,
)

deviation_breakdown = compute_deviation_breakdown(
    process_logs
)

trend_df = compute_trend(
    process_logs
)

risk_incidents = score_incidents(
    risk_incidents_raw
)

risk_score = overall_process_risk_score(
    risk_incidents,
    drift_df,
)

risk_drivers = top_risk_drivers(
    risk_incidents,
    drift_df,
)


# =============================================================================
# SIDEBAR BRAND
# =============================================================================

render_html(
    """
    <div style="
        padding:8px 0 6px;
    ">

        <div style="
            font-size:42px;
            line-height:1;
            filter:
                drop-shadow(
                    0 0 15px
                    rgba(249,115,22,.35)
                );
        ">
            🧬
        </div>

        <div style="
            color:#F8FAFC;
            font-size:20px;
            font-weight:950;
            margin-top:8px;
        ">
            Process Genome AI
        </div>

        <div style="
            color:#5EEAD4;
            font-size:10px;
            font-weight:800;
            letter-spacing:1px;
            margin-top:6px;
        ">
            EXL ENTERPRISE PROCESS INTELLIGENCE
        </div>

    </div>
    """
)


st.sidebar.markdown("---")
st.sidebar.caption(
    "✅ Anthropic Connected"
    if os.getenv("ANTHROPIC_API_KEY")
    
)


# =============================================================================
# NAVIGATION
# =============================================================================

PAGES = [
    "🏠 Command Center",
    "📊 CXO Dashboard",
    "🧬 Process Genome Explorer",
    "🤖 AI SOP Generator",
    "📉 SOP Drift Detection",
    "⚠️ Risk & Explainability",
    "✅ Human Approval Workflow",
    "📡 Real-Time Monitoring",
    "🔔 Predictive Alerts",
    "🔀 Process Comparison",
    "🎓 Training Generator",
    "📜 Audit Trail",
]

FEATURE_DESCRIPTIONS = {
    "🏠 Command Center": "Executive health, ROI, and live process KPIs",
    "📊 CXO Dashboard": "Leadership view of value, risk, and adoption",
    "🧬 Process Genome Explorer": "Inspect the SOP genome and its genes",
    "🤖 AI SOP Generator": "Draft grounded SOP updates with AI",
    "📉 SOP Drift Detection": "Find execution drift across process steps",
    "⚠️ Risk & Explainability": "Score risks and understand their drivers",
    "✅ Human Approval Workflow": "Review and approve proposed mutations",
    "📡 Real-Time Monitoring": "Watch simulated process execution live",
    "🔔 Predictive Alerts": "Explore forward-looking drift and risk alerts",
    "🔀 Process Comparison": "Compare genome generations and fitness",
    "🎓 Training Generator": "Generate training material and assessments",
    "📜 Audit Trail": "Review and export the immutable activity log",
}


def open_feature(feature: str):
    """Navigate to a feature and rotate the selected SOP so each click shows a
    different industry-oriented demo view.
    """
    st.session_state.active_page = feature

    # Rotate the currently selected SOP to the next one in the flattened list
    try:
        sop_options = []
        for v in INDUSTRY_TEMPLATES.values():
            for s in v:
                if s not in sop_options:
                    sop_options.append(s)

        if sop_options:
            current = st.session_state.get("selected_template", sop_options[0])
            if current in sop_options:
                next_idx = (sop_options.index(current) + 1) % len(sop_options)
            else:
                next_idx = 0
            st.session_state.selected_template = sop_options[next_idx]
    except Exception:
        # Keep navigation even if rotation fails
        pass


st.sidebar.markdown("---")
page = st.sidebar.radio(
    "Navigation",
    PAGES,
    label_visibility="collapsed",
    key="active_page",
)

# Show a selectable SOP dropdown only on SOP-related pages
sop_pages = [
    "📉 SOP Drift Detection",
    "🧬 Process Genome Explorer",
    "🤖 AI SOP Generator",
]

if page in sop_pages:
    # flatten industry templates into a unique list of SOP names
    sop_options = []
    for v in INDUSTRY_TEMPLATES.values():
        for s in v:
            if s not in sop_options:
                sop_options.append(s)

    if "selected_template" not in st.session_state:
        st.session_state.selected_template = sop_options[0] if sop_options else "Loan Underwriting SOP"
    elif st.session_state.selected_template not in sop_options:
        st.session_state.selected_template = sop_options[0] if sop_options else "Loan Underwriting SOP"

    selected = st.sidebar.selectbox(
        "Selected SOP",
        sop_options,
        index=sop_options.index(st.session_state.selected_template),
        key="selected_template",
    )
else:
    # Keep selection in state but don't render anything in the sidebar for non-SOP pages
    if "selected_template" not in st.session_state:
        st.session_state.selected_template = "Loan Underwriting SOP"

# =============================================================================
# SIDEBAR SYSTEM STATUS
# =============================================================================

st.sidebar.markdown("---")

st.sidebar.caption(
    "💡 Anthropic Claude enabled using ANTHROPIC_API_KEY."
)

st.sidebar.caption(
    "✅ Anthropic Connected"
    if os.getenv("ANTHROPIC_API_KEY")
    else "❌ Anthropic Not Connected"
)

llm_backend = getattr(
    rag,
    "llm_backend",
    "",
)

embedder = getattr(
    rag,
    "embedder",
    None,
)

store = getattr(
    rag,
    "store",
    None,
)


embedder_label = (
    embedder.label()
    if (
        embedder is not None
        and hasattr(
            embedder,
            "label",
        )
    )
    else "Unknown"
)


store_backend = (
    getattr(
        store,
        "backend",
        "Unknown",
    )
    if store is not None
    else "Unknown"
)


llm_status = get_llm_status(
    rag
)


selected_template_name = st.session_state.get("selected_template", "Loan Underwriting SOP")
selected_template_meta = TEMPLATE_METADATA.get(
    selected_template_name,
    {
        "industry": "Banking",
        "title": "Loan Underwriting",
        "sop_id": SOP_ID,
        "version": "v3.2",
        "embeddings": embedder_label,
        "vector_store": store_backend,
        "llm_detail": llm_status["detail"],
    },
)

render_html(
    f"""
    <div style="
        padding:14px;

        border-radius:16px;

        background:
            linear-gradient(
                135deg,
                rgba(15,23,42,.90),
                rgba(11,20,36,.80)
            );

        border:
            1px solid
            rgba(255,255,255,.08);

        box-shadow:
            0 15px 35px rgba(0,0,0,.25);
    ">

        <div style="
            color:#94A3B8;
            font-size:10px;
            font-weight:800;
            letter-spacing:.8px;
            text-transform:uppercase;
        ">
            {selected_template_meta["industry"]} · Enterprise Demo
        </div>

        <div style="
            color:#F8FAFC;
            font-size:14px;
            font-weight:800;
            margin-top:7px;
        ">
            {selected_template_meta["title"]}
        </div>

        <div style="
            color:#64748B;
            font-size:11px;
            margin-top:4px;
        ">
            SOP {selected_template_meta["sop_id"]} · {selected_template_meta["version"]}
        </div>

        <div style="
            margin-top:14px;
            color:#94A3B8;
            font-size:11px;
            line-height:1.9;
        ">

            <b style="color:#CBD5E1;">
                Embeddings:
            </b>
            {selected_template_meta["embeddings"]}

            <br>

            <b style="color:#CBD5E1;">
                Vector Store:
            </b>
            {selected_template_meta["vector_store"]}

        </div>

        <div style="
            margin-top:12px;
            padding:10px;

            border-radius:11px;

            background:
                {llm_status["color"]}12;

            border:
                1px solid
                {llm_status["color"]}45;
        ">

            <div style="
                color:{llm_status["color"]};
                font-size:12px;
                font-weight:900;
            ">
                {llm_status["icon"]}
                LLM {llm_status["label"]}
            </div>

            <div style="
                color:#94A3B8;
                font-size:10px;
                margin-top:3px;
            ">
                {selected_template_meta["llm_detail"]}
            </div>

        </div>

    </div>
    """
)


st.sidebar.markdown("---")

# =============================================================================
# COMMAND CENTER
# =============================================================================

if page == "🏠 Command Center":

    render_html(
        """
        <div class="hero-card">

            <div class="hero-brand">
                🧬 EXL ENTERPRISE PROCESS INTELLIGENCE
            </div>

            <div class="hero-title">
                Process Genome AI
            </div>

            <div class="hero-subtitle">
                Enterprise SOP Intelligence & Autonomous Process
                Governance Platform for intelligent, compliant and
                continuously evolving operations.
            </div>

            <div class="hero-metrics">

                <div class="hero-chip chip-teal">
                    🟢 LIVE PROCESS MONITORING
                </div>

                <div class="hero-chip chip-purple">
                    ◉ AI-DRIVEN SOP EVOLUTION
                </div>

                <div class="hero-chip chip-orange">
                    ⚡ PREDICTIVE RISK INTELLIGENCE
                </div>

                <div class="hero-chip chip-pink">
                    🛡 HUMAN GOVERNANCE
                </div>

                <div class="hero-chip chip-blue">
                    ◈ AUDIT-READY INTELLIGENCE
                </div>

            </div>

        </div>
        """
    )


    st.markdown(
        '<div class="section-label'>
        'ENTERPRISE COMMAND CENTER'
        '</div>',
        unsafe_allow_html=True,
    )

    st.markdown("## Explore Process Intelligence")
    st.caption("Select a feature to open its full workspace.")
    for row_start in range(0, len(PAGES), 4):
        feature_columns = st.columns(4)
        for feature_column, feature in zip(feature_columns, PAGES[row_start:row_start + 4]):
            with feature_column:
                st.button(
                    feature,
                    key=f"feature_button_{feature}",
                    use_container_width=True,
                    on_click=open_feature,
                    args=(feature,),
                )
                st.caption(FEATURE_DESCRIPTIONS[feature])


    st.markdown(
        "## Executive Process Health"
    )
    st.markdown("## 💰 Executive ROI Dashboard")

    # demo metrics based on selected SOP
    demo = get_demo_values(selected_template_name)

    r1, r2, r3, r4 = st.columns(4)

    r1.metric(
        "Potential Annual Savings",
        f"${demo['annual_savings_m']:.1f}M",
        "+18%"
    )

    r2.metric(
        "FTE Hours Saved",
        f"{int(demo['executions_logged'] // 10):,} hrs",
        "+4,200"
    )

    r3.metric(
        "Compliance Risk Reduction",
        f"{demo['compliance_pct']}%",
        "+11%"
    )

    r4.metric(
        "SLA Improvement",
        f"{10 + (demo['compliance_pct'] % 10)}%",
        "+9%"
    )

    st.info(
        """
    Business Impact Model

    • 300 employees
    • 20 SOP searches per day
    • Average search time reduced from 15 mins to 20 sec
    • Annual productivity gain > 18,000 hours
    • Estimated cost savings > $2.8M/year
    """
    )
    st.markdown("## 🧬 Process Genome Score™")

    g1, g2, g3, g4 = st.columns(4)

    g1.metric(
        "Compliance Score",
        f"{demo['compliance_pct']}"
    )

    g2.metric(
        "Efficiency Score",
        f"{min(99, 70 + int(demo['active_sop_genes']/2))}"
    )

    g3.metric(
        "Risk Score",
        f"{int(demo['process_risk_score'])}"
    )

    g4.metric(
        "Genome Score™",
        f"{int(50 + demo['process_risk_score'] / 2)}/100"
    )
    st.success(
        """
    Process Genome Score™ combines:

    • Compliance Adherence
    • Operational Efficiency
    • Risk Exposure
    • Process Stability

    into a single enterprise process health metric.
    """
    )

    k1, k2, k3, k4, k5, k6 = st.columns(6)
    k1.metric(
            "Process Risk",
            f"{int(demo['process_risk_score'])}/100",
            "Elevated",
        )

    k2.metric(
            "Active SOPs",
            f"{demo['active_sop_genes']}",
            "+6",
        )

    k3.metric(
            "AI Agents",
            "12",
            "+2",
        )

    k4.metric(
            "Pending Reviews",
            sum(
                1
                for value
                in st.session_state.mutation_decisions.values()
                if value == "Pending Review"
            ),
        )

    k5.metric(
            "Compliance",
            f"{demo['compliance_pct']}%",
            "+4%",
        )

    k6.metric(
            "Live Processes",
            f"{demo['processes_monitored']}",
        )


    st.markdown("")


    st.markdown(
            "### 🧠 AI Executive Insights"
        )

    ai1, ai2, ai3 = st.columns(3)

    with ai1:
        render_html(
                """
            <div class="executive-card teal">

                    <div class="executive-icon">
                        📈
                    </div>

                    <div class="executive-title">
                        Drift Acceleration
                    </div>

                    <div class="executive-text">
                        Loan Underwriting SOP drift increased by
                        <b style="color:#5EEAD4;">14%</b>
                        over the last two weeks.
                    </div>

                </div>
                """
            )

    with ai2:
        render_html(
            """
            <div class="executive-card purple">

                <div class="executive-icon">
                    ⚠️
                </div>

                <div class="executive-title">
                    Risk Concentration
                </div>

                <div class="executive-text">
                    Fraud Screening contributes approximately
                    <b style="color:#C4B5FD;">33%</b>
                    of total process risk.
                </div>

            </div>
            """
        )

    with ai3:
        render_html(
            """
            <div class="executive-card pink">

                <div class="executive-icon">
                    🚀
                </div>

                <div class="executive-title">
                    AI Recommendation
                </div>

                <div class="executive-text">
                    SOP Version
                    <b style="color:#FDBA74;">3.3</b>
                    is recommended for human approval.
                </div>

            </div>
            """
        )


    st.markdown("")

    c1, c2, c3, c4, c5 = st.columns(5)

    c1.metric(
        "Process Risk Score",
        f"{safe_float(risk_score.get('composite_score',0)):.0f}/100",
    )

    c2.metric(
        "Active SOP Genes",
        len(genome.genes),
    )

    c3.metric(
        "Executions Logged",
        f"{len(process_logs):,}",
    )

    c4.metric(
        "Open Risk Incidents",
        int(
            safe_float(
                risk_score.get(
                    "open_incidents",
                    0,
                )
            )
        ),
    )

    critical_steps = 0

    if (
        drift_df is not None
        and not drift_df.empty
        and "drift_band" in drift_df.columns
    ):

        critical_steps = len(
            drift_df[
                drift_df["drift_band"]
                == "Critical"
            ]
        )


    c5.metric(
        "Critical Drift Steps",
        critical_steps,
    )


    st.markdown("---")


    left, right = st.columns(
        [1.5, 1]
    )


    with left:

        st.markdown(
            "### 📊 Process Drift Intelligence"
        )


        if drift_df is not None and not drift_df.empty:

            fig = px.bar(
                drift_df,
                x="drift_severity_index",
                y="step_name",
                orientation="h",
                color="drift_band",
                color_discrete_map={
                    "Critical": RED,
                    "High": ORANGE,
                    "Moderate": YELLOW,
                    "Stable": GREEN,
                },
            )


            fig.update_layout(
                height=470,
                template="plotly_dark",
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(15,23,42,.55)",
                font=dict(
                    color="#CBD5E1"
                ),
                yaxis=dict(
                    categoryorder="total ascending"
                ),
                margin=dict(
                    l=10,
                    r=10,
                    t=20,
                    b=10,
                ),
            )


            st.plotly_chart(
                fig,
                use_container_width=True,
            )


    with right:

        st.markdown(
            "### 🎯 Process Risk Composition"
        )


        fig2 = go.Figure(
            go.Indicator(
                mode="gauge+number",
                value=safe_float(
                    risk_score.get("composite_score", 0)
                ),
                title={
                    "text": "Enterprise Risk"
                },
                gauge={
                    "axis": {
                        "range": [0, 100]
                    },
                    "bar": {"color": ORANGE},
                    "steps": [
                        {"range": [0, 25], "color": "#064E3B"},
                        {"range": [25, 50], "color": "#713F12"},
                        {"range": [50, 75], "color": "#7C2D12"},
                        {"range": [75, 100], "color": "#7F1D1D"},
                    ],
                },
            )
        )


        fig2.update_layout(
            height=280,
            template="plotly_dark",
            paper_bgcolor="rgba(0,0,0,0)",
            margin=dict(
                l=20,
                r=20,
                t=40,
                b=10,
            ),
        )


        st.plotly_chart(
            fig2,
            use_container_width=True,
        )

        st.markdown(
            "### 🧩 Deviation Breakdown"
        )


        if deviation_breakdown is not None and not deviation_breakdown.empty:

            fig3 = px.pie(
                deviation_breakdown,
                names="deviation_type",
                values="count",
                hole=0.55,
                color_discrete_sequence=[
                    PRIMARY,
                    PURPLE,
                    PINK,
                    BLUE,
                    ORANGE,
                ],
            )


            fig3.update_layout(
                height=280,
                template="plotly_dark",
                paper_bgcolor="rgba(0,0,0,0)",
                margin=dict(
                    l=10,
                    r=10,
                    t=10,
                    b=10,
                ),
            )


            st.plotly_chart(
                fig3,
                use_container_width=True,
            )


    st.markdown(
        "### 📈 Process Deviation Trend"
    )


    dynamic_trend = build_dynamic_trend(
        trend_df
    )


    if (
        dynamic_trend is not None
        and not dynamic_trend.empty
    ):

        fig4 = px.area(
            dynamic_trend,
            x="timestamp",
            y="deviation_rate_pct",
        )


        fig4.update_traces(
            line_color=ORANGE,
            fillcolor="rgba(249,115,22,.18)",
        )


        fig4.update_layout(
            height=300,
            template="plotly_dark",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(15,23,42,.55)",
            margin=dict(
                l=10,
                r=10,
                t=10,
                b=10,
            ),
        )


        st.plotly_chart(
            fig4,
            use_container_width=True,
        )


    st.markdown(
        "### 🎯 AI-Ranked Enterprise Risk Drivers"
    )


    driver_columns = [
        "step_name",
        "drift_severity_index",
        "incident_count",
        "open_count",
        "composite_driver_score",
    ]


    available_columns = [
        c
        for c in driver_columns
        if c in risk_drivers.columns
    ]


    if available_columns:

        st.dataframe(
            risk_drivers[
                available_columns
            ].rename(
                columns={
                    "step_name":
                        "Process Step",
                    "drift_severity_index":
                        "Drift Index",
                    "incident_count":
                        "Risk Incidents",
                    "open_count":
                        "Open Incidents",
                    "composite_driver_score":
                        "AI Risk Score",
                }
            ),
            use_container_width=True,
            hide_index=True,
        )


# =============================================================================
# PROCESS GENOME EXPLORER
# =============================================================================

elif page == "🧬 Process Genome Explorer":
    st.title(
        "🧬 Process Genome Explorer"
    )

    st.caption(
        "Every SOP step is represented as a process gene carrying "
        "risk, ownership, duration and compliance traits."
    )


    seq = genome.sequence_string()


    colored_seq = "".join(
        f'<span class="base-{base}">{base}</span>'
        for base in seq
    )


    render_html(
        f"""
        <div class="genome-card">

            <div style="
                color:#F8FAFC;
                font-size:18px;
                font-weight:800;
            ">
                Genome Sequence
            </div>

            <div style="
                color:#94A3B8;
                margin-top:4px;
                font-size:12px;
            ">
                {genome.sop_id} · {genome.version}
            </div>

            <div class="dna-sequence">
                {colored_seq}
            </div>

            <div style="
                color:#94A3B8;
                font-size:12px;
            ">
                <span class="base-G">G</span>
                Low risk &nbsp;&nbsp;

                <span class="base-T">T</span>
                Medium risk &nbsp;&nbsp;

                <span class="base-A">A</span>
                High risk &nbsp;&nbsp;

                <span class="base-C">C</span>
                Critical risk
            </div>

        </div>
        """
    )


    c1, c2, c3 = st.columns(3)


    c1.metric(
        "Genome Length",
        len(genome.genes),
    )


    c2.metric(
        "Baseline Cycle Time",
        f"{genome.total_expected_duration()} min",
    )


    comp = genome.risk_composition()


    c3.metric(
        "High/Critical Genes",
        comp.get("High",0) + comp.get("Critical",0),
    )


    st.markdown(
        "### 🌐 3D Process Genome Landscape"
    )


    fig3d = create_process_3d(
        genome,
        drift_df,
    )


    if fig3d is not None:

        st.plotly_chart(
            fig3d,
            use_container_width=True,
        )


    st.markdown(
        "### Gene-by-Gene Breakdown"
    )


    for gene in genome.genes:

        drift_row = drift_df[
            drift_df.step_no
            == gene.step_no
        ] if drift_df is not None else pd.DataFrame()


        band = (
            drift_row.iloc[0].drift_band
            if not drift_row.empty
            else "Stable"
        )


        with st.expander(
            f"Gene {gene.step_no} · "
            f"{gene.step_name} — {band}"
        ):

            cc1, cc2 = st.columns(
                [2, 1]
            )


            with cc1:

                st.write(
                    gene.description
                )

                st.caption(
                    f"Owner: {gene.owner_role} · "
                    f"Compliance: {gene.compliance_ref}"
                )


            with cc2:

                st.metric(
                    "Baseline Duration",
                    f"{gene.expected_duration_min} min",
                )

                st.metric(
                    "Risk Tier",
                    gene.risk_level,
                )

                render_html(
                    badge(band)
                )

# =============================================================================
# CXO DASHBOARD
# =============================================================================

elif page == "📊 CXO Dashboard":

    st.title("📊 CXO Business Dashboard")

    c1, c2, c3, c4, c5 = st.columns(5)

    c1.metric(
        "Processes Monitored",
        "850"
    )

    c2.metric(
        "Compliance",
        "96%"
    )

    c3.metric(
        "High Risk Processes",
        "12"
    )

    c4.metric(
        "Annual Savings",
        "$4.2M"
    )

    c5.metric(
        "AI Recommendations Applied",
        "78%"
    )

    st.markdown("---")

    st.markdown("## Executive Summary")

    st.success(
        """
        Process Genome AI currently monitors 850 enterprise processes.

        AI governance reduced risk exposure by 42%.

        Compliance adherence improved to 96%.

        Potential annual savings exceed $4.2M through
        reduced search effort, lower audit costs,
        improved SLA adherence and risk prevention.

        This demonstrates direct business value for EXL clients.
        """
    )

    st.markdown("## 💰 Business Value Overview")

    b1, b2, b3, b4 = st.columns(4)

    b1.metric(
        "Hours Saved",
        "18,900"
    )

    b2.metric(
        "Audit Effort Reduction",
        "35%"
    )

    b3.metric(
        "SLA Improvement",
        "31%"
    )

    b4.metric(
        "Risk Reduction",
        "42%"
    )

    st.markdown("## 🌍 Industry Scalability")

    industry_df = pd.DataFrame({
        "Industry": [
            "Banking",
            "Insurance",
            "Healthcare",
            "Finance & Accounting",
            "Supply Chain"
        ],
        "Sample Process": [
            "Loan Underwriting",
            "Claims Processing",
            "Prior Authorization",
            "Invoice Processing",
            "Vendor Management"
        ]
    })

    st.dataframe(
        industry_df,
        use_container_width=True,
        hide_index=True
    )

# =============================================================================
# AI SOP GENERATOR
# =============================================================================

elif page == "🤖 AI SOP Generator":

    st.title(
        "🤖 AI SOP Generator"
    )

    st.caption(
        "Generate enterprise-ready SOP drafts grounded in the existing "
        "Process Genome using retrieval-augmented intelligence."
    )


    with st.form(
        "sop_gen_form"
    ):

        process_description = st.text_area(
            "Business Requirement",
            placeholder=(
                "Example: New regulatory requirement requires "
                "enhanced source-of-funds verification."
            ),
            height=130,
        )


        domain = st.text_input(
            "Business Domain",
            value="Loan Underwriting",
        )


        submitted = st.form_submit_button(
            "⚡ Generate Enterprise SOP",
            type="primary",
        )


    if submitted and process_description.strip():

        with st.spinner(
            "Analyzing Process Genome and generating SOP..."
        ):

            result = rag.generate_sop_draft(
                process_description,
                domain,
            )


        st.success(
            f"Generated using: {result.get('backend', 'Process Genome AI')}"
        )


        col1, col2 = st.columns(
            [1.6, 1]
        )


        with col1:

            st.markdown(
                "### 📝 AI-Generated SOP"
            )

            st.markdown(
                result.get(
                    "draft",
                    "No SOP draft was generated.",
                )
            )


        with col2:

            st.markdown(
                "### 🔎 Grounding Evidence"
            )


            for i, snippet in enumerate(
                result.get(
                    "grounded_on",
                    [],
                ),
                1,
            ):

                with st.container():

                    st.markdown(
                        f"**Evidence {i}**"
                    )

                    st.caption(
                        snippet
                    )


        log_event(
            AUDIT_PATH,
            CURRENT_USER,
            "SOP_GENERATED",
            "SOP",
            SOP_ID,
            (
                "AI SOP draft generated: "
                f"{process_description[:100]}"
            ),
        )


    elif submitted:

        st.warning(
            "Please enter a business requirement."
        )


    st.markdown("---")


    st.markdown(
        "### 🔍 Ask the Process Genome"
    )


    q = st.text_input(
        "Ask a question",
        placeholder=(
            "Which step handles fraud screening?"
        ),
    )


    if q.strip():

        hits = rag.retrieve(
            q,
            top_k=3,
        )


        if not hits:

            st.info(
                "No relevant Process Genome evidence found."
            )


        for text, score, meta in hits:

            with st.container():

                st.markdown(
                    f"**Relevance: {score:.2f}**"
                )

                st.caption(
                    meta.get(
                        "step_name",
                        "",
                    )
                )

                st.write(
                    text
                )

# =============================================================================
# SOP DRIFT DETECTION
# =============================================================================

elif page == "📉 SOP Drift Detection":

    st.title(
        "📉 SOP Drift Detection"
    )

    st.caption(
        "Compare actual process execution behavior against the "
        "approved enterprise SOP genome."
    )


    tab1, tab2, tab3 = st.tabs(
        [
            "Step-Level Drift",
            "Deviation Breakdown",
            "Structural Drift",
        ]
    )


    with tab1:

        columns = [
            "step_name",
            "executions",
            "expected_duration",
            "avg_actual_duration",
            "duration_overrun_pct",
            "deviation_rate_pct",
            "risk_level",
            "drift_severity_index",
            "drift_band",
        ]


        columns = [
            c
            for c in columns
            if c in drift_df.columns
        ]


        st.dataframe(
            drift_df[
                columns
            ].rename(
                columns={
                    "step_name":
                        "Step",
                    "executions":
                        "Executions",
                    "expected_duration":
                        "Baseline",
                    "avg_actual_duration":
                        "Avg Actual",
                    "duration_overrun_pct":
                        "Overrun %",
                    "deviation_rate_pct":
                        "Deviation %",
                    "risk_level":
                        "Risk",
                    "drift_severity_index":
                        "Drift Index",
                    "drift_band":
                        "Band",
                }
            ),
            use_container_width=True,
            hide_index=True,
        )


    with tab2:

        c1, c2 = st.columns(
            [1, 1.3]
        )


        with c1:

            st.dataframe(
                deviation_breakdown.rename(
                    columns={
                        "deviation_type":
                            "Deviation Type",
                        "count":
                            "Count",
                        "pct":
                            "% of Deviations",
                    }
                ),
                use_container_width=True,
                hide_index=True,
            )


        with c2:

            if not deviation_breakdown.empty:

                fig = px.bar(
                    deviation_breakdown,
                    x="deviation_type",
                    y="count",
                    color="deviation_type",
                    color_discrete_sequence=[
                        PRIMARY,
                        PURPLE,
                        PINK,
                        ORANGE,
                        BLUE,
                    ],
                )


                fig.update_layout(
                    height=380,
                    template="plotly_dark",
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(15,23,42,.55)",
                    showlegend=False,
                )


                st.plotly_chart(
                    fig,
                    use_container_width=True,
                )


            else:

                st.info(
                    "No deviation data available."
                )


    with tab3:

        case_ids = sorted(
            process_logs.case_id.dropna()
            .unique()
            .tolist()
        )


        if not case_ids:

            st.info(
                "No case IDs available."
            )


        else:

            selected_case = st.selectbox(
                "Select case",
                case_ids,
            )


            case_steps = (
                process_logs[
                    process_logs.case_id
                    == selected_case
                ]
                .sort_values("timestamp")
                .step_no
                .tolist()
            )


            baseline_seq = sorted(
                sop_master.step_no.tolist()
            )


            diff = structural_diff(
                baseline_seq,
                case_steps,
            )


            c1, c2, c3 = st.columns(3)


            c1.metric(
                "Skipped Steps",
                len(
                    diff["skipped_steps"]
                ),
            )


            c2.metric(
                "Unexpected Steps",
                len(
                    diff["added_steps"]
                ),
            )


            c3.metric(
                "Reordered",
                "Yes"
                if diff["reordered"]
                else "No",
            )


            if diff["skipped_steps"]:

                names = sop_master[
                    sop_master.step_no.isin(
                        diff["skipped_steps"]
                    )
                ].step_name.tolist()


                st.error(
                    "Skipped steps: "
                    + ", ".join(names)
                )


            if diff["added_steps"]:

                st.warning(
                    "Unexpected step numbers: "
                    + ", ".join(
                        map(
                            str,
                            diff["added_steps"],
                        )
                    )
                )


            if diff["reordered"]:

                st.warning(
                    f"Baseline: "
                    f"{diff['baseline_order']}"
                )

                st.warning(
                    f"Observed: "
                    f"{diff['observed_order']}"
                )


# =============================================================================
# RISK & EXPLAINABILITY
# =============================================================================

elif page == "⚠️ Risk & Explainability":

    st.title(
        "⚠️ Risk Detection & AI Explainability"
    )

    st.caption(
        "Transparent factor-level explanation for every process risk score."
    )


    c1, c2, c3 = st.columns(3)


    c1.metric(
        "Composite Risk",
        f"{safe_float(risk_score.get('composite_score',0)):.0f}/100",
        risk_score.get("label", ""),
    )


    c2.metric(
        "Incident Component",
        f"{safe_float(risk_score.get('incident_component', 0)):.1f}",
    )


    c3.metric(
        "Drift Component",
        f"{safe_float(risk_score.get('drift_component', 0)):.1f}",
    )


    st.markdown(
        "### 🧾 Risk Incidents"
    )


    sev_filter = st.multiselect(
        "Severity",
        [
            "Critical",
            "High",
            "Medium",
            "Low",
        ],
        default=[
            "Critical",
            "High",
        ],
    )


    filtered = (
        risk_incidents[
            risk_incidents.severity.isin(
                sev_filter
            )
        ]
        if sev_filter
        else risk_incidents
    )


    incident_columns = [
        "incident_id",
        "step_name",
        "risk_type",
        "severity",
        "detected_on",
        "status",
        "description",
    ]


    incident_columns = [
        c
        for c in incident_columns
        if c in filtered.columns
    ]


    st.dataframe(
        filtered[
            incident_columns
        ].rename(
            columns={
                "incident_id":
                    "ID",
                "step_name":
                    "Step",
                "risk_type":
                    "Type",
                "severity":
                    "Severity",
                "detected_on":
                    "Detected",
                "status":
                    "Status",
                "description":
                    "Description",
            }
        ),
        use_container_width=True,
        hide_index=True,
    )


    st.markdown("---")


    st.markdown(
        "### 🧠 AI Explainability"
    )


    if not drift_df.empty:

        step_choice = st.selectbox(
            "Select process step",
            drift_df.step_name.tolist(),
        )


        row = drift_df[
            drift_df.step_name
            == step_choice
        ].iloc[0]


        explanation = explain_drift_row(
            row
        )


        st.info(
            explanation["narrative"]
        )


        factors = explanation.get(
            "factors",
            [],
        )


        if factors:

            factor_cols = st.columns(
                len(factors)
            )


            for col, factor in zip(
                factor_cols,
                factors,
            ):

                with col:

                    st.markdown(
                        f"**{factor['factor']}**"
                    )

                    st.markdown(
                        str(
                            factor["value"]
                        )
                    )

                    contribution = factor.get(
                        "contribution"
                    )


                    if contribution is not None:

                        st.progress(
                            min(
                                1.0,
                                max(
                                    0.0,
                                    safe_float(
                                        contribution
                                    )
                                    / 100,
                                ),
                            )
                        )


                    st.caption(
                        factor.get(
                            "explanation",
                            "",
                        )
                    )


# =============================================================================
# HUMAN APPROVAL WORKFLOW
# =============================================================================

elif page == "✅ Human Approval Workflow":

    st.title(
        "✅ Human-in-the-Loop Approval"
    )

    st.caption(
        "AI proposes SOP mutations while enterprise users retain "
        "final decision authority."
    )


    if (
        st.session_state.mutation_proposals
        is None
    ):

        st.session_state.mutation_proposals = (
            propose_mutations(
                drift_df,
                risk_drivers,
            )
        )


    proposals = (
        st.session_state.mutation_proposals
        or []
    )


    pending_count = 0
    approved_count = 0
    rejected_count = 0


    for proposal in proposals:

        key = mutation_key(
            proposal
        )


        decision = (
            st.session_state
            .mutation_decisions
            .get(
                key,
                "Pending Review",
            )
        )


        if decision == "Approved":
            approved_count += 1

        elif decision == "Rejected":
            rejected_count += 1

        else:
            pending_count += 1


    s1, s2, s3, s4 = st.columns(4)


    s1.metric(
        "AI Proposals",
        len(proposals),
    )


    s2.metric(
        "Pending Review",
        pending_count,
    )


    s3.metric(
        "Approved",
        approved_count,
    )


    s4.metric(
        "Rejected",
        rejected_count,
    )


    if approved_count:

        render_html(
            f"""
            <div class="approval-approved">

                🟢 {approved_count}
                SOP MUTATION(S) APPROVED

                <span style="
                    float:right;
                    color:#BBF7D0;
                    font-size:12px;
                ">
                    Human Governance Confirmed
                </span>

            </div>
            """
        )


    if not proposals:

        st.success(
            "No mutations currently proposed."
        )


    else:

        for i, proposal in enumerate(
            proposals
        ):

            key = mutation_key(
                proposal
            )


            decision = (
                st.session_state
                .mutation_decisions
                .get(
                    key,
                    "Pending Review",
                )
            )


            with st.container():

                c1, c2 = st.columns(
                    [3, 1]
                )


                with c1:

                    st.markdown(
                        f"### 🧬 "
                        f"{proposal['mutation_type']}"
                    )


                    st.markdown(
                        f"**Process Step:** "
                        f"{proposal['step_name']}"
                    )


                    st.write(
                        proposal["description"]
                    )


                    exp = explain_mutation(
                        pd.Series(
                            {
                                "mutation_description":
                                    proposal[
                                        "description"
                                    ],
                                "mutation_type":
                                    proposal[
                                        "mutation_type"
                                    ],
                                "fitness_score":
                                    proposal[
                                        "fitness_score"
                                    ],
                            }
                        )
                    )


                    st.caption(
                        exp["narrative"]
                    )


                with c2:

                    st.metric(
                        "Fitness",
                        proposal[
                            "fitness_score"
                        ],
                    )


                    render_html(
                        status_badge(
                            decision
                        )
                    )


                if decision == "Approved":

                    render_html(
                        """
                        <div class="approval-approved">

                            ✅ APPROVED

                            <br>

                            <span style="
                                font-size:11px;
                                font-weight:500;
                                color:#BBF7D0;
                            ">
                                This mutation has passed
                                human governance and is now
                                included in the approved
                                mutation history.
                            </span>

                        </div>
                        """
                    )


                elif decision == "Rejected":

                    render_html(
                        """
                        <div class="approval-rejected">

                            ❌ REJECTED

                            <br>

                            <span style="
                                font-size:11px;
                                font-weight:500;
                                color:#FECACA;
                            ">
                                This AI mutation was rejected
                                by the process owner.
                            </span>

                        </div>
                        """
                    )


                else:

                    b1, b2, b3 = st.columns(3)


                    if b1.button(
                        "✅ Approve Mutation",
                        key=f"approve_{i}",
                        type="primary",
                    ):

                        st.session_state.mutation_decisions[
                            key
                        ] = "Approved"


                        approved_entry = {
                            "step_name":
                                proposal[
                                    "step_name"
                                ],
                            "mutation_type":
                                proposal[
                                    "mutation_type"
                                ],
                            "description":
                                proposal[
                                    "description"
                                ],
                            "fitness_score":
                                proposal[
                                    "fitness_score"
                                ],
                            "approved_by":
                                CURRENT_USER,
                            "approved_at":
                                datetime.now().strftime(
                                    "%Y-%m-%d %H:%M:%S"
                                ),
                        }


                        existing_keys = {
                            (
                                item["step_name"],
                                item["mutation_type"],
                            )
                            for item
                            in st.session_state.approved_mutations
                        }


                        entry_key = (
                            approved_entry["step_name"],
                            approved_entry["mutation_type"],
                        )


                        if entry_key not in existing_keys:

                            st.session_state.approved_mutations.append(
                                approved_entry
                            )


                        log_event(
                            AUDIT_PATH,
                            CURRENT_USER,
                            "SOP_MUTATION_APPROVED",
                            "Mutation",
                            key,
                            proposal[
                                "description"
                            ],
                        )


                        st.experimental_rerun()


                    if b2.button(
                        "❌ Reject Mutation",
                        key=f"reject_{i}",
                    ):

                        st.session_state.mutation_decisions[
                            key
                        ] = "Rejected"


                        rejected_entry = {
                            "step_name":
                                proposal[
                                    "step_name"
                                ],
                            "mutation_type":
                                proposal[
                                    "mutation_type"
                                ],
                            "description":
                                proposal[
                                    "description"
                                ],
                            "fitness_score":
                                proposal[
                                    "fitness_score"
                                ],
                            "rejected_by":
                                CURRENT_USER,
                            "rejected_at":
                                datetime.now().strftime(
                                    "%Y-%m-%d %H:%M:%S"
                                ),
                        }


                        st.session_state.rejected_mutations.append(
                            rejected_entry
                        )


                        log_event(
                            AUDIT_PATH,
                            CURRENT_USER,
                            "SOP_MUTATION_REJECTED",
                            "Mutation",
                            key,
                            proposal[
                                "description"
                            ],
                        )


                        st.experimental_rerun()


                    if b3.button(
                        "↩ Reset",
                        key=f"reset_{i}",
                    ):

                        st.session_state.mutation_decisions[
                            key
                        ] = "Pending Review"


                        st.session_state.approved_mutations = [
                            item
                            for item
                            in st.session_state.approved_mutations
                            if not (
                                item["step_name"]
                                == proposal[
                                    "step_name"
                                ]
                                and
                                item["mutation_type"]
                                == proposal[
                                    "mutation_type"
                                ]
                            )
                        ]


                        st.experimental_rerun()


    st.markdown("---")


    st.markdown(
        "### 🟢 Approved Mutation Registry"
    )


    if st.session_state.approved_mutations:

        approved_df = pd.DataFrame(
            st.session_state.approved_mutations
        )


        st.dataframe(
            approved_df.rename(
                columns={
                    "step_name":
                        "Process Step",
                    "mutation_type":
                        "Mutation Type",
                    "description":
                        "Approved Change",
                    "fitness_score":
                        "Fitness",
                    "approved_by":
                        "Approved By",
                    "approved_at":
                        "Approved At",
                }
            ),
            use_container_width=True,
            hide_index=True,
        )


    else:

        st.info(
            "No mutations have been approved in this session."
        )


    st.markdown("---")


    st.markdown(
        "### 📚 Historical SOP Mutation Versions"
    )


    st.dataframe(
        sop_versions.rename(
            columns={
                "version_id":
                    "Version",
                "generation":
                    "Generation",
                "mutation_type":
                    "Type",
                "mutation_description":
                    "Description",
                "fitness_score":
                    "Fitness",
                "status":
                    "Status",
                "approved_by":
                    "Approved By",
                "timestamp":
                    "Date",
            }
        ),
        use_container_width=True,
        hide_index=True,
    )


# =============================================================================
# REAL-TIME MONITORING
# =============================================================================

elif page == "📡 Real-Time Monitoring":

    st.title(
        "📡 Real-Time Process Monitoring"
    )

    st.caption(
        "Simulated enterprise execution stream for demonstrating "
        "real-time process governance."
    )


    c1, c2, c3 = st.columns(3)


    with c1:

        if st.button(
            "▶ Advance Simulation",
            type="primary",
        ):

            st.session_state.sim_tick += 1


            executors = [
                "A.Rao",
                "K.Menon",
                "S.Iyer",
                "P.Nair",
                "R.Das",
                "T.Sharma",
            ]


            for _ in range(
                random.randint(
                    3,
                    6,
                )
            ):

                step_row = (
                    sop_master
                    .sample(1)
                    .iloc[0]
                )


                deviated = (
                    random.random()
                    < 0.22
                )


                event = {
                    "Time":
                        datetime.now().strftime(
                            "%H:%M:%S"
                        ),
                    "Case ID":
                        f"LN-{2026300 + random.randint(0,99)}",
                    "Process Step":
                        step_row.step_name,
                    "Executor":
                        random.choice(
                            executors
                        ),
                    "Status":
                        (
                            "⚠️ Deviation"
                            if deviated
                            else "✅ On-Track"
                        ),
                    "Risk":
                        step_row.risk_level,
                }


                st.session_state.live_feed.insert(
                    0,
                    event,
                )


            st.session_state.live_feed = (
                st.session_state.live_feed[:40]
            )


    with c2:

        st.metric(
            "Simulation Ticks",
            st.session_state.sim_tick,
        )


    with c3:

        st.metric(
            "Events in Stream",
            len(
                st.session_state.live_feed
            ),
        )


    if st.session_state.live_feed:

        feed_df = pd.DataFrame(
            st.session_state.live_feed
        )


        st.dataframe(
            feed_df,
            use_container_width=True,
            hide_index=True,
        )


        deviations_live = feed_df[
            feed_df["Status"].str.contains(
                "Deviation",
                na=False,
            )
        ]


        live_rate = get_live_deviation_rate()


        l1, l2 = st.columns(2)


        l1.metric(
            "Live Deviation Rate",
            f"{live_rate:.1f}%",
        )


        l2.metric(
            "Predictive Pressure",
            (
                "HIGH"
                if live_rate >= 30
                else
                "ELEVATED"
                if live_rate >= 18
                else
                "NORMAL"
            ),
        )


        if len(deviations_live):

            st.warning(
                f"⚠️ {len(deviations_live)} "
                "live deviations detected."
            )


        else:

            st.success(
                "✅ No deviations in the current live window."
            )


    else:

        st.info(
            "Click Advance Simulation to start "
            "the live process stream."
        )


# =============================================================================
# PREDICTIVE ALERTS
# =============================================================================

elif page == "🔔 Predictive Alerts":

    st.title(
        "🔔 Predictive Process Alerts"
    )

    st.caption(
        "Forecast process drift before it becomes a critical enterprise event. "
        "The forecast updates as simulated process executions arrive."
    )


    dynamic_trend = apply_template_impact_to_trend(
        build_dynamic_trend(trend_df)
    )


    if (
        dynamic_trend is not None
        and not dynamic_trend.empty
    ):

        projected_df, slope = project_trend(
            dynamic_trend,
            periods_ahead=4,
        )

        template_values = get_demo_values(get_selected_template_name())
        slope = template_values["drift_slope"]

        fig = px.line(
            projected_df,
            x="timestamp",
            y="deviation_rate_pct",
            color="type",
            color_discrete_map={
                "Historical": PRIMARY,
                "Projected": ORANGE,
            },
            markers=True,
        )


        fig.update_traces(
            line=dict(
                width=4
            )
        )


        fig.update_layout(
            height=450,
            template="plotly_dark",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(15,23,42,.55)",
            margin=dict(
                l=10,
                r=10,
                t=25,
                b=10,
            ),
            xaxis_title="Process Timeline",
            yaxis_title="Deviation Rate %",
        )


        st.plotly_chart(
            fig,
            use_container_width=True,
        )


        latest_value = safe_float(
            dynamic_trend.iloc[-1][
                "deviation_rate_pct"
            ]
        )

        latest_value = max(latest_value, template_values["drift_pct"] / 2)

        slope_value = safe_float(
            slope
        )


        m1, m2, m3, m4 = st.columns(4)


        m1.metric(
            "Current Deviation",
            f"{latest_value:.1f}%",
        )


        m2.metric(
            "Forecast Slope",
            f"{slope_value:+.2f}",
        )


        m3.metric(
            "Live Simulation Ticks",
            st.session_state.sim_tick,
        )


        m4.metric(
            "Live Event Deviation",
            f"{get_live_deviation_rate():.1f}%",
        )


        alerts = generate_predictive_alerts(
            drift_df,
            dynamic_trend,
            slope,
        )

        for alert in alerts:
            alert["title"] = f"{selected_template_name} · {alert['title']}"
            alert["message"] = (
                f"{alert['message']} This pattern is consistent with the "
                f"{selected_template_name} operating profile and current drift signal."
            )

        if not alerts:

            st.success(
                "✅ No predictive alerts. "
                "Process trajectory is stable."
            )


        for alert in alerts:

            icon = SEV_ICON.get(
                alert["severity"],
                "🔵",
            )
            with st.container():

                st.markdown(
                    f"### {icon} "
                    f"{alert['title']}"
                )


                st.write(
                    alert["message"]
                )


                st.caption(
                    "Recommended action: "
                    f"{alert['recommended_action']}"
                )


    else:

        st.info(
            "No historical trend available."
        )


# =============================================================================
# PROCESS COMPARISON
# =============================================================================

elif page == "🔀 Process Comparison":

    st.title(
        "🔀 Process & Genome Version Comparison"
    )

    st.caption(
        "Compare genome generations, approved AI mutations and "
        "process fitness evolution."
    )


    gens = sorted(
        pd.Series(
            sop_versions.generation
        )
        .dropna()
        .unique()
        .tolist()
    )


    approved_count = len(
        st.session_state.approved_mutations
    )


    if approved_count:

        base_generation = (
            max(gens)
            if gens
            else 0
        )


        virtual_generation = (
            base_generation
            + 1
        )


        if virtual_generation not in gens:

            gens = (
                gens
                + [virtual_generation]
            )


    if not gens:

        st.info(
            "No genome generations available."
        )


    else:

        c1, c2 = st.columns(2)


        gen_a = c1.selectbox(
            "Baseline Generation",
            gens,
            index=0,
        )


        gen_b = c2.selectbox(
            "Compare Generation",
            gens,
            index=len(gens) - 1,
        )


        hist_a = sop_versions[
            sop_versions.generation
            <= gen_a
        ]


        hist_b = sop_versions[
            sop_versions.generation
            <= gen_b
        ]


        fit_a = pd.to_numeric(
            hist_a.fitness_score,
            errors="coerce",
        ).max()


        fit_b = pd.to_numeric(
            hist_b.fitness_score,
            errors="coerce",
        ).max()


        if (
            approved_count
            and gen_b
            == max(gens)
        ):

            approved_fitness = [
                safe_float(
                    item.get(
                        "fitness_score",
                        0,
                    )
                )
                for item
                in st.session_state.approved_mutations
            ]


            if approved_fitness:

                fit_b = max(
                    [
                        fit_b
                        if pd.notna(fit_b)
                        else 0
                    ]
                    + approved_fitness
                )


        m1, m2, m3 = st.columns(3)


        m1.metric(
            f"Fitness Gen {gen_a}",
            (
                f"{fit_a:.2f}"
                if pd.notna(fit_a)
                else "—"
            ),
        )


        delta = None


        if (
            pd.notna(fit_a)
            and pd.notna(fit_b)
        ):

            delta = (
                f"{fit_b-fit_a:+.2f}"
            )


        m2.metric(
            f"Fitness Gen {gen_b}",
            (
                f"{fit_b:.2f}"
                if pd.notna(fit_b)
                else "—"
            ),
            delta,
        )


        mutations_between = sop_versions[
            (
                sop_versions.generation
                > min(gen_a, gen_b)
            )
            &
            (
                sop_versions.generation
                <= max(gen_a, gen_b)
            )
        ]


        m3.metric(
            "Historical Mutations",
            len(mutations_between),
        )


        st.markdown(
            "### 🧬 Mutations Between Generations"
        )


        if mutations_between.empty:

            st.info(
                "No historical mutations between selected generations."
            )


        else:

            display_cols = [
                "generation",
                "mutation_type",
                "mutation_description",
                "fitness_score",
                "status",
            ]


            display_cols = [
                c
                for c in display_cols
                if c in mutations_between.columns
            ]


            st.dataframe(
                mutations_between[
                    display_cols
                ].rename(
                    columns={
                        "generation":
                            "Generation",
                        "mutation_type":
                            "Type",
                        "mutation_description":
                            "Description",
                        "fitness_score":
                            "Fitness",
                        "status":
                            "Status",
                    }
                ),
                use_container_width=True,
                hide_index=True,
            )


        st.markdown(
            "### 🟢 Live Human-Approved Mutations"
        )


        if st.session_state.approved_mutations:

            approved_df = pd.DataFrame(
                st.session_state.approved_mutations
            )


            st.dataframe(
                approved_df.rename(
                    columns={
                        "step_name":
                            "Process Step",
                        "mutation_type":
                            "Mutation Type",
                        "description":
                            "Approved Change",
                        "fitness_score":
                            "Fitness",
                        "approved_by":
                            "Approved By",
                        "approved_at":
                            "Approved At",
                    }
                ),
                use_container_width=True,
                hide_index=True,
            )


            st.success(
                f"🧬 {len(st.session_state.approved_mutations)} "
                "approved mutation(s) are now reflected in the "
                "live genome comparison."
            )


        else:

            st.info(
                "Approve a mutation in Human Approval Workflow "
                "to see it appear here dynamically."
            )


        st.markdown(
            "### 📈 Genome Fitness Evolution"
        )


        evo = sop_versions.copy()


        evo["fitness_numeric"] = pd.to_numeric(
            evo.fitness_score,
            errors="coerce",
        )


        evo["Generation Label"] = (
            "Historical Gen "
            + evo["generation"].astype(str)
        )


        if st.session_state.approved_mutations:

            base_gen_series = pd.to_numeric(
                sop_versions.generation,
                errors="coerce",
            ).dropna()


            base_gen = (
                max(base_gen_series)
                if not base_gen_series.empty
                else 0
            )


            live_rows = []


            for item in st.session_state.approved_mutations:

                live_rows.append(
                    {
                        "generation":
                            base_gen + 1,

                        "fitness_numeric":
                            safe_float(
                                item.get(
                                    "fitness_score",
                                    0,
                                )
                            ),

                        "Generation Label":
                            "🟢 Live Approved",
                    }
                )


            if live_rows:

                evo = pd.concat(
                    [
                        evo[
                            [
                                "generation",
                                "fitness_numeric",
                                "Generation Label",
                            ]
                        ],
                        pd.DataFrame(
                            live_rows
                        ),
                    ],
                    ignore_index=True,
                )


        fig = px.line(
            evo,
            x="generation",
            y="fitness_numeric",
            color="Generation Label",
            markers=True,
        )


        fig.update_traces(
            line=dict(
                width=4
            )
        )


        fig.update_layout(
            height=390,
            template="plotly_dark",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(15,23,42,.55)",
            xaxis_title="Genome Generation",
            yaxis_title="Fitness Score",
        )


        st.plotly_chart(
            fig,
            use_container_width=True,
        )


# =============================================================================
# TRAINING GENERATOR
# =============================================================================

elif page == "🎓 Training Generator":

    st.title(
        "🎓 AI Training Generator"
    )

    st.caption(
        "Automatically convert approved SOP knowledge into employee training."
    )


    deck = generate_training_deck(
        genome
    )


    if deck:

        st.markdown(
            f"### 📖 Training Deck · "
            f"{len(deck)} Slides"
        )


        slide_idx = (
            st.slider(
                "Training Slide",
                1,
                len(deck),
                1,
            )
            - 1
        )


        slide = deck[
            slide_idx
        ]


        with st.container():

            st.markdown(
                f"## {slide['title']}"
            )


            for bullet in slide[
                "bullets"
            ]:

                st.markdown(
                    f"- {bullet}"
                )


    else:

        st.info(
            "No training slides generated."
        )


    st.markdown("---")


    st.markdown(
        "### ✏️ Knowledge Assessment"
    )


    quiz = generate_quiz(
        genome,
        n_questions=5,
    )


    answers = []


    with st.form(
        "quiz_form"
    ):

        for i, question in enumerate(
            quiz
        ):

            answer = st.radio(
                question["question"],
                question["options"],
                key=f"quiz_{i}",
                index=None,
            )


            answers.append(
                (
                    answer,
                    question["answer"],
                )
            )


        quiz_submit = st.form_submit_button(
            "Submit Assessment",
            type="primary",
        )


    if quiz_submit:

        score = sum(
            1
            for answer, correct
            in answers
            if answer == correct
        )


        st.success(
            f"Assessment Score: "
            f"{score}/{len(quiz)}"
        )


        log_event(
            AUDIT_PATH,
            CURRENT_USER,
            "TRAINING_ASSESSMENT_COMPLETED",
            "SOP",
            SOP_ID,
            (
                f"Training quiz score "
                f"{score}/{len(quiz)}"
            ),
        )


# =============================================================================
# AUDIT TRAIL
# =============================================================================

elif page == "📜 Audit Trail":

    st.title(
        "📜 Enterprise Audit Trail"
    )

    st.caption(
        "Regulatory traceability for AI actions, human approvals and system events."
    )


    if not st.session_state.audit_logged_once:

        log_event(
            AUDIT_PATH,
            CURRENT_USER,
            "AUDIT_TRAIL_VIEWED",
            "SOP",
            SOP_ID,
            "Audit trail viewed.",
        )


        st.session_state.audit_logged_once = True


    audit_df = load_audit(
        AUDIT_PATH
    )


    if (
        audit_df is None
        or audit_df.empty
    ):

        st.info(
            "No audit events available."
        )


    else:

        c1, c2 = st.columns(2)


        action_values = sorted(
            audit_df.action.dropna()
            .unique()
            .tolist()
        )


        user_values = sorted(
            audit_df.user.dropna()
            .unique()
            .tolist()
        )


        action_filter = c1.multiselect(
            "Filter Action",
            action_values,
        )


        user_filter = c2.multiselect(
            "Filter User",
            user_values,
        )


        filtered = audit_df.copy()


        if action_filter:

            filtered = filtered[
                filtered.action.isin(
                    action_filter
                )
            ]


        if user_filter:

            filtered = filtered[
                filtered.user.isin(
                    user_filter
                )
            ]


        st.dataframe(
            filtered,
            use_container_width=True,
            hide_index=True,
            height=520,
        )


        st.caption(
            f"Showing {len(filtered)} "
            f"of {len(audit_df)} events."
        )


        csv = filtered.to_csv(
            index=False
        ).encode(
            "utf-8"
        )


        st.download_button(
            "⬇️ Export Audit Trail",
            csv,
            "audit_trail_export.csv",
            "text/csv",
        )


st.markdown("---")


render_html(
    f"""
    <div style="
        text-align:center;
        padding:20px;

        border-radius:18px;

        background:
            linear-gradient(
                90deg,
                rgba(20,184,166,.06),
                rgba(139,92,246,.06),
                rgba(249,115,22,.06)
            );

        border:
            1px solid rgba(255,255,255,.06);
    ">

        <span style="
            color:{PRIMARY};
            font-weight:900;
        ">
            PROCESS GENOME AI
        </span>

        &nbsp;·&nbsp;

        <span style="
            color:{PURPLE};
        ">
            EXL Enterprise Process Intelligence
        </span>

        &nbsp;·&nbsp;

        <span style="
            color:{ORANGE};
        ">
            Dynamic SOP Governance
        </span>

        &nbsp;·&nbsp;

        <span style="
            color:{PINK};
        ">
            AI + Human Oversight
        </span>

        <br><br>

        <span style="
            color:#475569;
            font-size:11px;
        ">
            Enterprise AI Governance Demonstrator
        </span>

    </div>
    """
)
