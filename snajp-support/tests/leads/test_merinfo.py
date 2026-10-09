"""Registerkällan merinfo (sources/merinfo.py): tolkning, Antons geografiregel,
filtret (bolagsfakta, aldrig registrets kontakter) och hela sökningen — utan ett enda nätanrop.

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
        # Okänt ord: ingen sökning i hela landet på något som inte är en ort.
        (["Qwrtzx"], None),
        # Felstavning och vardagsnamn tolkas (2026-10-07: "Luelå" och "Övik"
        # tappades, och körningen sökte utan dem).
        (["Gbg"], ["goteborg"]),
        (["Luelå"], ["lulea"]),
        (["Övik"], ["ornskoldsvik"]),
        (["Umeå", "Luelå", "Skellefteå"], ["umea", "skelleftea", "lulea"]),
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
    # En målgruppsmening är ingen bransch (Alunix 2026-10-04).
    assert m.valj_branscher(["Företag med gamla, dåligt optimerade hemsidor eller ingen sida alls."]) == []


@pytest.mark.parametrize(
    ("andring", "skal"),
    [
        ({"status": "Bolaget är avregistrerat"}, "Inte aktivt"),
        ({"bolagsform": "Enskild firma"}, "Enskild firma"),
        ({"anstallda": 80}, "För stort"),
    ],
)
def test_kanda_bolagsfakta_faller(andring, skal):
    b = m.tolka_bolag(bolagssida("Alfa Bygg AB", "556000-0001", **andring), "u")
    utfall = m.kontrollera(b, {"size": {"anstallda_min": 1, "anstallda_max": 49}}, None)
    assert utfall and utfall.startswith(skal)


def test_merinfo_ar_ett_filter_inte_en_kontaktkalla():
    """Anton 2026-10-04: bolag utan person eller telefon i registret passerar
    filtret; registrets kontaktuppgifter blir aldrig leadets."""
    for andring in ({"roll": None}, {"telefon": None}, {"roll": "Styrelseledamot"}):
        b = m.tolka_bolag(bolagssida("Alfa Bygg AB", "556000-0001", **andring), "u")
        assert m.kontrollera(b, {"size": {"anstallda_min": 1, "anstallda_max": 49}}, None) is None
    b = m.tolka_bolag(bolagssida("Alfa Bygg AB", "556000-0001"), "u")
    k = m.till_kandidat(b, {}, None)
    assert (k["contact_name"], k["contact_phone"], k["contact_role"]) == (None, None, None)
    assert k["vd_namn"] == "Test Testsson"
    ledamot = m.tolka_bolag(bolagssida("Delta AB", "556000-0004", roll="Styrelseledamot"), "u")
    assert m.vd_namn(ledamot) is None
    # Omsättningsfiltret (merinfo anger tkr; profilen kronor).
    assert str(m.kontrollera(b, {"size": {"omsattning_max": 1_000_000}}, None)).startswith("För hög omsättning")


def test_vd_uppgift_maste_ga_att_knyta_till_vd():
    sida = (
        "<p>Kontakta oss: info@alfabygg.se, 031-11 11 11</p>"
        "<div>Test Testsson, VD<br>Tel 070-123 45 67</div>"
    )
    assert discovery.vd_uppgift_i_text(sida, "Test Testsson", "https://alfabygg.se") == {
        "contact_email": None, "contact_phone": "070-123 45 67"}
    mejl = "<p>Test Testsson</p><a href='mailto:test.testsson@alfabygg.se'>test.testsson@alfabygg.se</a>"
    assert discovery.vd_uppgift_i_text(mejl, "Test Testsson", "https://alfabygg.se")["contact_email"] == (
        "test.testsson@alfabygg.se")
    # Ett växelnummer eller info@ som inte står vid VD:ns namn räknas inte.
    assert discovery.vd_uppgift_i_text("<p>info@alfabygg.se 031-11 11 11</p>", "Test Testsson",
                                       "https://alfabygg.se") is None


@pytest.fixture
def anyio_backend():
    return "asyncio"


def _installera_sidor(monkeypatch, sidor: dict[str, str]) -> list[str]:
    hamtade: list[str] = []

    async def _hamta(url, **_):
        hamtade.append(url)
        return sidor.get(url)

    monkeypatch.setattr(m, "hamta", _hamta)
    return hamtade


def _sidor_for_sokningen():
    rader = {r["company_name"]: r["url"] for r in m.tolka_lista(LISTA)}
    return rader, {
        "https://www.merinfo.se/byggbranschen/molndal/foretag/1": LISTA,
        rader["Alfa Bygg AB"]: bolagssida("Alfa Bygg AB", "556000-0001", hemsida="www.alfabygg.se"),
        # Beta har ingen hemsida i registret: den slås upp.
        rader["Beta Måleri AB"]: bolagssida("Beta Måleri AB", "556000-0002", telefon=None),
        # Gamma: ingen VD och ingen hemsida att hitta.
        rader["Gamma Golv AB"]: bolagssida("Gamma Golv AB", "556000-0003", roll=None),
        rader["Delta Snickeri AB"]: bolagssida("Delta Snickeri AB", "556000-0004", roll="Styrelseledamot",
                                               person="Dora Delta", hemsida="www.deltasnickeri.se"),
    }


@pytest.mark.anyio
async def test_iris_kraver_mejl_resten_fordelas(monkeypatch):
    """Antons regler 12–16 (2026-10-07), som ersätter 3–4 och 8 här: ett
    Iris-lead har en mejladress, aldrig registrets telefon. Gamma (ingen sajt,
    bara registrets nummer, ingen VD) blir ej kvalificerad; Delta (sajt där
    inget hittades) prövas om och skrivs inte som listrad."""
    rader, sidor = _sidor_for_sokningen()
    _installera_sidor(monkeypatch, sidor)

    async def _uppslag(namn, geografi=None):
        return {"Beta Måleri AB": "https://www.betamaleri.se"}.get(namn)

    async def _kontakt(webb, vd=None, *, bolagsadress_racker=False, **_k):
        # Sebbes beslut 2026-10-07: Iris godtar bolagets egen adress när ingen
        # namngiven person finns. Testets sajter bär bara VD:n ur registret.
        assert bolagsadress_racker
        if not vd:
            return None
        return {"contact_email": f"vd@{webb.split('www.')[-1]}", "contact_phone": None,
                "contact_name": vd, "contact_role": "VD", "contact_level": "named_role_match"}

    monkeypatch.setattr(discovery, "sla_upp_webbplats", _uppslag)
    monkeypatch.setattr(discovery, "hamta_person_kontakt", _kontakt)
    icp = {"industries": ["Bygg"], "geography": ["Mölndal"], "size": {"anstallda_min": 1, "anstallda_max": 49}}
    listspar: list[dict] = []
    leads = await m.sok(icp, 5, uteslut=set(), profil=None, listspar=listspar)

    assert sorted(k["company_name"] for k in leads) == ["Alfa Bygg AB", "Beta Måleri AB"]
    assert all((k["contact_name"], k["contact_role"]) == ("Test Testsson", "VD") for k in leads)
    assert all(k["contact_phone"] is None for k in leads), "registrets nummer blir aldrig Iris-kontakt"
    beta = next(k for k in leads if k["company_name"] == "Beta Måleri AB")
    assert beta["website"] == "https://www.betamaleri.se"
    assert {r["company_name"]: (r["spar"], r["signal_detalj"]) for r in listspar} == {
        "Gamma Golv AB": ("ej_kvalificerad", "Ingen namngiven VD"),
        "Delta Snickeri AB": ("prova_om", "Sajt utan hittad kontakt"),
    }
    # Ett nummer utan namngiven VD hör inte hemma på en listrad (regel 5).
    gamma = next(r for r in listspar if r["company_name"] == "Gamma Golv AB")
    assert gamma["contact_phone"] is None


def test_ensam_vd_far_registrets_nummer_men_bara_da():
    """Antons beslut 2026-10-05: registrets telefonnummer får användas när VD
    är den enda personen i bolaget (högst en anställd, ingen annan med roll)."""
    ensam = m.tolka_bolag(bolagssida("Ett AB", "556000-0009", anstallda=1, telefon="070-999 99 99"), "u")
    assert m.ensam_vd_telefon(ensam) == "070-999 99 99"
    tva = m.tolka_bolag(bolagssida("Två AB", "556000-0010", anstallda=2), "u")
    assert m.ensam_vd_telefon(tva) is None
    ledamot = m.tolka_bolag(bolagssida("Led AB", "556000-0011", anstallda=1, roll="Styrelseledamot"), "u")
    assert m.ensam_vd_telefon(ledamot) is None
    # Suppleanten i mallen räknas inte som en annan person med roll.
    assert all(p["roll"] != "Styrelsesuppleant" for p in ensam["personer"])


@pytest.mark.anyio
async def test_lista_kraver_kontakt_som_gar_att_knyta_till_vd(monkeypatch):
    rader, sidor = _sidor_for_sokningen()
    _installera_sidor(monkeypatch, sidor)

    async def _uppslag(namn, geografi=None):
        return {"Beta Måleri AB": "https://www.betamaleri.se"}.get(namn)

    async def _vd_kontakt(webb, vd):
        assert vd == "Test Testsson"
        return {"contact_email": "test@alfabygg.se", "contact_phone": None} if "alfabygg" in webb else None

    monkeypatch.setattr(discovery, "sla_upp_webbplats", _uppslag)
    monkeypatch.setattr(discovery, "hamta_vd_kontakt", _vd_kontakt)
    icp = {"industries": ["Bygg"], "geography": ["Mölndal"]}
    leads = await m.sok(icp, 5, uteslut=set(), profil=None, lage="lista")

    # Beta: VD men inget på sajten som går att knyta till VD. Delta: ingen VD.
    assert [k["company_name"] for k in leads] == ["Alfa Bygg AB"]
    assert (leads[0]["contact_name"], leads[0]["contact_role"], leads[0]["contact_email"]) == (
        "Test Testsson", "VD", "test@alfabygg.se")


@pytest.mark.anyio
async def test_uteslutna_och_okand_malgrupp(monkeypatch):
    _installera_sidor(monkeypatch, {"https://www.merinfo.se/byggbranschen/molndal/foretag/1": LISTA})
    icp = {"industries": ["Bygg"], "geography": ["Mölndal"]}
    uteslut = {"alfa bygg ab", "gamma golv ab", "delta snickeri ab"}
    assert await m.sok(icp, 3, uteslut=uteslut) == []
    # Okänd ort, och en bransch utan någon lista hos merinfo: None, så den
    # gamla kedjan tar vid i stället för ett tomt svar.
    assert await m.sok({"industries": ["Bygg"], "geography": ["Qwrtzx"]}, 3) is None
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


@pytest.mark.anyio
async def test_fa_registertraffar_fylls_pa_med_sokningen(monkeypatch):
    """Sebbes beslut 2026-10-07: registret först, men ger det färre bolag än
    beställt fyller den gamla sökkedjan på, utan registrets bolag och med
    bara det antal som fattas."""
    monkeypatch.setenv("LEADS_MERINFO", "scrapegraph")
    monkeypatch.setenv("LEADS_KALLOR", "")

    async def _sok(icp, antal, **_k):
        return [{"company_name": "Alfa Bygg AB", "website": "https://alfabygg.se"}]

    prompter: list[str] = []

    async def _gemini(prompt):
        prompter.append(prompt)
        return '[{"company_name":"Beta Bygg AB","website":"https://betabygg.se"},' \
               '{"company_name":"Gamma Bygg AB","website":"https://gammabygg.se"}]'

    async def _utan(rader):
        return rader

    monkeypatch.setattr(m, "sok", _sok)
    monkeypatch.setattr(discovery, "_gemini_med_sokning", _gemini)
    monkeypatch.setattr("app.leads.platshallare.utan_platshallare", _utan)
    ut = await discovery.hitta_bolag({"industries": ["Bygg"]}, 2)
    assert [r["company_name"] for r in ut] == ["Alfa Bygg AB", "Beta Bygg AB"]
    assert ut[1]["kalla"] == "gemini" and "kalla" not in ut[0]
    assert "Uteslut dessa namn: alfa bygg ab" in prompter[0], "registrets bolag ska uteslutas ur utfyllnaden"


def test_regionnyckel_expanderas_utan_profil(monkeypatch):
    """icp.geo bär regionnycklar (app/leads/geo.py). Profilen expanderar dem
    normalt; utan profil ska `sok` göra det själv, annars blev "goteborg"
    bara staden. Sju kommuner i samma län → länet (Antons regel)."""
    sedda: list[tuple[str, str | None, int]] = []

    def _url(bransch, plats, sida):
        sedda.append((bransch, plats, sida))
        return f"https://x/{bransch}/{plats}/{sida}"

    async def _tom(url, **_):
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


@pytest.mark.anyio
async def test_sokningen_hamtar_i_takt_med_behovet(monkeypatch):
    """Plan 2026-10-05: N=5 får inte kosta mer än 20 hämtningar när målgruppen
    är tät. Förut: alla listsidor en sida djupare och tre bolagssidor per
    beställt lead (15) på en gång, före något filter."""
    rader = "\n".join(
        f"##  [ Bolag {i} AB ](https://www.merinfo.se/foretag/Bolag-{i}-AB-55600{i:05d}/2k{i})" for i in range(60)
    )
    sidor = {f"https://www.merinfo.se/byggbranschen/molndal/foretag/{s}": rader for s in (1, 2, 3)}
    for i in range(60):
        sidor[f"https://www.merinfo.se/foretag/Bolag-{i}-AB-55600{i:05d}/2k{i}"] = bolagssida(
            f"Bolag {i} AB", f"55600{i:05d}"[:6] + "-" + f"55600{i:05d}"[6:], hemsida=f"www.bolag{i}.se"
        )
    hamtade = _installera_sidor(monkeypatch, sidor)
    monkeypatch.setattr(discovery, "webbplats_matchar_namn", lambda namn, webb: True)

    async def _kontakt(webb, vd=None, **_k):
        return {"contact_email": "vd@exempel.se", "contact_phone": None,
                "contact_name": vd or "Namn Namnsson", "contact_role": "VD" if vd else None,
                "contact_level": "named_role_match" if vd else "named_other"}

    monkeypatch.setattr(discovery, "hamta_person_kontakt", _kontakt)
    icp = {"industries": ["Bygg"], "geography": ["Mölndal"], "size": {"anstallda_min": 1, "anstallda_max": 49}}
    leads = await m.sok(icp, 5, uteslut=set(), profil=None)
    assert len(leads) == 5
    assert len(hamtade) <= 20, hamtade
    # En listsida räckte: loopen bläddrar inte vidare när raderna räcker.
    assert sum("/foretag/1" in u or "/foretag/2" in u for u in hamtade if "byggbranschen" in u) == 1


@pytest.mark.anyio
async def test_enskild_firma_falls_innan_bolagssidan_hamtas(monkeypatch):
    lista = "##  [ Anna Andersson Bygg ](https://www.merinfo.se/foretag/Anna-Andersson-Bygg-8001011234/2k0e)\n"
    hamtade = _installera_sidor(monkeypatch, {"https://www.merinfo.se/byggbranschen/molndal/foretag/1": lista})
    assert await m.sok({"industries": ["Bygg"], "geography": ["Mölndal"]}, 3) == []
    assert not any("Anna-Andersson" in u for u in hamtade)


# -- Sajtens adress mot registrets ort (2026-10-09) ---------------------------


def test_sajt_med_adress_pa_annan_ort_ar_inte_bolagets():
    from app.leads.sources.merinfo import adress_motsager_registret

    piteå = {"ort": "Piteå", "postnr": "941 41"}
    # landin.se: bilverkstaden i Sollentuna fick "Landin & Markström AB" i Piteå.
    assert adress_motsager_registret("Landin & Pettersson Bilservice\nBox 12, 192 79 Sollentuna", piteå)
    # Samma postnummerområde, samma ort, eller orten nämnd: bolagets.
    assert not adress_motsager_registret("Storgatan 1, 941 33 Piteå", piteå)
    assert not adress_motsager_registret("Industrivägen 4, 943 31 Öjebyn", piteå)
    assert not adress_motsager_registret("Vi bygger i Piteå och Luleå. Kontor: 972 41 Luleå", piteå)
    # Ingen adress alls, eller ingen registerort: inget att pröva.
    assert not adress_motsager_registret("Välkommen till oss!", piteå)
    assert not adress_motsager_registret("192 79 Sollentuna", {})


@pytest.mark.anyio
async def test_iris_hamtar_bolag_med_levande_doman_forst(monkeypatch):
    """2026-10-09: 52 köpta bolagssidor för 8 leads. Rader vars namn ger en
    levande domän (gratis HEAD) hämtas först; de andra står kvar sist."""
    rader, sidor = _sidor_for_sokningen()
    hamtade = _installera_sidor(monkeypatch, sidor)
    monkeypatch.setenv("LEADS_DIREKTHAMTNING", "1")

    async def _gissa(namn):
        return {"Beta Måleri AB": "https://betamaleri.se", "Delta Snickeri AB": "https://deltasnickeri.se"}.get(namn)

    async def _komplettera(rankade, antal, **_):
        return rankade[:antal]

    monkeypatch.setattr(discovery, "gissa_webbplats_via_head", _gissa)
    monkeypatch.setattr(m, "_komplettera", _komplettera)
    icp = {"industries": ["Bygg"], "geography": ["Mölndal"], "size": {"anstallda_min": 1, "anstallda_max": 49}}
    await m.sok(icp, 1, uteslut=set(), profil=None)

    bolagssidor = [u for u in hamtade if "merinfo.se/foretag/" in u]
    assert bolagssidor[:2] == [rader["Beta Måleri AB"], rader["Delta Snickeri AB"]]
