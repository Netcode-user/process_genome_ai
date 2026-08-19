# process_genome_ai
# 🧬 Process Genome AI: Dynamic SOP Evolution

**An AI system that treats every Standard Operating Procedure as a living genome — continuously observed, diagnosed for drift, evolved through AI-proposed mutations, and always kept under human control.**

Built for the EXL internal hackathon — demo domain: **Loan Underwriting**.

---

## 1. The Problem

SOPs are written once and quietly rot. Regulators update requirements, teams
invent workarounds under deadline pressure, tools change — and six months
later nobody can say with confidence what the process *actually* is anymore.
Audits become archaeology. Risk hides in the gap between the documented SOP
and the executed reality.

## 2. The Idea: SOPs as a Genome

We model an SOP the way biology models an organism:

| Biology | Process Genome AI |
|---|---|
| Gene | A single SOP step (owner, risk, duration, compliance ref) |
| Genome | The full ordered SOP |
| Mutation | An AI-proposed change to a step (recalibrate, strengthen control, merge, reorder) |
| Natural selection | Fitness scoring (cycle-time gain + risk reduction + precedent alignment) |
| Expression | A mutation becomes the new live baseline **only after human approval** |

This framing gives us a single coherent data model that naturally supports
versioning, diffing, drift detection, and an auditable evolution history —
instead of eleven disconnected point tools.

## 3. Architecture

```
                         ┌───────────────────────────┐
   Process Execution     │      Streamlit Frontend     │
   Logs (Databricks /    │  Command Center · Genome    │
   event stream)  ───────▶  Explorer · Drift · Risk ·  │
                         │  Approval · Monitoring ·    │
   SOP Master (genome    │  Alerts · Comparison ·      │
   baseline)      ───────▶  Training · Audit Trail     │
                         └──────────────┬───────────────┘
                                        │
        ┌───────────────────────────────┼───────────────────────────────┐
        ▼                               ▼                               ▼
┌───────────────┐            ┌───────────────────┐            ┌──────────────────┐
│ Drift Engine    │            │   RAG Engine        │            │  Mutation Engine   │
│ (duration,      │            │ Chunking → Embed →   │            │ Fitness scoring →  │
│ frequency,       │            │ FAISS Vector Store → │            │ Human Approval →   │
│ structural,      │            │ Azure OpenAI / local  │            │ Genome Versioning  │
│ trend drift)     │            │ template generation   │            │                    │
└───────────────┘            └───────────────────┘            └──────────────────┘
        │                               │                               │
        └───────────────┬───────────────┴───────────────┬───────────────┘
                         ▼                               ▼
                ┌──────────────────┐            ┌──────────────────┐
                │  Risk Engine        │            │ Explainability     │
                │  + Predictive Alerts │            │  (transparent,      │
                │                     │            │  formula-linked)    │
                └──────────────────┘            └──────────────────┘
                         │
                         ▼
                ┌──────────────────┐
                │  Immutable Audit    │
                │  Trail (CSV / Delta) │
                └──────────────────┘
```

**Production target (Databricks + Azure):** raw process events land in a
Bronze Delta table, get modeled into the Silver "genome" + "execution"
tables, Gold aggregates feed the dashboard; Unity Catalog governs access;
Azure OpenAI (via private endpoint) powers generation; the same Streamlit
app (or a Databricks App) sits on top unchanged. See `utils/data_loader.py`
for the exact swap points — CSV readers become Delta/SQL reads with no
other code changes required.

## 4. Tech Stack

| Layer | Technology |
|---|---|
| App / UI | Python, Streamlit, Plotly |
| LLM | Azure OpenAI (GPT-4o) — with an offline deterministic template fallback |
| Retrieval | RAG: chunking → embeddings → vector search |
| Embeddings | Azure OpenAI `text-embedding-3-small` → sentence-transformers → TF-IDF (3-tier graceful fallback) |
| Vector store | FAISS (`IndexFlatL2`), with a NumPy cosine-similarity fallback if FAISS isn't installed |
| Data platform (target) | Databricks Lakehouse (Delta tables, Unity Catalog) |
| Data | Pandas, NumPy, scikit-learn |

