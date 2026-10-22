"""Registerkällan allabolag (sources/allabolag.py, 2026-10-15): tolkningen av
en sparad riktig sökresultatsida, geofiltren, sökorden, cachen och hela
merinfo.sok i allabolag-läget — utan ett enda nätanrop (conftest tömmer
LEADS_DIREKTHAMTNING, och hämtningen läser då bara cachen).

Fixturen är sökningen "redovisning" i Mölndal som den såg ut 2026-10-15,
oförändrad.
"""
from __future__ import annotations

import json

import pytest

from app.leads import discovery, sidhamtning
from app.leads.discovery import DiscoveryError
from app.leads.sources import allabolag as a
from app.leads.sources import merinfo as m
from app.storage.memory import MemoryStorage

TENANT = "00000000-0000-4000-a000-00000000ab01"


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture(scope="module")
def sida() -> dict:
    return a.tolka_sida(a.FIXTUR.read_text(encoding="utf-8"), a.FIXTUR_URL)


def _bolag(sida: dict, namn: str) -> dict:
    return next(b for b in sida["bolag"] if b["company_name"] == namn)


# -- Tolkningen ------------------------------------------------------------------


def test_sidan_ger_traffar_i_merinfos_bolagsform(sida):
    assert (sida["hits"], sida["pages"], len(sida["bolag"])) == (29, 2, 25)
    # Exakt samma nycklar som merinfo.tolka_bolag: urvalet läser båda lika.
    merinfo_form = set(m.tolka_bolag("", "https://www.merinfo.se/foretag/x"))
    assert all(set(b) == merinfo_form for b in sida["bolag"])

    b = _bolag(sida, "Account i Mölndal AB")
    assert b["orgnr"] == "556477-7083"
    assert b["website"] == "http://www.revisorn.com"
    assert (b["anstallda"], b["omsattning"]) == (4, 5_185_000), "allabolag anger tkr, formen kronor"
    assert (b["ort"], b["lan"], b["postnr"]) == ("Mölndal", "Västra Götalands län", "431 67")
    assert b["sni"] is None and b["sni_namn"]
    assert b["url"] == "https://www.allabolag.se/5564777083"
    assert b["status"] is None, "aktiva sökträffar saknar status; okänt fäller aldrig"


def test_saknade_falt_blir_none_aldrig_gissade(sida):
    assert _bolag(sida, "Axblom & Thöresson redovisning aktiebolag")["anstallda"] is None  # "1-4"
    seven = _bolag(sida, "Seven Redovisning AB")
    assert seven["website"] is None and seven["epost"] is None and seven["telefon"] is None
    # Postadressen när besöksadressen saknas.
    assert _bolag(sida, "POP Redovisning och Revision AB")["postnr"] == "431 34"


def test_enskild_firma_bar_aldrig_personnumret(sida):
    """allabolag visar en enskild näringsidkares personnummer med löpnummer
    (14 siffror). Det förs inte vidare; formen fäller bolaget."""
    ef = _bolag(sida, "RÅD & REDOVISNING, ANNA EXEMPEL")
    assert ef["orgnr"] is None and ef["bolagsform"] == "Enskild firma"
    assert "Enskild firma" in m.kontrollera(ef, {}, None)
    assert m.ar_enskild(m.till_kandidat(ef, {}, None))
    assert not any(len("".join(c for c in str(b["orgnr"] or "") if c.isdigit())) > 10 for b in sida["bolag"])


def test_registret_ar_ett_filter_inte_en_kontaktkalla(sida):
    """Antons regel 1: sökträffens kontaktperson blir aldrig leadets kontakt.
    Bara VD:s namn läses (regel 15), och ensam-VD-undantaget (regel 7) kräver
    hela personlistan, som en sökträff inte har."""
    vd = _bolag(sida, "Lindome Lön och Redovisning AB")
    assert vd["personer"][0]["roll"] == "Verkställande direktör" and m.vd_namn(vd)
    assert m.ensam_vd_telefon({**vd, "anstallda": 1}) is None
    k = m.till_kandidat(vd, {}, None)
    assert k["source_name"] == "allabolag" and k["source_url"] == vd["url"]
    assert all(k[f] is None for f in ("contact_name", "contact_role", "contact_phone", "contact_email"))
    assert m.vd_namn(_bolag(sida, "Account i Mölndal AB")) is None, "en ordförande är aldrig VD"


