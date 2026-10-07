"""En körning med en generell målgrupp ska hitta bolag (Sebbe 2026-10-07).

Körningarna 6ed99585 och f92ed14d i development: bransch "B2B", orterna
"Umeå, Luelå, Skellefteå". Registret kunde inte översätta "B2B" och gav None,
den öppna sökningen svarade [] i tre rundor, och körningen slutade som
"0 undersökta → 0 leads". Tre lager ska hindra det:

1. "B2B" (eller ingen bransch) söker brett i registret i kundens område.
2. Ger den öppna sökningen inget och registret inte användes, söks
   registret brett i stället för att rundan slutar tom.
3. Blir det ändå inget heter slutet `inga_traffar` och säger varför.
"""

from __future__ import annotations

import pytest

from app.leads import discovery
from app.leads import korning as iris_korning
from app.leads.sources import merinfo as m


@pytest.mark.anyio
async def test_b2b_soker_brett_i_registret(monkeypatch):
    sedda: list[tuple[str, str | None]] = []

    def _url(bransch, plats, sida):
        sedda.append((bransch, plats))
        return f"https://x/{bransch}/{plats}/{sida}"

    async def _tom(url, **_):
        return None

    monkeypatch.setattr(m, "listsida_url", _url)
    monkeypatch.setattr(m, "hamta", _tom)
    await m.sok({"industries": ["B2B"], "geography": ["Umeå", "Luelå", "Skellefteå"]}, 3)
    assert {b for b, _ in sedda} == set(m.BRED_B2B)
    assert {p for _, p in sedda} == {"umea", "skelleftea", "lulea"}


def test_specifik_bransch_soker_inte_brett():
    assert not m.ar_generisk_bransch(["E-utbildning"])
    assert m.ar_generisk_bransch(["B2B"])
    assert m.ar_generisk_bransch([])


@pytest.mark.anyio
async def test_tom_sokning_faller_tillbaka_pa_bred_registersokning(monkeypatch):
    monkeypatch.setenv("LEADS_MERINFO", "scrapegraph")
    monkeypatch.setenv("LEADS_KALLOR", "")
    anrop: list[bool] = []

    async def _sok(icp, antal, *, bred=False, **_k):
        anrop.append(bred)
        return [{"company_name": "Norrbygg AB", "website": "https://norrbygg.se"}] if bred else None

    async def _gemini(_prompt):
        return "[]"

    async def _utan(rader):
        return rader

    monkeypatch.setattr(m, "sok", _sok)
    monkeypatch.setattr(discovery, "_gemini_med_sokning", _gemini)
    monkeypatch.setattr("app.leads.platshallare.utan_platshallare", _utan)
    ut = await discovery.hitta_bolag({"industries": ["Nischbransch"], "geography": ["Umeå"]}, 2)
    assert [r["company_name"] for r in ut] == ["Norrbygg AB"]
    assert anrop == [False, True]


@pytest.mark.anyio
async def test_registrets_ja_ger_ingen_bred_extrasokning(monkeypatch):
    """Skyddsnätet är bara för när registret inte användes: ett ärligt [] ur
    registret ska inte kosta en andra, bred sökning."""
    monkeypatch.setenv("LEADS_MERINFO", "scrapegraph")
    monkeypatch.setenv("LEADS_KALLOR", "")
    anrop: list[bool] = []

    async def _sok(icp, antal, *, bred=False, **_k):
        anrop.append(bred)
        return []

    async def _gemini(_prompt):
        return "[]"

    async def _utan(rader):
        return rader

    monkeypatch.setattr(m, "sok", _sok)
    monkeypatch.setattr(discovery, "_gemini_med_sokning", _gemini)
    monkeypatch.setattr("app.leads.platshallare.utan_platshallare", _utan)
    assert await discovery.hitta_bolag({"industries": ["Bygg"], "geography": ["Umeå"]}, 2) == []
    assert anrop == [False]


def test_noll_bolag_heter_inga_traffar_och_sager_varfor():
    k = iris_korning.ny_korning(mal=10, scope="research_and_draft", overrides=None, is_test=False)
    iris_korning.avsluta(k, "slut_pa_kandidater")
    assert k["slut_orsak"] == "inga_traffar"
    assert "inga bolag" in iris_korning.sammanfatta(k)


def test_provade_bolag_ar_fortfarande_slut_pa_kandidater():
    k = iris_korning.ny_korning(mal=3, scope="research_and_draft", overrides=None, is_test=False)
    k["tratt"].append({"namn": "A", "steg": "förfilter", "skal": "Ingen webbplats"})
    iris_korning.avsluta(k, "slut_pa_kandidater")
    assert k["slut_orsak"] == "slut_pa_kandidater"