**Why the fallback chains matter:** the app runs completely offline —
useful when demoing on a jury laptop with no live Azure credentials or
internet — and upgrades itself automatically to live Azure OpenAI + FAISS
the moment real credentials/packages are available. Nothing in the UI or
downstream logic needs to change either way.

## 5. Feature Map

| # | Feature | Where |
|---|---|---|
| 1 | **AI SOP Generation** (RAG-grounded drafting) | `🤖 AI SOP Generator` |
| 2 | **Process Genome** (SOP-as-genome model + DNA-style visualization) | `🧬 Process Genome Explorer` |
| 3 | **SOP Drift Detection** (duration / frequency / structural / trend drift) | `📉 SOP Drift Detection` |
| 4 | **Risk Detection** (incident scoring + composite process risk) | `⚠️ Risk & Explainability` |
| 5 | **AI Explainability** (factor-level, formula-consistent narratives) | `⚠️ Risk & Explainability` |
| 6 | **Human Approval** (mutation approve/reject workflow) | `✅ Human Approval Workflow` |
| 7 | **Real-Time Monitoring** (simulated live execution stream) | `📡 Real-Time Monitoring` |
| 8 | **Predictive Alerts** (trend extrapolation + threshold alerts) | `🔔 Predictive Alerts` |
| 9 | **Process Comparison** (genome generation diff + fitness trend) | `🔀 Process Comparison` |
| 10 | **Training Generator** (auto slide deck + quiz from live genome) | `🎓 Training Generator` |
| 11 | **Audit Trail** (immutable, filterable, exportable log) | `📜 Audit Trail` |
| 12 | **Process Dashboard** (KPIs, gauges, trend charts) | `🏠 Command Center` |

## 6. Getting Started

```bash
# 1. Create a virtual environment (recommended)
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. (Optional) enable live Azure OpenAI generation
cp .env.example .env
# fill in AZURE_OPENAI_API_KEY / AZURE_OPENAI_ENDPOINT, then:
export $(cat .env | xargs)      # or use python-dotenv / your shell's env loader

# 4. Run the app
streamlit run app.py
```

The app opens at `http://localhost:8501`. No Azure credentials, FAISS, or
internet connection are required to run the full demo — every AI component
has a deterministic offline fallback (see Tech Stack above).

## 7. Included Sample Data (`/data`)

| File | Rows | Description |
|---|---|---|
| `sop_master.csv` | 15 | The baseline Process Genome — Loan Underwriting SOP v3.2 |
| `process_execution_logs.csv` | ~3,870 | 260 simulated loan cases executed against the SOP, with injected drift patterns (skips, reorders, overruns) that increase over time to demonstrate trend detection |
| `sop_versions.csv` | 6 | Genome generation / mutation history with fitness scores |
| `risk_incidents.csv` | 42 | Logged risk incidents across severities and steps |
| `audit_trail.csv` | 120 (+ live) | Seed audit history; the app appends real events as you use it |

All data is synthetic and safe to demo publicly.

## 8. Demo Script (suggested 5-minute jury walkthrough)

1. **Command Center** — "Here's our process risk score, live, computed from real drift + incident data."
2. **Process Genome Explorer** — "This is the SOP encoded as a genome — you can see risk visually as a DNA strand."
3. **SOP Drift Detection → Structural tab** — pick a case, show a skipped step live.
4. **AI SOP Generator** — type a new regulatory requirement, generate a grounded draft SOP in seconds.
5. **Human Approval Workflow** — approve an AI-proposed mutation; watch it hit the Audit Trail instantly.
6. **Predictive Alerts** — show the trend line forecasting a step crossing into critical drift *before* it happens.
7. **Training Generator** — show the auto-refreshed training deck/quiz for the just-approved change.

## 9. Roadmap Beyond the Hackathon

- Wire `utils/data_loader.py` to live Databricks Delta tables (Bronze/Silver/Gold) with CDC via Debezium for true real-time ingestion.
- Replace the rule-based mutation proposer with an LLM agent (ReAct/LangGraph) reasoning over retrieved precedent mutations.
- Add a knowledge-graph layer linking SOP steps to regulatory clauses for automated compliance-impact analysis on every mutation.
- Move audit logging to an append-only, WORM-compliant store for regulatory-grade immutability.

