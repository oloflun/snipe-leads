"""Registerkällan merinfo (sources/merinfo.py): tolkning, Antons geografiregel,
kontaktkravet och hela sökningen — utan ett enda nätanrop.

Sidorna nedan är SYNTETISKA men i exakt det markdown-format ScrapeGraphAI
gav för merinfos list- och bolagssidor 2026-10-01. Riktiga sidor checkas
inte in: de bär verkliga personers namn och telefonnummer.
"""
from __future__ import annotations

import pytest

from app.leads import discovery
from app.leads.sources import merinfo as m

LISTA = """\
[ Sök ](https://www.merinfo.se/)
##  [ Alfa Bygg AB ](https://www.merinfo.se/foretag/Alfa-Bygg-AB-5560000001/2k0aaaa-aaaa)
Mölndal
[ __070-111 11 11](tel:+46701111111) [ Visa alla telefonnummer ](https://www.merinfo.se/foretag/Alfa-Bygg-AB-5560000001/2k0aaaa-aaaa/telefonnummer)
##  [ Beta Måleri AB ](https://www.merinfo.se/foretag/Beta-M%C3%A5leri-AB-5560000002/2k0bbbb-bbbb)
Mölndal
##  [ Gamma Golv AB ](https://www.merinfo.se/foretag/Gamma-Golv-AB-5560000003/2k0cccc-cccc)
[ __031-22 22 22](tel:+4631222222) [ Visa alla telefonnummer ](https://www.merinfo.se/foretag/Gamma-Golv-AB-5560000003/2k0cccc-cccc/telefonnummer)
##  [ Delta Snickeri AB ](https://www.merinfo.se/foretag/Delta-Snickeri-AB-5560000004/2k0dddd-dddd)
[ __070-444 44 44](tel:+46704444444) [ Visa alla telefonnummer ](https://www.merinfo.se/foretag/Delta-Snickeri-AB-5560000004/2k0dddd-dddd/telefonnummer)
"""


def bolagssida(namn: str, orgnr: str, *, roll: str | None = "Verkställande direktör", person: str = "Test Testsson",
               telefon: str | None = "070-111 11 11", anstallda: int = 4, status: str = "Bolaget är aktivt",
               bolagsform: str = "Aktiebolag", verksamhet: str = "Bolaget skall bedriva byggverksamhet.",
               epost: str | None = None, hemsida: str | None = None) -> str:
    rollblock = (
        f"{roll}:\n     [ {person} ](https://www.merinfo.se/person/M%C3%B6lndal/Test-1970/xxxx)\n" if roll else ""
    )
    telblock = f"[ __ {telefon} ](tel:+46700000000)\n" if telefon else ""
    return f"""\
# [{namn}](https://www.merinfo.se/foretag/x)
Org.nr: {orgnr}
Mölndal
##  Bolagsöversikt & nyckeltal
Omsättning 3 922 tkr
Resultat efter finansnetto 431 tkr
## Telefonnummer
{telblock}## Adress
{namn}
TESTGATAN 1
431 34 Mölndal
## Bolagsinformation
Org.nummer:
     {orgnr}
{rollblock}Styrelsesuppleant:
     [ Suppleant Person ](https://www.merinfo.se/person/M%C3%B6lndal/S-1980/yyyy)
E-post:
     {epost or "__Lägg till e-post"}
Hemsida:
     {hemsida or "__Lägg till hemsida"}
## Bolagsfakta
Antal anställda:
    {anstallda} st
### Verksamhetsbeskrivning
{verksamhet}
Status
     __ {status}
Bolagsform
    {bolagsform}
Länssäte
    Västra Götaland
Kommunsäte
    Mölndal
### Svensk näringsgrensindelning
  * 43330 [Golv- och väggbeläggningsarbeten](https://www.merinfo.se/search?d=c&sni=43330)
"""


