"""Inga påhittade bolag: existensgrinden och det som ska hålla utan den.

Provkörningen 2026-10-05 (Snajp, utan filter) gav tre bolag som inte finns,
med poäng 100, status Redo och ett färdigt utkast. Varje test nedan låser ett
av leden som släppte igenom dem.
"""

from unittest.mock import AsyncMock

import pytest

from app.api import leads as leads_api
from app.leads import bedomning, existens, korning, sidhamtning
from app.leads.discovery import DiscoveryError
from app.leads.sources import merinfo
from app.storage.memory import MemoryStorage

TENANT = "22222222-2222-2222-2222-222222222222"


# -- Grinden ---------------------------------------------------------------


def test_domanen_som_inte_svarar_faller():
    skal = existens.styrk(
        {"company_name": "Detaljhandel Design AB", "website": "https://detaljhandeldesign.se", "kalla": "gemini"},
        {"matt": True, "svarar_inte": True},
    )
    assert skal and "svarar inte" in skal


def test_sajten_som_tillhor_nagon_annan_faller():
    skal = existens.styrk(
        {"company_name": "Exempel E-handel AB", "website": "https://cykelhuset.se", "kalla": "gemini"},
        {"matt": True, "sidtext": "Köp cyklar billigt hos Cykelhuset i Borås"},
    )
    assert skal and "står inte på webbplatsen" in skal


def test_bolagsnamnet_i_sidfoten_racker():
    """Utdraget är kapat vid 3 000 tecken; namnet står ofta bara längst ned."""
    sidtext = ("Vi bygger om kök och badrum. " * 300) + "© Hantverkarna i Lund AB"
    assert len(sidtext) > 3000
    assert existens.styrk(
        {"company_name": "Hantverkarna i Lund AB", "website": "https://hil-bygg.se", "kalla": "gemini"},
        {"matt": True, "sidtext": sidtext, "utdrag": sidtext[:3000]},
    ) is None


def test_registerbolag_styrks_av_registret():
    assert existens.styrk({"company_name": "Lilla Bygg AB", "source_name": "merinfo"}, {"matt": True}) is None


def test_blockerad_sajt_kraver_att_domanen_bar_namnet():
    blockerad = {"matt": True, "http_status": 403}
    assert existens.styrk({"company_name": "Countivo AB", "website": "https://countivo.se"}, blockerad) is None
    assert existens.styrk({"company_name": "Countivo AB", "website": "https://annat.se"}, blockerad)


# -- Körningen -------------------------------------------------------------


@pytest.mark.anyio
async def test_sokrundan_valjer_bort_det_ostyrkta_bolaget(monkeypatch):
    kandidater = [
        {"company_name": "Byggmästarna i Göteborg AB", "website": "https://byggmastarnagbg.se", "kalla": "gemini"},
        {"company_name": "Prestigo", "website": "https://prestigo.se", "kalla": "gemini"},
    ]
    monkeypatch.setattr(korning, "hitta_bolag", AsyncMock(return_value=kandidater))

    async def _mat(url):
        if "byggmastarnagbg" in url:
            return {"har_webbplats": True, "matt": True, "svarar_inte": True, "rader": []}
        return {"har_webbplats": True, "matt": True, "sidtext": "Prestigo bygger och målar", "rader": []}

    monkeypatch.setattr(korning, "mat_webbplats", _mat)
    k = korning.ny_korning(mal=2, scope="research", overrides=None, is_test=True)
    await korning.sokrunda({}, {}, k, uteslut=set())

    assert [c["company_name"] for c in k["kandidater"]] == ["Prestigo"]
    assert k["tratt"] == [
        {
            "namn": "Byggmästarna i Göteborg AB",
            "steg": "existens",
            "skal": "Bolaget gick inte att styrka: webbplatsen svarar inte.",
        }
    ]


