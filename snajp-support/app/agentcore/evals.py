"""Evalgrind (plan Del B, Del C punkt 5).

En pinnad kund flyttas ALDRIG till en ny baseline utan att först ha passerat
sina egna evals i skuggläge (INV-AGENT-002): ny baseline -> skuggkörning mot
kundens evals -> diff per fall -> kunden godkänner -> pin flyttas. Varje
vendorad mk:-skill har redan evals/evals.json; cs:/sa: saknar det formatet
idag och load_skill_evals returnerar tom lista för dem tills tenant-evals
(agent_evals-tabellen, migration 010) finns.
"""

from __future__ import annotations

import json
from dataclasses import dataclass

from .registry import parse_skill_name


@dataclass(frozen=True)
class EvalCase:
    id: str
    prompt: str
    expected_output: str


def load_skill_evals(skill: str) -> list[EvalCase]:
    ref = parse_skill_name(skill)
    evals_path = ref.dir / "evals" / "evals.json"
    if not evals_path.is_file():
        return []
    data = json.loads(evals_path.read_text(encoding="utf-8"))
    raw_cases = data.get("evals", []) if isinstance(data, dict) else data
    return [
        EvalCase(
            id=str(case.get("id", i)),
            prompt=case.get("prompt", ""),
            expected_output=case.get("expected_output", ""),
        )
        for i, case in enumerate(raw_cases)
    ]


@dataclass(frozen=True)
class PromotionDecision:
    approved: bool
    regressions: tuple[str, ...] = ()


def decide_promotion(
    *,
    baseline_scores: dict[str, float],
    candidate_scores: dict[str, float],
    tenant_approved: bool,
) -> PromotionDecision:
    """INV-AGENT-002: en bump som sänker EN kunds evalpoäng blockeras i test,
    oavsett godkännande. Godkännande krävs även när inget regredierar —
    en pin flyttas aldrig tyst."""
    regressions = tuple(
        eval_id
        for eval_id, base_score in baseline_scores.items()
        if candidate_scores.get(eval_id, 0.0) < base_score
    )
    if regressions:
        return PromotionDecision(approved=False, regressions=regressions)
    return PromotionDecision(approved=tenant_approved)
