"""
training_generator.py
----------------------
Auto-generates onboarding/training material and a quick-check quiz from
the current Process Genome -- so every SOP mutation that gets approved
automatically produces refreshed training content, closing the loop
between "process changed" and "workforce retrained".
"""

from __future__ import annotations
from typing import List, Dict
from core.genome import ProcessGenome


def generate_training_deck(genome: ProcessGenome) -> List[Dict]:
    slides = [{
        "title": f"Training: {genome.sop_id} ({genome.version})",
        "bullets": [
            f"{len(genome.genes)} process steps",
            f"Estimated total cycle time: {genome.total_expected_duration()} minutes",
            "Covers roles: " + ", ".join(sorted(set(g.owner_role for g in genome.genes))),
        ],
    }]
    for g in genome.genes:
        slides.append({
            "title": f"Step {g.step_no}: {g.step_name}",
            "bullets": [
                g.description,
                f"Owner: {g.owner_role}",
                f"Target duration: {g.expected_duration_min} min",
                f"Risk level: {g.risk_level}  |  Compliance ref: {g.compliance_ref}",
            ],
        })
    slides.append({
        "title": "Key Takeaways",
        "bullets": [
            "Always follow the documented step order -- reordering counts as process drift.",
            "High/Critical risk steps require full documentation; do not skip evidentiary steps.",
            "Report any workaround or blocker immediately rather than improvising silently.",
        ],
    })
    return slides


def generate_quiz(genome: ProcessGenome, n_questions: int = 5) -> List[Dict]:
    import random
    random.seed(7)
    genes = genome.genes
    questions = []

    sample_genes = random.sample(genes, min(n_questions, len(genes)))
    for g in sample_genes:
        wrong_owners = list({x.owner_role for x in genes if x.owner_role != g.owner_role})
        options = [g.owner_role] + random.sample(wrong_owners, min(3, len(wrong_owners)))
        random.shuffle(options)
        questions.append({
            "question": f"Who is responsible for '{g.step_name}'?",
            "options": options,
            "answer": g.owner_role,
        })
    return questions
