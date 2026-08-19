"""
explainability.py
------------------
Produces human-readable, feature-attributed explanations for AI decisions:
drift flags, risk scores, and mutation recommendations. This is a
lightweight, transparent stand-in for SHAP-style attribution -- each
factor's contribution is computed directly from the same weighted formula
used by drift_detection.py / risk_engine.py, so the explanation is always
mathematically consistent with the score shown to the user (no black box).
"""

from __future__ import annotations
import pandas as pd


def explain_drift_row(row: pd.Series) -> dict:
    dev_contribution = round(0.55 * min(row.deviation_rate_pct, 100) * row.risk_weight, 1)
    dur_component = max(row.duration_overrun_pct, 0)
    dur_contribution = round(0.45 * min(dur_component, 150) / 1.5 * row.risk_weight, 1)

    factors = [
        {
            "factor": "Deviation Frequency",
            "value": f"{row.deviation_rate_pct}% of executions deviated",
            "contribution": dev_contribution,
            "explanation": (
                f"Out of {int(row.executions)} logged executions of '{row.step_name}', "
                f"{int(row.deviation_count)} deviated from the documented SOP path. "
                "This is the single strongest signal of process drift."
            ),
        },
        {
            "factor": "Duration Overrun",
            "value": f"{row.duration_overrun_pct}% vs. baseline",
            "contribution": dur_contribution,
            "explanation": (
                f"Average actual duration ({row.avg_actual_duration:.1f} min) compared to the "
                f"SOP-documented expectation ({row.expected_duration} min). Sustained overruns "
                "usually indicate an undocumented manual workaround or a resourcing bottleneck."
            ),
        },
        {
            "factor": "Baseline Risk Tier",
            "value": row.risk_level,
            "contribution": None,
            "explanation": (
                f"This step is classified '{row.risk_level}' risk in the governing SOP, so drift "
                f"here is amplified by a {row.risk_weight}x multiplier before contributing to the "
                "Drift Severity Index -- deviations in high-risk / compliance-sensitive steps matter "
                "disproportionately more than in low-risk steps."
            ),
        },
    ]
    return {
        "step_name": row.step_name,
        "drift_severity_index": row.drift_severity_index,
        "drift_band": row.drift_band,
        "factors": factors,
        "narrative": (
            f"**{row.step_name}** scored a Drift Severity Index of **{row.drift_severity_index}/100** "
            f"(**{row.drift_band}**). This is driven primarily by "
            f"{'deviation frequency' if dev_contribution >= dur_contribution else 'duration overrun'} "
            f"({max(dev_contribution, dur_contribution)} of {round(dev_contribution + dur_contribution, 1)} weighted points), "
            f"amplified by the step's '{row.risk_level}' baseline risk classification."
        ),
    }


def explain_mutation(mutation_row: pd.Series) -> dict:
    return {
        "mutation": mutation_row.mutation_description,
        "type": mutation_row.mutation_type,
        "fitness_score": mutation_row.fitness_score,
        "narrative": (
            f"This **{mutation_row.mutation_type}** mutation was scored a fitness of "
            f"**{mutation_row.fitness_score}** by the genome evolution engine. Fitness combines "
            "(a) projected cycle-time reduction, (b) projected risk-adjusted compliance impact, and "
            "(c) similarity to previously human-approved mutations of the same type retrieved via RAG. "
            "A score above 0.80 is auto-routed for fast-track human approval; below that, it queues "
            "for standard committee review."
        ),
    }