## 10. Project Structure

```
process_genome_ai/
├── app.py                      # Streamlit app (all pages/tabs)
├── requirements.txt
├── .env.example
├── .streamlit/config.toml      # theme
├── core/
│   ├── genome.py                # Process Genome data model + chunking
│   ├── embeddings.py            # 3-tier embedding provider
│   ├── vector_store.py          # FAISS wrapper + NumPy fallback
│   ├── rag_engine.py            # Retrieval + generation orchestration
│   ├── drift_detection.py       # Duration/frequency/structural/trend drift
│   ├── risk_engine.py           # Composite risk scoring
│   ├── explainability.py        # Factor-level AI explanations
│   ├── mutation_engine.py       # Mutation proposal + fitness scoring
│   ├── alerts.py                # Trend extrapolation + predictive alerts
│   ├── training_generator.py    # Auto training deck + quiz
│   └── audit.py                 # Append-only audit logging
├── utils/
│   └── data_loader.py           # Cached CSV loaders (Delta-ready)
└── data/
    ├── sop_master.csv
    ├── process_execution_logs.csv
    ├── sop_versions.csv
    ├── risk_incidents.csv
    └── audit_trail.csv
```

## Output Screenshots

![image 1](./Screenshots/Screenshot%201.jpeg)
-----------------------------------------------
![image 2](./Screenshots/Screenshot%2010.jpeg)
-----------------------------------------------
![image 3](./Screenshots/Screenshot%2011.jpeg)
-----------------------------------------------
![image 4](./Screenshots/Screenshot%2012.jpeg)
-----------------------------------------------
![image 5](./Screenshots/Screenshot%2013.jpeg)
-----------------------------------------------
![image 6](./Screenshots/Screenshot%2014.jpeg)
-----------------------------------------------
![image 7](./Screenshots/Screenshot%2015.jpeg)
-----------------------------------------------
![image 8](./Screenshots/Screenshot%2016.jpeg)
-----------------------------------------------
![image 9](./Screenshots/Screenshot%2017.jpeg)
-----------------------------------------------
![image 10](./Screenshots/Screenshot%2018.jpeg)
-----------------------------------------------
![image 11](./Screenshots/Screenshot%2019.jpeg)
-----------------------------------------------
![image 12](./Screenshots/Screenshot%202.jpeg)
-----------------------------------------------
![image 13](./Screenshots/Screenshot%2020.jpeg)
-----------------------------------------------
![image 14](./Screenshots/Screenshot%2021.jpeg)
-----------------------------------------------
![image 15](./Screenshots/Screenshot%2022.jpeg)
-----------------------------------------------
![image 16](./Screenshots/Screenshot%2023.jpeg)
-----------------------------------------------
![image 17](./Screenshots/Screenshot%2024.jpeg)
-----------------------------------------------
![image 18](./Screenshots/Screenshot%2025.jpeg)
-----------------------------------------------
![image 19](./Screenshots/Screenshot%2026.jpeg)
-----------------------------------------------
![image 20](./Screenshots/Screenshot%2027.jpeg)
-----------------------------------------------
![image 21](./Screenshots/Screenshot%2028.jpeg)
-----------------------------------------------
![image 22](./Screenshots/Screenshot%2029.jpeg)
-----------------------------------------------
![image 23](./Screenshots/Screenshot%203.jpeg)
-----------------------------------------------
![image 24](./Screenshots/Screenshot%2030.jpeg)
-----------------------------------------------
![image 25](./Screenshots/Screenshot%2031.jpeg)
-----------------------------------------------
![image 26](./Screenshots/Screenshot%204.jpeg)
-----------------------------------------------
![image 27](./Screenshots/Screenshot%205.jpeg)
-----------------------------------------------
![image 28](./Screenshots/Screenshot%206.jpeg)
-----------------------------------------------
![image 29](./Screenshots/Screenshot%207.jpeg)
----------------------------------------------
![image 30](./Screenshots/Screenshot%208.jpeg)
----------------------------------------------
![image 31](./Screenshots/Screenshot%209.jpeg)
------------------------------------------------