# -- Geografi och sökord ---------------------------------------------------------


@pytest.mark.parametrize(
    ("termer", "vantat"),
    [
        ([], [None]),
        (["Göteborg", "Mölndal"], ["municipality=Göteborg", "municipality=Mölndal"]),
        (["Norrland"], ["county=Norrbotten", "county=Västerbotten", "county=Jämtland", "county=Västernorrland",
                        "county=Gävleborg"]),
        (["Västerbottens län", "Umeå"], ["county=Västerbotten"]),
        (["Luelå"], ["municipality=Luleå"]),
        (["Gbg"], ["municipality=Göteborg"]),
        (["Atlantis"], None),
        # Flera områden i ett fält (main 2026-10-22: hela strängen gav None).
        (["Göteborg & Norrland (Umeå)"], ["municipality=Göteborg", "municipality=Umeå"]),
        (["Borås, Alingsås och Mölndal"], ["municipality=Borås", "municipality=Alingsås", "municipality=Mölndal"]),
        (["Helsingborg/Lund"], ["municipality=Helsingborg", "municipality=Lund"]),
        # Parentesen preciserar; är den ingen ort gäller det yttre.
        (["Norrland (Umeå)"], ["municipality=Umeå"]),
        (["Norrland (Atlantis)"], ["county=Norrbotten", "county=Västerbotten", "county=Jämtland",
                                   "county=Västernorrland", "county=Gävleborg"]),
    ],
)
def test_geofiltret(termer, vantat):
    assert a.valj_filter(termer) == vantat


def test_regionnyckeln_blir_sina_kommuner_inte_lanet():
    """Göteborgsområdet är sju kommuner. Hos merinfo blev tre kommuner i
    samma län hela länet; här är varje kommun en gratis sökning."""
    filter_ = a.valj_filter([], regioner=["goteborg"])
    assert "municipality=Mölndal" in filter_ and "municipality=Kungsbacka" in filter_
    assert not any(f.startswith("county=") for f in filter_)


def test_sokorden_ar_kundens_egna():
    assert a.valj_termer(["Byggföretag", "B2B"]) == ["Bygg"]
    assert a.valj_termer(["e-utbildning & möblerfirmor"]) == ["e-utbildning", "möbler"]
    assert a.valj_termer(["Företag med gamla och dåligt underhållna hemsidor"]) == []
    assert a.valj_termer([], malgrupp="Redovisningsbyråer") == ["Redovisningsbyråer"]


def test_sokadressen():
    assert a.sokadress("båt", "county=Västerbotten", 2) == (
        "https://www.allabolag.se/bransch-s%C3%B6k?q=b%C3%A5t&county=V%C3%A4sterbotten&page=2"
    )
    assert a.sokadress("bygg", "Umeå", 1).endswith("?q=bygg&municipality=Ume%C3%A5")
    assert a.sokadress("bygg", None, 1).endswith("?q=bygg")


def test_registervalet(monkeypatch):
    assert m.register() == "merinfo" and not m.aktiv()
    monkeypatch.setenv("LEADS_MERINFO", "scrapegraph")
    assert m.register() == "allabolag" and m.aktiv(), "osatt = allabolag när registret är på"
    monkeypatch.setenv("LEADS_REGISTER", "merinfo")
    assert m.register() == "merinfo"
    monkeypatch.setenv("LEADS_MERINFO", "")
    monkeypatch.setenv("LEADS_REGISTER", "allabolag")
    assert m.register() == "allabolag" and m.aktiv()


def test_registret_ar_pa_som_standard_nar_ingen_flagga_ar_satt(monkeypatch):
    """Main 2026-10-21: varken LEADS_MERINFO eller LEADS_REGISTER var satt,
    registret var av och körningarna hängde på en död Gemini-väg. Helt osatt
    betyder nu allabolag PÅ; en TOM sträng är fortfarande uttryckligt av
    (testsvitens hermetik i tests/conftest.py bygger på det)."""
    monkeypatch.delenv("LEADS_MERINFO", raising=False)
    monkeypatch.delenv("LEADS_REGISTER", raising=False)
    assert m.aktiv() and m.register() == "allabolag"
    monkeypatch.setenv("LEADS_REGISTER", "")
    assert not m.aktiv(), "tom sträng = uttryckligt av"


