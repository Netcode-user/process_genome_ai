"""
rag_engine.py
-------------
Retrieval-Augmented Generation orchestration layer.

Builds the vector index from the Process Genome (chunked per step) plus
historical mutation/audit context, exposes a `.retrieve()` for grounding,
and a `.generate()` that produces an SOP-drafting response -- calling
Azure OpenAI chat completions when credentials are configured, otherwise
falling back to a deterministic, template-driven generator so the demo
always works end-to-end offline.
"""

from __future__ import annotations
import os
from typing import List, Dict
from core.embeddings import EmbeddingEngine
from core.vector_store import VectorStore
from core.genome import ProcessGenome


class RAGEngine:
    def __init__(self, genome: ProcessGenome, extra_docs: List[Dict] = None):
        self.embedder = EmbeddingEngine()
        chunks = genome.to_chunks()
        if extra_docs:
            chunks.extend(extra_docs)

        texts = [c["text"] for c in chunks]
        metas = [c["metadata"] for c in chunks]

        # TF-IDF backend needs to be fit on the corpus first
        if self.embedder.backend == "tfidf":
            self.embedder.fit(texts)

        vecs = self.embedder.encode(texts)
        self.store = VectorStore(dim=vecs.shape[1])
        self.store.add(vecs, texts, metas)

        self.llm_backend = "template"
        if os.getenv("AZURE_OPENAI_API_KEY") and os.getenv("AZURE_OPENAI_ENDPOINT"):
            try:
                from openai import AzureOpenAI  # noqa: F401
                self.chat_client = AzureOpenAI(
                    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
                    api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-01"),
                    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
                )
                self.chat_deployment = os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT", "gpt-4o")
                self.llm_backend = "azure_openai"
            except Exception:
                self.llm_backend = "template"

    def retrieve(self, query: str, top_k: int = 4):
        qvec = self.embedder.encode([query])[0]
        return self.store.search(qvec, top_k=top_k)

    def generate_sop_draft(self, process_description: str, domain_context: str = "loan underwriting") -> Dict:
        """Retrieve grounding context, then draft a new SOP section / step set."""
        retrieved = self.retrieve(process_description, top_k=4)
        context_snippets = [r[0] for r in retrieved]

        if self.llm_backend == "azure_openai":
            prompt = (
                f"You are a process compliance expert drafting a Standard Operating Procedure "
                f"for a {domain_context} process.\n\nExisting related SOP steps (context):\n"
                + "\n".join(f"- {c}" for c in context_snippets)
                + f"\n\nDraft SOP steps for the following new/changed process requirement:\n"
                f"{process_description}\n\n"
                "Return 3-6 numbered steps, each with: step name, description, responsible role, "
                "expected duration in minutes, and risk level (Low/Medium/High/Critical)."
            )
            resp = self.chat_client.chat.completions.create(
                model=self.chat_deployment,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=800,
            )
            draft_text = resp.choices[0].message.content
            return {"draft": draft_text, "grounded_on": context_snippets, "backend": "Azure OpenAI (GPT-4o)"}

        # ---- Template fallback (deterministic, offline) ----
        draft_text = _template_sop_draft(process_description, context_snippets, domain_context)
        return {"draft": draft_text, "grounded_on": context_snippets, "backend": "Local Template Generator (offline mode)"}


def _template_sop_draft(process_description: str, context_snippets: List[str], domain_context: str) -> str:
    risk_kw = {
        "fraud": "High", "compliance": "High", "regulat": "High", "kyc": "High",
        "valuation": "High", "credit": "Medium", "income": "Medium", "document": "Low",
        "intake": "Low", "notif": "Low",
    }
    desc_lower = process_description.lower()
    inferred_risk = "Medium"
    for kw, lvl in risk_kw.items():
        if kw in desc_lower:
            inferred_risk = lvl
            break

    steps = [
        ("Step 1 - Trigger & Intake", f"Capture the triggering event for: {process_description}. Log into the process management system with a unique case reference.", "Process Owner", 10, "Low"),
        ("Step 2 - Data Validation", "Validate all required inputs against the source-of-truth systems and flag incomplete records for exception handling.", "Ops Analyst", 15, inferred_risk),
        ("Step 3 - AI-Assisted Risk Check", "Run the automated risk/fraud/compliance scoring engine against the case and attach the resulting confidence score.", "System / Risk Analyst", 5, "Medium"),
        ("Step 4 - Specialist Review", f"Route to the appropriate specialist for manual assessment when AI confidence falls below threshold or risk = {inferred_risk}.", "Senior Analyst", 20, inferred_risk),
        ("Step 5 - Approval & Sign-off", "Obtain the appropriate level of human approval based on risk tier before the case can proceed.", "Approving Manager", 10, "Medium"),
        ("Step 6 - Closure & Audit Logging", "Close the case, notify stakeholders, and write an immutable audit trail entry capturing every decision made.", "System", 5, "Low"),
    ]
    lines = [f"### AI-Drafted SOP: {process_description}", f"_Domain: {domain_context} | Grounded on {len(context_snippets)} existing SOP step(s) via RAG retrieval._\n"]
    for name, desc, owner, dur, risk in steps:
        lines.append(f"**{name}**  \n{desc}  \n*Responsible:* {owner} | *Expected duration:* {dur} min | *Risk level:* {risk}\n")
    return "\n".join(lines)
