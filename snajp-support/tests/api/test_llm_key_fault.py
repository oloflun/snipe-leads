"""En LLM-nyckel som inte går att skicka ska upptäckas FÖRE första anropet.

Bakgrunden är mätt i drift. `/health/ready` svarade "riktig agent aktiv" med en
nyckel som innehöll ett tecken över ASCII. Nyckeln gick i huvudet
`Authorization: Bearer <nyckel>`, och httpx kodar huvudvärden som ASCII — så
varje agentkörning föll med
`'ascii' codec can't encode character '\\xe0' in position 7`. Position 7 är
första tecknet efter "Bearer ".

Felet var alltså inte en kraschande tjänst utan en tjänst som rapporterade sig
frisk och inte var det. Samma klass som migration 029: trovärdigt men fel.
"""

from __future__ import annotations

import pytest

from app.config import Settings


def _settings(**kwargs) -> Settings:
    return Settings(llm_provider="deepseek", **kwargs)


def test_ren_ascii_nyckel_ar_giltig():
    s = _settings(deepseek_api_key="sk-" + "a" * 32)
    assert s.llm_key_fault() is None
    assert not s.is_simulation()


def test_tom_nyckel_ar_simulering_inte_fel():
    """Ingen nyckel är ett LÄGE, inte ett fel. Att blanda ihop dem hade gjort
    varje utvecklarmiljö röd."""
    s = _settings(deepseek_api_key="")
    assert s.llm_key_fault() is None
    assert s.is_simulation()


@pytest.mark.parametrize(
    "key, position",
    [
        ("\xe0k\xe0" + "a" * 36, 0),          # exakt formen som föll i drift
        ("sk-" + "a" * 20 + "ö" + "a" * 10, 23),
        # Hårt mellanslag (U+00A0). Skrivet som escape med flit: som literalt
        # tecken är det osynligt i diffen, vilket är exakt hur det hamnar i en
        # nyckel någon klistrat in från en webbsida.
        ("sk-" + "a" * 30 + " ", 33),
    ],
)
def test_icke_ascii_nyckel_pekas_ut_med_position(key: str, position: int):
    s = _settings(deepseek_api_key=key)
    fault = s.llm_key_fault()
    assert fault is not None, "En nyckel som inte kan skickas måste rapporteras."
    assert f"position {position}" in fault, (
        "Positionen måste stå i beskedet. Utan den söker den som läser efter "
        "ett osynligt tecken i en sträng som inte får skrivas ut."
    )


def test_trasig_nyckel_tvingar_simuleringslage():
    """Annars påstår tjänsten att den är live och faller på första anropet —
    ett läge som ser friskt ut i varje kontroll utom den som kostar en kund."""
    s = _settings(deepseek_api_key="\xe0k\xe0" + "a" * 36)
    assert s.is_simulation()
