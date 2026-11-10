"""Skälet när faktagrinden stoppar ett utkast (hittat av evalsviten, 2026-11-10).

Grinden fäller på två saker: påståenden utan stöd i underlaget, och meningar
som gissar om mottagaren. Skälet som lämnades till människan skrev bara ut den
första listan. Ett utkast som stoppades för en gissning fick skälet
"påståenden utan stöd …: []", en tom lista, och den som skulle ta över såg inte
vad som var fel.
"""

from __future__ import annotations

from app.agent.leads_agent import stoppskal_grundning


def test_gissningen_star_i_skalet_nar_inga_pastaenden_saknar_stod():
    skal = stoppskal_grundning(
        {"ok": False, "unsupported_after": [], "gissningar_after": ["Ni får säkert många frågor om takskottning."]}
    )

    assert "[]" not in skal
    assert "takskottning" in skal and "gissar om mottagaren" in skal
    assert skal.endswith("Utkastet köas inte.")


def test_ostodda_pastaenden_star_i_skalet():
    skal = stoppskal_grundning({"ok": False, "unsupported_after": ["percent: '30 %'"], "gissningar_after": []})

    assert "30 %" in skal and "utan stöd i underlaget" in skal
    assert "gissar" not in skal


def test_bada_slagen_star_i_skalet():
    skal = stoppskal_grundning(
        {"ok": False, "unsupported_after": ["number: '12000'"], "gissningar_after": ["Ni har nog ont om tid."]}
    )

    assert "12000" in skal and "ont om tid" in skal


def test_ett_skal_utan_uppgifter_sager_det_rakt_ut():
    skal = stoppskal_grundning({"ok": False})

    assert "[]" not in skal and "None" not in skal
    assert skal.endswith("Utkastet köas inte.")


def test_bada_kedjorna_anvander_samma_skal():
    from pathlib import Path

    rot = Path(__file__).resolve().parents[2] / "app" / "agent"
    for fil in ("leads_agent.py", "leads_research_v2.py"):
        kalla = (rot / fil).read_text(encoding="utf-8")
        assert "stoppskal_grundning(grounding)" in kalla, fil
        assert "grounding['unsupported_after']}. Utkastet köas inte." not in kalla, fil
