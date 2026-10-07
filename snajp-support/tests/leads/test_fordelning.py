"""Fördelningen efter kontaktsökningen (Antons regler 12, 13, 15 och 16,
2026-10-07): Iris, ringlistan, ej kvalificerade, eller prövas om.

Inga nätanrop: kontaktsökningen och webbplatsuppslagen mockas, lagringen
är MemoryStorage.
"""

from __future__ import annotations

import pytest

from app.api.leads import _skapa_prospekt_ur_kandidat, _spara_listspar
from app.leads import discovery, korning, sidhamtning, upptagna
from app.leads.sources import merinfo as m
from app.storage.memory import MemoryStorage

TENANT = "00000000-0000-4000-a000-0000000f0d01"
pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend():
    return "asyncio"


def _kandidat(**andring) -> dict:
    k = {
        "company_name": "Alfa Bygg AB",
        "orgnr": "556000-0001",
        "website": "https://alfabygg.se",
        "ort": "Mölndal",
        "vd_namn": "Test Testsson",
        "anstallda": 4,
        "_epost": None,
        "_telefon": None,
        "_bolagsform": "Aktiebolag",
        "source_name": "merinfo",
        "source_url": "https://www.merinfo.se/foretag/Alfa-Bygg-AB-5560000001/2k",
    }
    return {**k, **andring}


# -- Tabellen -----------------------------------------------------------------


@pytest.mark.parametrize(
    ("kandidat", "kontakt", "vantat"),
    [
        # Mejl på sajten → Iris.
        (_kandidat(), {"contact_email": "info@alfabygg.se"}, ("iris", None)),
        # Ingen sajt men registrets bolags-e-post → Iris (regel 13).
        (_kandidat(website=None, _epost="kontor@alfabygg.se"), None, ("iris", None)),
        # Bara telefon, VD namngiven, aktiebolag → ringlistan (regel 15).
        (_kandidat(), {"contact_phone": "031-12 34 56"}, ("ring", None)),
        (_kandidat(website=None, _telefon="031-12 34 56"), None, ("ring", None)),
        # Telefon utan namngiven VD → ej kvalificerad (regel 16).
        (_kandidat(website=None, vd_namn=None, _telefon="031-12 34 56"), None,
         ("ej_kvalificerad", "Ingen namngiven VD")),
        # Sajtens eget nummer räcker utan VD (regel 12 går före VD-kravet).
        (_kandidat(vd_namn=None), {"contact_phone": "031-12 34 56"}, ("ring", None)),
        # Enskild firma → aldrig ringlistan, aldrig Iris (NIX, MFL 19 §).
        (_kandidat(orgnr="800101-1234", _telefon="070-111 11 11"), {"contact_email": "anna@gmail.com"},
         ("ej_kvalificerad", "Enskild firma (NIX-kontroll krävs)")),
        (_kandidat(_bolagsform="Enskild näringsidkare", _telefon="070-111 11 11"), None,
         ("ej_kvalificerad", "Enskild firma (NIX-kontroll krävs)")),
        # Sajt där inget hittades → prövas om, även med registrets nummer
        # men utan VD (regel 12: en sajt hamnar aldrig bland ej kvalificerade).
        (_kandidat(), None, ("prova_om", "Sajt utan hittad kontakt")),
        (_kandidat(vd_namn=None, _telefon="031-12 34 56"), None, ("prova_om", "Sajt utan hittad kontakt")),
        # Sidtaket stoppade sökningen → prövas om, oavsett registret.
        (_kandidat(_epost="kontor@alfabygg.se"), {"tak": True}, ("prova_om", "Stoppad av sidtaket")),
        # Ingen sajt, inget mejl, ingen telefon.
        (_kandidat(website=None), None, ("ej_kvalificerad", "Inget kontaktsätt")),
        # Registrets HR-adress duger inte.
        (_kandidat(website=None, _epost="jobb@alfabygg.se"), None, ("ej_kvalificerad", "Inget kontaktsätt")),
    ],
)
def test_fordelningen(kandidat, kontakt, vantat):
    assert m.fordela(kandidat, kontakt) == vantat


def test_registrets_epost_bar_iris_kandidaten():
    k = m.iris_kandidat(_kandidat(website=None, _epost="Kontor@AlfaBygg.se"), None)
    assert (k["contact_email"], k["contact_level"], k["kontakt_kalla"]) == ("kontor@alfabygg.se", "role_address", "register")
    sajt = m.iris_kandidat(_kandidat(), {"contact_email": "info@alfabygg.se", "tilltal_namn": "Test Testsson",
                                         "contact_name": "Test Testsson", "tak": False})
    assert sajt["kontakt_kalla"] == "webbplats" and "tak" not in sajt


