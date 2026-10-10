"""Textändringar i en läst skill (PlaybookStep.radandringar, 2026-10-06).

Skillfilen rörs aldrig (INV-SKILL-005). Ändringen sker på den lästa texten,
kräver ett skäl (INV-SKILL-003) och faller vid import om texten inte längre
finns i skillen, så att den aldrig tyst slutar gälla.
"""

import pytest

from app.agentcore.packs import PlaybookStep, RadandringSaknasError, ScopeWithoutRationaleError
from app.agentcore.registry import load_section
from app.leads.outreach_playbook import OUTREACH_V2

_RAD = "[Desire: Brief proof point - similar company result]"


def _steg(**k) -> PlaybookStep:
    return PlaybookStep(
        skill="sa:draft-outreach", requires=("offer_selected",), scope=("§ Execution Flow",), rationale="test", **k
    )


def test_andringen_tillampas_pa_den_lasta_texten_och_filen_ar_orord():
    steg = _steg(radandringar=((_RAD, "[Desire: produktens nytta]", "påhittade case"),))
    assert _RAD in load_section("sa:draft-outreach", "Execution Flow"), "skillfilen ska vara orörd"
    text = steg.render()
    assert _RAD not in text and "[Desire: produktens nytta]" in text


def test_text_som_inte_finns_faller_vid_import():
    with pytest.raises(RadandringSaknasError):
        _steg(radandringar=(("Den här raden finns inte i skillen", "", "skäl"),))


def test_andring_utan_skal_faller():
    with pytest.raises(ScopeWithoutRationaleError):
        _steg(radandringar=((_RAD, "", " "),))


def test_utkaststeget_bar_inga_liknande_bolag_case():
    text = OUTREACH_V2.steps[0].render()
    for monster in ("Similar Company", "similar company result", "Case study from a similar", "research-prospect"):
        assert monster not in text, monster
    assert "Step 3: Identify Hook" in text, "arbetsflödet ska stå kvar"