# -- Hämtningen och cachen -------------------------------------------------------------


@pytest.mark.anyio
async def test_hamtningen_ar_av_i_testsviten_och_cachen_lases(sida):
    storage = MemoryStorage()
    kontext = sidhamtning.starta(storage, TENANT)
    assert await a.sok_sida("redovisning", "municipality=Mölndal", 1) is None

    url = a.sokadress("redovisning", "municipality=Mölndal", 1)
    await storage.put_sidcache(TENANT, url + a._CACHEVERSION, innehall=json.dumps(sida), fel=None)
    bolag = await a.sok_sida("redovisning", "municipality=Mölndal", 1)
    assert len(bolag) == 25 and kontext.cachetraffar == 1
    assert kontext.totalt == 0, "allabolag räknas aldrig som ett betalt anrop"
    # Bortom sista sidan: inga fler träffar, inget fel.
    await storage.put_sidcache(TENANT, a.sokadress("redovisning", "municipality=Mölndal", 3) + a._CACHEVERSION,
                               innehall=json.dumps(sida), fel=None)
    assert await a.sok_sida("redovisning", "municipality=Mölndal", 3) == []


@pytest.mark.anyio
async def test_direkthamtningen_tolkar_och_cachar(monkeypatch):
    monkeypatch.setenv("LEADS_DIREKTHAMTNING", "1")
    hamtade: list[str] = []

    async def _html(url):
        hamtade.append(url)
        return a.FIXTUR.read_text(encoding="utf-8"), None

    monkeypatch.setattr(a, "_hamta_html", _html)
    storage = MemoryStorage()
    sidhamtning.starta(storage, TENANT)
    forsta = await a.sok_sida("redovisning", "municipality=Mölndal", 1)
    andra = await a.sok_sida("redovisning", "municipality=Mölndal", 1)
    assert forsta == andra and len(forsta) == 25
    assert len(hamtade) == 1, "samma sida hämtas en gång (sidcachen)"


@pytest.mark.anyio
async def test_sparrad_sida_ger_none(monkeypatch):
    monkeypatch.setenv("LEADS_DIREKTHAMTNING", "1")

    async def _html(url):
        return "<html>Access denied</html>", None

    monkeypatch.setattr(a, "_hamta_html", _html)
    assert await a.sok_sida("bygg", None, 1) is None


# -- Hela sökningen i allabolag-läget ----------------------------------------------------


def _installera_allabolag(monkeypatch, sida: dict) -> list[tuple]:
    anrop: list[tuple] = []

    async def _sok_sida(term, plats, nr):
        anrop.append((term, plats, nr))
        if (term, plats, nr) == ("redovisning", "municipality=Mölndal", 1):
            return [dict(b) for b in sida["bolag"]]
        return []

    async def _ingen_merinfo(*_a, **_k):
        raise AssertionError("merinfo ska inte hämtas i allabolag-läget")

    monkeypatch.setenv("LEADS_REGISTER", "allabolag")
    monkeypatch.setattr(a, "sok_sida", _sok_sida)
    monkeypatch.setattr(m, "hamta", _ingen_merinfo)
    return anrop


