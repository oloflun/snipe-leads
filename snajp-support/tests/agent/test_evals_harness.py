"""Eval-harnessens MÄTNING som ren funktion — domsluten ska gå att
falsifiera utan modell. Själva golden-körningen är scripts/kor_evals.py."""

from app.agent.evals import SUPPORT_GOLDEN, EvalCase, _mat_case

KB = ["Betalsätt\nVi tar Swish och kort.", "Leverans\nLeverans tar 2-5 arbetsdagar."]


def _resultat(**over):
    grund = {
        "escalated": False,
        "escalation_reason": None,
        "category": "betalning",
        "reply": "Du kan betala med Swish eller kort.",
    }
    grund.update(over)
    return grund


def test_ratt_utfall_ger_inga_fel():
    case = EvalCase(id="x", beskrivning="", message="Vilka betalsätt?", forvantat={"eskalerar": False, "kategori_i": ["betalning"]})
    assert _mat_case(case, _resultat(), KB) == []


def test_fel_eskaleringsbeslut_falls():
    case = EvalCase(id="x", beskrivning="", message="m", forvantat={"eskalerar": False})
    fel = _mat_case(case, _resultat(escalated=True, escalation_reason="oops"), KB)
    assert any("eskalerar" in f for f in fel)


def test_faithfulness_faller_pahittad_siffra():
    """Ragas-frågan, husets extraktor: en siffra som inte finns i KB eller i
    kundens meddelande är ett ostött claim."""
    case = EvalCase(id="x", beskrivning="", message="Hur snabb är leveransen?", forvantat={})
    fel = _mat_case(case, _resultat(reply="97 procent av paketen kommer fram inom en dag."), KB)
    assert any("faithfulness" in f for f in fel)


def test_faithfulness_godkanner_siffra_ur_kb():
    case = EvalCase(id="x", beskrivning="", message="Hur snabb är leveransen?", forvantat={})
    assert _mat_case(case, _resultat(reply="Leveransen tar 2-5 arbetsdagar."), KB) == []


def test_foljdfragekravet_falls_utan_fragetecken():
    case = EvalCase(id="x", beskrivning="", message="Hej", forvantat={"staller_foljdfraga": True})
    fel = _mat_case(case, _resultat(reply="Hej på dig."), KB)
    assert any("fråga" in f for f in fel)


def test_forbjudna_ord_falls_i_bade_svar_och_orsak():
    case = EvalCase(id="x", beskrivning="", message="m", forvantat={"far_inte_innehalla": ["retention"]})
    fel = _mat_case(
        case, _resultat(escalated=True, escalation_reason="retention_risk"), KB
    )
    assert any("retention" in f for f in fel)


def test_golden_setet_ar_verkliga_fall_med_matbara_krav():
    assert len(SUPPORT_GOLDEN) >= 7
    for case in SUPPORT_GOLDEN:
        assert case.beskrivning, f"{case.id}: golden-fall utan dokumenterat upphov"
        assert case.forvantat, f"{case.id}: inga mätbara egenskaper"
