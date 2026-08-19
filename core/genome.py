"""
genome.py
---------
Models an SOP as a "Process Genome": an ordered sequence of Genes (steps),
each carrying attributes (owner, risk, duration, compliance ref) analogous
to a biological gene carrying traits. Mutations (AI-suggested improvements)
are proposed against this genome, scored with a fitness function, and
routed through human approval before being "expressed" (activated) in the
live SOP.

This module also provides text-chunking utilities used to feed the RAG
vector store.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict
import pandas as pd


@dataclass
class Gene:
    step_no: int
    step_name: str
    description: str
    owner_role: str
    expected_duration_min: int
    risk_level: str
    compliance_ref: str

    def to_text(self) -> str:
        return (
            f"Step {self.step_no}: {self.step_name}. {self.description}. "
            f"Owner: {self.owner_role}. Expected duration: {self.expected_duration_min} min. "
            f"Risk level: {self.risk_level}. Compliance reference: {self.compliance_ref}."
        )

    def sequence_symbol(self) -> str:
        """Encode risk level as a genome 'base' for visualization (A/T/C/G style)."""
        return {"Low": "G", "Medium": "T", "High": "A", "Critical": "C"}.get(self.risk_level, "N")


@dataclass
class ProcessGenome:
    sop_id: str
    version: str
    genes: List[Gene] = field(default_factory=list)

    @classmethod
    def from_dataframe(cls, df: pd.DataFrame, sop_id: str, version: str = "v3.2") -> "ProcessGenome":
        genes = []
        subset = df[df.sop_id == sop_id].sort_values("step_no")
        for _, row in subset.iterrows():
            genes.append(Gene(
                step_no=int(row.step_no),
                step_name=row.step_name,
                description=row.description,
                owner_role=row.owner_role,
                expected_duration_min=int(row.expected_duration_min),
                risk_level=row.risk_level,
                compliance_ref=row.compliance_ref,
            ))
        return cls(sop_id=sop_id, version=version, genes=genes)

    def sequence_string(self) -> str:
        return "".join(g.sequence_symbol() for g in self.genes)

    def total_expected_duration(self) -> int:
        return sum(g.expected_duration_min for g in self.genes)

    def risk_composition(self) -> Dict[str, int]:
        comp = {"Low": 0, "Medium": 0, "High": 0, "Critical": 0}
        for g in self.genes:
            comp[g.risk_level] = comp.get(g.risk_level, 0) + 1
        return comp

    def to_chunks(self) -> List[Dict]:
        """One RAG chunk per gene (step) -- ideal granularity for retrieval."""
        return [{"text": g.to_text(), "metadata": {"sop_id": self.sop_id, "step_no": g.step_no,
                                                     "step_name": g.step_name, "risk_level": g.risk_level}}
                for g in self.genes]


def chunk_text(text: str, chunk_size: int = 400, overlap: int = 60) -> List[str]:
    """Simple sliding-window chunker for longer free-text documents (policy PDFs etc.)."""
    words = text.split()
    if len(words) <= chunk_size:
        return [text]
    chunks = []
    start = 0
    while start < len(words):
        end = start + chunk_size
        chunks.append(" ".join(words[start:end]))
        start = end - overlap
    return chunks