# -- _komplettera: takstopp och ringlistan --------------------------------------


async def test_takstoppat_bolag_skrivs_inte_och_utesluts_inte(monkeypatch):
    async def _kontakt(webb, vd=None, **_k):
        return {"tak": True}

    monkeypatch.setattr(discovery, "hamta_person_kontakt", _kontakt)
    listspar: list[dict] = []
    ut = await m._komplettera([_kandidat()], 1, lage="iris", puls=None, listspar=listspar)
    assert ut == []
    assert [(r["spar"], r["tak"]) for r in listspar] == [("prova_om", True)]

    lager = MemoryStorage()
    k = {"listspar": listspar, "is_test": False}
    await _spara_listspar(lager, TENANT, k)
    assert await lager.list_lead_lists(TENANT) == []
    assert await lager.list_prospects(TENANT) == []
    assert not upptagna.upptagen(await upptagna.hamta(lager, TENANT), "Alfa Bygg AB", "556000-0001")
    assert k["fordelning"] == {"ring": 0, "ej_kvalificerade": 0, "prova_om": 0, "tak": 1}


async def test_resten_provas_inte_nar_webbtaket_ar_nått(monkeypatch):
    anrop: list[str] = []

    async def _kontakt(webb, vd=None, **_k):
        anrop.append(webb)
        return None

    monkeypatch.setattr(discovery, "hamta_person_kontakt", _kontakt)
    kontext = sidhamtning.starta(None, TENANT, webb_tak=0)
    assert kontext.webb_slut
    listspar: list[dict] = []
    assert await m._komplettera([_kandidat()], 1, lage="iris", puls=None, listspar=listspar) == []
    assert anrop == [] and listspar == []
    sidhamtning._KONTEXT.set(None)


async def test_ringlistan_och_ej_kvalificerade_sparas(monkeypatch):
    kontakter = {
        "https://alfabygg.se": {"contact_email": None, "contact_phone": "031-12 34 56", "contact_name": None},
        "https://betabygg.se": {"contact_email": "info@betabygg.se", "contact_name": None},
    }

    async def _kontakt(webb, vd=None, **_k):
        return kontakter.get(webb)

    monkeypatch.setattr(discovery, "hamta_person_kontakt", _kontakt)
    rankade = [
        _kandidat(jev_triage={"beslut": "behall"}),
        _kandidat(company_name="Beta Bygg AB", orgnr="556000-0002", website="https://betabygg.se"),
        _kandidat(company_name="Gamma Golv AB", orgnr="556000-0003", website=None, vd_namn=None,
                  _telefon="031-22 22 22"),
        _kandidat(company_name="Delta Snickeri AB", orgnr="556000-0004", website="https://deltasnickeri.se"),
    ]
    listspar: list[dict] = []
    iris = await m._komplettera(rankade, 2, lage="iris", puls=None, listspar=listspar)
    assert [k["company_name"] for k in iris] == ["Beta Bygg AB"]
    assert iris[0]["anstallda"] == 4

    lager = MemoryStorage()
    k = korning.ny_korning(mal=1, scope="research_and_draft", overrides=None, is_test=False)
    k["listspar"] = listspar
    # Alfa (telefon på sajten, VD i registret) → ring. Gamma → ej
    # kvalificerad. Delta (sajt utan hittad kontakt) prövas om.
    await _spara_listspar(lager, TENANT, k)

    [ring] = await lager.list_prospects(TENANT)
    assert ring["origin"] == "ring"
    assert (ring["company_name"], ring["contact_name"], ring["contact_role"], ring["contact_phone"]) == (
        "Alfa Bygg AB", "Test Testsson", "VD", "031-12 34 56")
    assert (ring["anstallda"], ring["orgnr"], ring["website"], ring["contact_level"]) == (
        4, "556000-0001", "https://alfabygg.se", "named_role_match")
    assert not ring.get("contact_email")

    [lista] = await lager.list_lead_lists(TENANT)
    assert lista["titel"].startswith("Ej kvalificerade, Iris ")
    [rad] = await lager.list_lead_list_items(TENANT, lista["id"])
    assert (rad["company_name"], rad["signal_detalj"], rad["contact_phone"]) == (
        "Gamma Golv AB", "Ingen namngiven VD", None)
    assert k["fordelning"] == {"ring": 1, "ej_kvalificerade": 1, "prova_om": 1, "tak": 0}

    # Körningsraden säger fördelningen.
    k["levererade"] = 1
    text = korning.sammanfatta(k)
    assert "→ 1 Iris-leads, 1 till ringlistan, 1 ej kvalificerade, 1 sajter utan hittad kontakt (prövas om)." in text

    # Ringlistans prospekt står i uteslutningen; listspåret körs en gång.
    assert upptagna.upptagen(await upptagna.hamta(lager, TENANT), "Alfa Bygg AB")
    await _spara_listspar(lager, TENANT, k)
    assert len(await lager.list_prospects(TENANT)) == 1