def test_listsidan_ger_namn_url_orgnr_och_telefon():
    rader = m.tolka_lista(LISTA)
    assert [r["company_name"] for r in rader] == ["Alfa Bygg AB", "Beta Måleri AB", "Gamma Golv AB", "Delta Snickeri AB"]
    assert rader[0]["orgnr"] == "556000-0001" and rader[0]["telefon"] == "070-111 11 11"
    # Telefonen tillhör sin egen rad, aldrig grannens.
    assert rader[1]["telefon"] is None and rader[1]["orgnr"] == "556000-0002"


def test_bolagssidan_ger_kontaktperson_med_roll_och_telefon():
    b = m.tolka_bolag(bolagssida("Alfa Bygg AB", "556000-0001"), "u")
    assert b["personer"][0] == {"roll": "Verkställande direktör", "namn": "Test Testsson"}
    # Suppleanten är aldrig en kontakt.
    assert all(p["roll"] != "Styrelsesuppleant" for p in b["personer"])
    assert b["telefon"] == "070-111 11 11"
    assert (b["postnr"], b["ort"], b["anstallda"], b["omsattning"]) == ("431 34", "Mölndal", 4, 3_922_000)
    assert (b["sni"], b["bolagsform"], b["epost"], b["website"]) == ("43330", "Aktiebolag", None, None)
    assert b["status"] == "Bolaget är aktivt"


@pytest.mark.parametrize(
    ("termer", "vantat"),
    [
        ([], [None]),
        (["Mölndal"], ["molndal"]),
        # Två specifika kommuner: separata sökningar, även i olika län.
        (["Mölndal", "Luleå"], ["molndal", "lulea"]),
        (["Stockholm", "Göteborg"], ["stockholm", "goteborg"]),
        # Sammanhängande område: tre kommuner i samma län blir länet.
        (["Göteborg", "Mölndal", "Partille"], ["vastra-gotalands-lan"]),
        (["Västra Götaland"], ["vastra-gotalands-lan"]),
        (["Stockholms län"], ["stockholms-lan"]),
        (["Göteborg", "Västra Götalands län"], ["vastra-gotalands-lan"]),
        (["Norrland"], ["norrbottens-lan", "vasterbottens-lan", "jamtlands-lan", "vasternorrlands-lan", "gavleborgs-lan"]),
        # Okänd ort: ingen sökning i hela landet på en felstavning.
        (["Gbg"], None),
    ],
)
def test_geografiregeln(termer, vantat):
    assert m.valj_platser(termer) == vantat


def test_branschval():
    assert m.valj_branscher(["Bygg"]) == ["byggbranschen"]
    assert m.valj_branscher(["byggföretag"]) == ["byggbranschen"]
    assert m.valj_branscher(["fastighet"]) == ["fastighetsbranschen"]
    # Utan träff i sitemapen provas ordet som egen slugg.
    assert m.valj_branscher(["golvläggare"]) == ["golvlaggare"]


@pytest.mark.parametrize(
    ("andring", "skal"),
    [
        ({"roll": None}, "Ingen verifierad kontakt"),
        ({"telefon": None}, "Ingen verifierad kontakt"),
        ({"status": "Bolaget är avregistrerat"}, "Inte aktivt"),
        ({"bolagsform": "Enskild firma"}, "Enskild firma"),
        ({"anstallda": 80}, "För stort"),
    ],
)
def test_kontaktkravet_och_kanda_fakta_faller(andring, skal):
    b = m.tolka_bolag(bolagssida("Alfa Bygg AB", "556000-0001", **andring), "u")
    if andring.get("telefon", "x") is None:
        b["telefon"] = None
    utfall = m.kontrollera(b, {"size": {"anstallda_min": 1, "anstallda_max": 49}}, None)
    assert utfall and utfall.startswith(skal)


def test_godkant_bolag_passerar():
    b = m.tolka_bolag(bolagssida("Alfa Bygg AB", "556000-0001"), "u")
    assert m.kontrollera(b, {"size": {"anstallda_min": 1, "anstallda_max": 49}}, None) is None