@pytest.mark.anyio
async def test_soktraffens_pastaenden_foljer_inte_med_till_prospektet():
    """Modellens gissade adress, ort och storlek gav kontaktväg och poäng 100."""
    storage = MemoryStorage()
    prospekt = await leads_api._skapa_prospekt_ur_kandidat(
        storage,
        TENANT,
        {
            "company_name": "Prestigo",
            "website": "https://prestigo.se",
            "kalla": "gemini",
            "contact_name": "Adam Exempel",
            "contact_email": "info@prestigo.se",
            "contact_role": "VD",
            "ort": "Göteborg",
            "anstallda": 15,
        },
        "test",
    )
    rad = await storage.get_prospect(TENANT, prospekt["id"])
    assert rad["website"] == "https://prestigo.se"
    for falt in ("contact_name", "contact_email", "contact_role", "ort", "anstallda"):
        assert not rad.get(falt), falt


def test_sammanfattningen_namnger_skalet_inte_kriteriet():
    """'3 bortvalda: ligger i göteborg' sades om bolag UTANFÖR Göteborg."""
    k = korning.ny_korning(mal=5, scope="research", overrides=None, is_test=True)
    k["undersokta"] = 2
    k["tratt"] = [
        {"namn": "A", "steg": "research", "skal": "Ligger i Göteborg: Orten Umeå ligger utanför målområdet."},
        {"namn": "B", "steg": "förfilter", "skal": "Utanför målområdet: postnummer 903 26."},
    ]
    text = korning.sammanfatta(k)
    assert "2 bortvalda: utanför målområdet" in text
    assert "ligger i göteborg" not in text


# -- Bedömningen -----------------------------------------------------------

_PROFIL_UTAN_KRITERIER = {"kommuner": ["Göteborg"], "anstallda_min": 1, "anstallda_max": 49}


def test_utan_kallmaterial_bedoms_bolaget_inte():
    b = bedomning.bedom(
        _PROFIL_UTAN_KRITERIER, {"motivering": "Passar bra."}, korpus="",
        kandidat={"ort": "Göteborg", "anstallda": 15}, har_underlag=False,
    )
    assert b["niva"] == "C" and b["qualified"] is False and b["score_total"] == 0
    assert b["disqualifiers"] and "Inget källmaterial" in b["disqualifiers"][0]
    assert "Passar bra" not in b["motivering"]


def test_ort_och_storlek_racker_inte_till_niva_a():
    b = bedomning.bedom(
        _PROFIL_UTAN_KRITERIER, {"ort": "Göteborg", "antal_anstallda": 15}, korpus="Göteborg, 15 anställda",
    )
    assert b["score_total"] == 100
    assert b["niva"] == "B"


def test_registrets_tal_kallas_inte_kallmaterial():
    b = bedomning.bedom(_PROFIL_UTAN_KRITERIER, {}, korpus="x", kandidat={"anstallda": 40})
    rad = next(r for r in b["score_breakdown"] if r["nyckel"] == "storlek")
    assert rad["motivering"] == "40 anställda enligt registret."


# -- Registret -------------------------------------------------------------

_ICP = {"industries": ["Bygg"], "geography": ["Mölndal"]}


@pytest.mark.anyio
async def test_tjanstefel_i_registret_faller_inte_tillbaka_pa_sokningen(monkeypatch):
    """Slut på kredit gav None, alltså "kunde inte tolka", och körningen gick
    vidare till den öppna sökningen som hittade på bolag."""
    monkeypatch.setattr(merinfo, "hamta", AsyncMock(return_value=None))
    kontext = sidhamtning.starta(None, TENANT)
    kontext.tjanstefel = 1
    with pytest.raises(DiscoveryError):
        await merinfo.sok(_ICP, 3)


@pytest.mark.anyio
async def test_kredittaket_ger_tom_lista_inte_none(monkeypatch):
    monkeypatch.setattr(merinfo, "hamta", AsyncMock(return_value=None))
    sidhamtning.starta(None, TENANT, tak=0)
    assert await merinfo.sok(_ICP, 3) == []


@pytest.fixture
def anyio_backend():
    return "asyncio"