@pytest.mark.anyio
async def test_sokningen_via_allabolag(monkeypatch, sida):
    """Samma urval som med merinfo: kontrollen, fördelningen (regler 12–16)
    och listspåret. Enskilda firmor når aldrig något spår, och kredittaket
    (tak=0) stoppar inte registret: listsidorna är gratis."""
    anrop = _installera_allabolag(monkeypatch, sida)

    async def _uppslag(namn, geografi=None):
        return None

    async def _kontakt(webb, vd=None, *, bolagsadress_racker=False, **_k):
        assert bolagsadress_racker
        if "revisorn.com" in webb:
            return {"contact_email": "info@revisorn.com", "contact_phone": None, "contact_level": "role_address"}
        return None

    monkeypatch.setattr(discovery, "sla_upp_webbplats", _uppslag)
    monkeypatch.setattr(discovery, "hamta_person_kontakt", _kontakt)
    sidhamtning.starta(MemoryStorage(), TENANT, tak=0)
    icp = {"industries": ["redovisning"], "geography": ["Mölndal"], "size": {"anstallda_min": 1, "anstallda_max": 49}}
    listspar: list[dict] = []
    leads = await m.sok(icp, 2, uteslut=set(), profil=None, listspar=listspar)

    assert [k["company_name"] for k in leads] == ["Account i Mölndal AB"]
    assert leads[0]["source_name"] == "allabolag" and leads[0]["lan"] == "Västra Götalands län"
    assert leads[0]["contact_phone"] is None, "registrets nummer blir aldrig Iris-kontakt"
    spar = {r["company_name"]: r for r in listspar}
    # Johannebergs ligger i en senare omgång: taket stoppade inte loopen.
    for namn in ("Lindome Lön och Redovisning AB", "Johannebergs Redovisning Aktiebolag"):
        assert spar[namn]["spar"] == "ring" and spar[namn]["contact_role"] == "VD"
    assert spar["Lunmans Konsult och Redovisningbyrå Aktiebolag"]["signal_detalj"] == "Ingen namngiven VD"
    namn_i_spar = {*spar, *(k["company_name"] for k in leads)}
    assert not any(b["bolagsform"] == "Enskild firma" and b["company_name"] in namn_i_spar for b in sida["bolag"])
    assert ("redovisning", "municipality=Mölndal", 2) in anrop, "bläddrar tills listan är slut"


@pytest.mark.anyio
async def test_upptagna_bolag_hoppas_over_pa_orgnr(monkeypatch, sida):
    _installera_allabolag(monkeypatch, sida)

    async def _komplettera(rankade, antal, **_):
        return rankade[:antal]

    monkeypatch.setattr(m, "_komplettera", _komplettera)
    icp = {"industries": ["redovisning"], "geography": ["Mölndal"]}
    ut = await m.sok(icp, 30, uteslut={"orgnr:5564777083"})
    assert ut and "Account i Mölndal AB" not in {k["company_name"] for k in ut}


@pytest.mark.anyio
async def test_hamtfel_ar_inte_kunde_inte_tolka(monkeypatch):
    """Sidorna gick inte att hämta: DiscoveryError, så att discovery fyller
    på med sökkedjan (regel 11) i stället för att tro att målgruppen saknas."""
    monkeypatch.setenv("LEADS_REGISTER", "allabolag")

    async def _fel(*_a):
        return None

    monkeypatch.setattr(a, "sok_sida", _fel)
    with pytest.raises(DiscoveryError):
        await m.sok({"industries": ["bygg"], "geography": ["Umeå"]}, 3)

    async def _tom(*_a):
        return []

    monkeypatch.setattr(a, "sok_sida", _tom)
    assert await m.sok({"industries": ["Nischbransch"], "geography": ["Umeå"]}, 3) is None


@pytest.mark.anyio
async def test_bred_sokning_anvander_allabolags_branschnamn(monkeypatch, sida):
    anrop = _installera_allabolag(monkeypatch, sida)
    await m.sok({"industries": ["B2B"], "geography": ["Umeå"]}, 1)
    assert {t for t, _p, _n in anrop} == set(a.BRED_B2B)
    assert {p for _t, p, _n in anrop} == {"municipality=Umeå"}


@pytest.mark.anyio
async def test_orgnr_ur_allabolags_namnsokning(monkeypatch, sida):
    from app.leads import orgnr_uppslag

    monkeypatch.setenv("LEADS_REGISTER", "allabolag")

    async def _traffar(namn):
        return [{"namn": b["company_name"], "orgnr": b["orgnr"], "ort": b["ort"]} for b in sida["bolag"]]

    monkeypatch.setattr(a, "orgnr_traffar", _traffar)
    assert await orgnr_uppslag.orgnr_i_registret("Account i Mölndal AB", "Mölndal") == "556477-7083"
    assert await orgnr_uppslag.orgnr_i_registret("RÅD & REDOVISNING, SUSANNE SONNTAG", "Mölndal") is None


def test_demo():
    a.demo()