def test_sammanfattningen_raknar_ur_listsparet_fore_sparningen():
    k = korning.ny_korning(mal=2, scope="research", overrides=None, is_test=False)
    k["listspar"] = [
        {"company_name": "A", "spar": "ring"},
        {"company_name": "B", "spar": "prova_om", "tak": False},
        {"company_name": "C", "spar": "prova_om", "tak": True},
        {"company_name": "D", "signal_detalj": "Inget kontaktsätt"},
    ]
    text = korning.sammanfatta(k)
    assert (
        "→ 0 Iris-leads, 1 till ringlistan, 1 ej kvalificerade, 1 sajter utan hittad kontakt (prövas om), "
        "1 stoppade av sidtaket (prövas om)." in text
    )


# -- Prospektet ---------------------------------------------------------------


async def test_iris_prospektet_bar_anstallda_och_bara_styrkta_adresser():
    lager = MemoryStorage()
    sajt = await _skapa_prospekt_ur_kandidat(
        lager, TENANT,
        {**_kandidat(), "contact_email": "alfa.bygg@gmail.com", "contact_level": "role_address",
         "kontakt_kalla": "webbplats"},
        "iris",
    )
    assert (sajt["contact_email"], sajt["anstallda"]) == ("alfa.bygg@gmail.com", 4)
    assert discovery.mottagare(sajt) == "alfa.bygg@gmail.com"
    # En annons- eller nyhetsträffs adress utanför bolagets domän stannar.
    annons = await _skapa_prospekt_ur_kandidat(
        lager, TENANT,
        {"company_name": "Beta AB", "website": "https://beta.se", "contact_email": "lisa@bemanning.se",
         "contact_level": "role_address", "source_name": "jobtech"},
        "iris",
    )
    assert not annons.get("contact_email")


# -- Webbplatsen -------------------------------------------------------------


def test_registrets_naknda_doman_tolkas():
    b = m.tolka_bolag(
        "# [Alfa Bygg AB](https://www.merinfo.se/foretag/x)\nOrg.nr: 556000-0001\n"
        "E-post:\n     kontor@alfa-bygg.se\nHemsida:\n     alfa-bygg.se\n",
        "u",
    )
    assert (b["website"], b["epost"]) == ("alfa-bygg.se", "kontor@alfa-bygg.se")


async def test_registrets_hemsida_godtas_utan_namnmatchning(monkeypatch):
    async def _ingen(*_a, **_k):
        raise AssertionError("inget betalt uppslag när registret har en hemsida")

    monkeypatch.setattr(discovery, "sla_upp_webbplats", _ingen)
    assert await m._webbplats(_kandidat(website="www.xyzab.se")) == "https://www.xyzab.se"


async def test_epostdomanen_och_gissningen_provas_fore_det_betalda(monkeypatch):
    monkeypatch.delenv("LEADS_DIREKTHAMTNING", raising=False)  # driftläget
    provade: list[str] = []

    async def _head(url):
        provade.append(url)
        return url == "https://kontorab.se"

    async def _gissa(namn):
        return None

    async def _betald(*_a, **_k):
        raise AssertionError("det betalda uppslaget ska inte behövas")

    monkeypatch.setattr(discovery, "_head_ok", _head)
    monkeypatch.setattr(discovery, "gissa_webbplats_via_head", _gissa)
    monkeypatch.setattr(discovery, "sla_upp_webbplats", _betald)
    assert await m._webbplats(_kandidat(website=None, _epost="info@kontorab.se")) == "https://kontorab.se"
    # En operatörsadress pekar inte ut bolagets sajt.
    provade.clear()
    monkeypatch.setattr(discovery, "sla_upp_webbplats", _gissa)
    assert await m._webbplats(_kandidat(website=None, _epost="alfa@comhem.se")) is None
    assert provade == []


def test_ringraden_utan_vd_bar_sajtens_kontakt_och_vaxelnivan():
    rad = m.ringrad(_kandidat(vd_namn=None), {"contact_phone": "031-12 34 56", "contact_name": "Per Persson"})
    assert (rad["contact_name"], rad["contact_role"], rad["contact_level"], rad["signal_detalj"]) == (
        "Per Persson", None, "role_address", "Bara telefon på sajten")