def test_bara_mejl_racker_som_kontaktvag():
    """Antons tillägg 2026-10-02: en rad med namn, roll och mejl men utan
    telefon sparas också. Namn och roll krävs fortfarande."""
    b = m.tolka_bolag(bolagssida("Beta Måleri AB", "556000-0002", telefon=None, epost="info@betamaleri.se"), "u")
    assert b["telefon"] is None and b["epost"] == "info@betamaleri.se"
    assert m.kontrollera(b, {}, None) is None
    utan_person = m.tolka_bolag(bolagssida("Beta Måleri AB", "556000-0002", roll=None, epost="info@betamaleri.se"), "u")
    assert str(m.kontrollera(utan_person, {}, None)).startswith("Ingen verifierad kontakt")
    # Telefon väger tyngre än mejl vid rangordningen.
    med_tel = m.tolka_bolag(bolagssida("Alfa Bygg AB", "556000-0001"), "u")
    assert m._kodpoang(med_tel, {}, None) > m._kodpoang(b, {}, None)


@pytest.fixture
def anyio_backend():
    return "asyncio"


def _installera_sidor(monkeypatch, sidor: dict[str, str]) -> list[str]:
    hamtade: list[str] = []

    async def _hamta(url):
        hamtade.append(url)
        return sidor.get(url)

    monkeypatch.setattr(m, "hamta", _hamta)
    return hamtade


@pytest.mark.anyio
async def test_hela_sokningen_levererar_bara_kvalificerade(monkeypatch):
    rader = {r["company_name"]: r["url"] for r in m.tolka_lista(LISTA)}
    hamtade = _installera_sidor(
        monkeypatch,
        {
            "https://www.merinfo.se/byggbranschen/molndal/foretag/1": LISTA,
            rader["Alfa Bygg AB"]: bolagssida("Alfa Bygg AB", "556000-0001"),
            # Beta saknar telefon både i listan och på bolagssidan, men har en
            # sajt: mejlen hämtas därifrån (hamta_kontaktvag, stubbad nedan).
            rader["Beta Måleri AB"]: bolagssida("Beta Måleri AB", "556000-0002", telefon=None,
                                                hemsida="www.betamaleri.se"),
            # Gamma saknar namngiven person: fälls på kontaktkravet.
            rader["Gamma Golv AB"]: bolagssida("Gamma Golv AB", "556000-0003", roll=None),
            rader["Delta Snickeri AB"]: bolagssida("Delta Snickeri AB", "556000-0004", roll="Styrelseledamot",
                                                   person="Dora Delta", telefon="070-444 44 44"),
        },
    )
    async def _kontaktvag(website):
        assert website == "https://www.betamaleri.se"
        return {"contact_email": "info@betamaleri.se", "contact_level": "role_address"}

    monkeypatch.setattr(discovery, "hamta_kontaktvag", _kontaktvag)
    icp = {"industries": ["Bygg"], "geography": ["Mölndal"], "roles": ["VD"], "size": {"anstallda_min": 1, "anstallda_max": 49}}
    leads = await m.sok(icp, 5, uteslut=set(), profil=None)

    assert [k["company_name"] for k in leads] == ["Alfa Bygg AB", "Beta Måleri AB", "Delta Snickeri AB"]
    beta = leads[1]
    assert beta["contact_phone"] is None and beta["contact_email"] == "info@betamaleri.se"
    alfa = leads[0]
    assert (alfa["contact_name"], alfa["contact_role"], alfa["contact_phone"]) == (
        "Test Testsson", "Verkställande direktör", "070-111 11 11")
    # VD matchar kundens önskade roll; ledamoten är en annan beslutsfattare.
    assert alfa["contact_level"] == "named_role_match" and leads[2]["contact_level"] == "named_other"
    assert alfa["source_name"] == "merinfo" and alfa["source_url"].startswith("https://www.merinfo.se/foretag/")
    # Beta saknade telefon i listan men hämtas ändå: mejl syns aldrig på listsidan.
    assert rader["Beta Måleri AB"] in hamtade


