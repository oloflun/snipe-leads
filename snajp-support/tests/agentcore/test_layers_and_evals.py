from app.agentcore.evals import PromotionDecision, decide_promotion, load_skill_evals
from app.agentcore.layers import Baseline, ComposedRun, RunLayer, TenantLayer
from app.agentcore.packs import Playbook, PlaybookStep


def test_pinned_pack_version_combines_baseline_and_playbook():
    baseline = Baseline(manifest_hash="abc123")
    playbook = Playbook(
        name="support/v1",
        steps=(PlaybookStep(skill="cs:ticket-triage", requires=("context_pack",)),),
    )
    tenant = TenantLayer(
        tenant_id="livrustning",
        tone="varm och saklig",
        instructions_md="",
        taxonomy=("garanti", "leverans"),
    )
    run = RunLayer(channel="web")
    composed = ComposedRun(baseline=baseline, playbook=playbook, tenant=tenant, run=run)
    assert composed.pinned_pack_version == "abc123:support/v1"


def test_load_skill_evals_returns_cases_for_a_mk_skill():
    cases = load_skill_evals("mk:ab-testing")
    assert len(cases) > 0
    assert cases[0].prompt


def test_load_skill_evals_returns_empty_for_a_cs_skill_without_evals_dir():
    # cs:/sa: (knowledge-work-plugins) don't ship evals/evals.json today —
    # tenant-level evals (agent_evals table, migration 010) cover them instead.
    assert load_skill_evals("cs:ticket-triage") == []


def test_promotion_blocked_on_any_regression_even_if_tenant_approved():
    decision = decide_promotion(
        baseline_scores={"eval-1": 0.9, "eval-2": 0.8},
        candidate_scores={"eval-1": 0.95, "eval-2": 0.7},  # eval-2 regredierar
        tenant_approved=True,
    )
    assert decision == PromotionDecision(approved=False, regressions=("eval-2",))


def test_promotion_requires_explicit_tenant_approval_even_with_no_regression():
    decision = decide_promotion(
        baseline_scores={"eval-1": 0.9},
        candidate_scores={"eval-1": 0.95},
        tenant_approved=False,
    )
    assert decision.approved is False
    assert decision.regressions == ()


def test_promotion_approved_when_no_regression_and_tenant_approved():
    decision = decide_promotion(
        baseline_scores={"eval-1": 0.9},
        candidate_scores={"eval-1": 0.95},
        tenant_approved=True,
    )
    assert decision.approved is True