@pytest.mark.anyio
async def test_uteslutna_och_okand_malgrupp(monkeypatch):
    _installera_sidor(monkeypatch, {"https://www.merinfo.se/byggbranschen/molndal/foretag/1": LISTA})
    icp = {"industries": ["Bygg"], "geography": ["Mölndal"]}
    uteslut = {"alfa bygg ab", "gamma golv ab", "delta snickeri ab"}
    assert await m.sok(icp, 3, uteslut=uteslut) == []
    # Okänd ort, och en bransch utan någon lista hos merinfo: None, så den
    # gamla kedjan tar vid i stället för ett tomt svar.
    assert await m.sok({"industries": ["Bygg"], "geography": ["Gbg"]}, 3) is None
    assert await m.sok({"industries": ["Finns Inte"], "geography": ["Mölndal"]}, 3) is None


@pytest.mark.anyio
async def test_hitta_bolag_anvander_registret_bara_nar_flaggan_ar_satt(monkeypatch):
    anrop: list[int] = []

    async def _sok(icp, antal, **_k):
        anrop.append(antal)
        return [{"company_name": "Alfa Bygg AB"}]

    monkeypatch.setattr(m, "sok", _sok)
    monkeypatch.setenv("LEADS_KALLOR", "")

    async def _gemini(_prompt):
        return "[]"

    monkeypatch.setattr(discovery, "_gemini_med_sokning", _gemini)
    assert await discovery.hitta_bolag({"industries": ["Bygg"]}, 2) == []
    assert anrop == []

    monkeypatch.setenv("LEADS_MERINFO", "scrapegraph")
    assert await discovery.hitta_bolag({"industries": ["Bygg"]}, 2) == [{"company_name": "Alfa Bygg AB"}]
    assert anrop == [2]


def test_regionnyckel_expanderas_utan_profil(monkeypatch):
    """icp.geo bär regionnycklar (app/leads/geo.py). Profilen expanderar dem
    normalt; utan profil ska `sok` göra det själv, annars blev "goteborg"
    bara staden. Sju kommuner i samma län → länet (Antons regel)."""
    sedda: list[tuple[str, str | None, int]] = []

    def _url(bransch, plats, sida):
        sedda.append((bransch, plats, sida))
        return f"https://x/{bransch}/{plats}/{sida}"

    async def _tom(url):
        return None

    monkeypatch.setattr(m, "listsida_url", _url)
    monkeypatch.setattr(m, "hamta", _tom)
    import asyncio

    ut = asyncio.run(m.sok({"industries": ["bygg"], "geo": ["goteborg"]}, 3))
    assert ut is None  # inga listrader: "kunde inte tolka", inte "inga bolag"
    # Sex kommuner i Västra Götaland → länet; Kungsbacka ligger i Halland
    # och blir en egen sökning (en kommun i ett annat län breddas inte).
    assert {plats for _, plats, _ in sedda} == {"vastra-gotalands-lan", "kungsbacka"}, sedda


def test_register_rankas_av_signaler_inte_valjs_av_dem():
    """Plan del C: en registerrad med signalträff går först och bär signalen;
    en signalträff utanför registret är inte målgruppen och faller."""
    register = [
        {"company_name": "Alfa Bygg AB", "orgnr": "556000-0001", "website": "https://alfabygg.se"},
        {"company_name": "Beta Måleri AB", "orgnr": "556000-0002", "website": "https://betamaleri.se"},
    ]
    signaler = [
        {"company_name": "BETA MÅLERI AB", "signal": "rekryterar", "signal_detalj": "Målare", "source_url": "https://af.se/1"},
        {"company_name": "Okänt Bolag AB", "signal": "nyhet", "source_url": "https://x.se"},
    ]
    ut = discovery._med_signaler(register, signaler)
    assert [r["company_name"] for r in ut] == ["Beta Måleri AB", "Alfa Bygg AB"]
    assert ut[0]["signal"] == "rekryterar" and ut[0]["signal_kalla"] == "https://af.se/1"
    assert "signal" not in ut[1] or ut[1].get("signal") is None
