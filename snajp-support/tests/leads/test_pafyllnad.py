"""Påfyllnadsstegen (Antons regel 2026-11-24): rena funktioner i
app/leads/korning.py.

"Iris får aldrig, under inga omständigheter leverera under beställt antal, i
värsta fall får man ta ett av de (mest kvalificerade) bortsorterade bolagen
för att fylla ut kvoten, om inga fullt kvalificerade hittas."

Här prövas stegens ordning, rangordningen av researchens bortval, tolkningen
av registrets storleksskäl och spärren som avgör vad som aldrig fylls på.
Motorn i sin helhet prövas i tests/invariants/test_inv_leads_n_002.py.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from app.leads import korning as km
from app.leads.platshallare import AVVECKLAT
from app.leads.scoring import MISS, OKAND, TRAFF


def _rad(nyckel: str, utfall: str, *, hart: bool = True, belagg: bool = False, etikett: str | None = None) -> dict:
    return {
        "nyckel": nyckel,
        "etikett": etikett or nyckel,
        "vikt": 1,
        "utfall": utfall,
        "motivering": "m",
        "hart": hart,
        "belagg": [{"url": "u", "citat": "c"}] if belagg else [],
    }


def _prospekt(namn: str, *, rader: list[dict], icp_fit: float = 0.3, dq: list[str] | None = None, **extra) -> dict:
    return {
        "id": namn,
        "company_name": namn,
        "website": f"https://{namn.lower()}.se",
        "contact_email": f"info@{namn.lower()}.se",
        "niva": "C",
        "qualified": False,
        "icp_fit": icp_fit,
        "score_breakdown": rader,
        "disqualifiers": dq or ["skäl"],
        "status": "new",
        **extra,
    }


# --- Stegens ordning -------------------------------------------------------


def _k(**extra) -> dict:
    k = km.ny_korning(mal=10, scope="research_and_draft", overrides=None, is_test=True)
    k["levererade"] = 8
    k.update(extra)
    return k


def test_stegen_kommer_i_bestamd_ordning():
    k = _k()
    sedda = []
    while (steg := km.nasta_pafyllnad(k)) is not None:
        sedda.append(steg)
        k.setdefault("pafyllnad", {}).setdefault("klara", []).append(steg)
    assert sedda == [
        "omforsok", "prova_om", "bortval", "storlek_25", "storlek_50", "storlek_100", "belagt_nej",
    ]


def test_inget_steg_nar_malet_ar_natt_eller_for_listjobb():
    assert km.nasta_pafyllnad(_k(levererade=10)) is None
    assert km.nasta_pafyllnad(_k(kalla="lista")) is None


def test_soksteg_hoppas_over_nar_kredittaket_eller_sokningen_stoppat():
    """Storleksvidgningen kräver sökrundor; de andra stegen körs ändå."""
    for orsak in ("kredittak", "sokningen_foll", "ingen_malgrupp"):
        k = _k(pafyllnad={"klara": ["omforsok", "prova_om", "bortval"]})
        assert km.nasta_pafyllnad(k, orsak=orsak) == "belagt_nej"


def test_belagt_nej_ligger_bakom_konstanten(monkeypatch):
    monkeypatch.setattr(km, "PAFYLL_BELAGT_NEJ", False)
    k = _k(pafyllnad={"klara": list(km.PAFYLLNADSSTEG[:-1])})
    assert km.nasta_pafyllnad(k) is None


# --- Rangordningen ---------------------------------------------------------


def test_rangordningen_av_researchens_bortval():
    under = _prospekt("Under", rader=[_rad("kp", TRAFF, belagg=True), _rad("k1", TRAFF)], icp_fit=0.5,
                      dq=["Under tröskeln: träffsäkerhet 50 av 60 krävda"])
    kp_okand_lag = _prospekt("KpOkandLag", rader=[_rad("kp", MISS), _rad("k1", TRAFF)], icp_fit=0.2)
    kp_okand_hog = _prospekt("KpOkandHog", rader=[_rad("kp", MISS), _rad("k1", TRAFF)], icp_fit=0.6)
    maste_okant = _prospekt("MasteOkant", rader=[_rad("kp", TRAFF, belagg=True), _rad("k1", OKAND)], icp_fit=0.9)
    bor_nej = _prospekt("BorNej", rader=[_rad("kp", TRAFF, belagg=True), _rad("k1", TRAFF),
                                         _rad("k2", MISS, hart=False, belagg=True)], icp_fit=0.95)
    kp_nej = _prospekt("KpNej", rader=[_rad("kp", MISS, belagg=True), _rad("k1", TRAFF)], icp_fit=0.99)
    maste_nej = _prospekt("MasteNej", rader=[_rad("kp", TRAFF, belagg=True), _rad("k1", MISS, belagg=True)])

    assert km.bortvalsgrupp(under) == "a"
    assert km.bortvalsgrupp(kp_okand_hog) == "b"
    assert km.bortvalsgrupp(maste_okant) == "c"
    assert km.bortvalsgrupp(bor_nej) == "d"
    assert km.bortvalsgrupp(kp_nej) == "nej"
    assert km.bortvalsgrupp(maste_nej) == "nej"

    alla = [kp_nej, bor_nej, maste_okant, kp_okand_lag, under, kp_okand_hog, maste_nej]
    steg3 = km.rangordna_bortval(alla, grupper=km.BORTVALSGRUPPER)
    assert [p["id"] for p in steg3] == ["Under", "KpOkandHog", "KpOkandLag", "MasteOkant", "BorNej"]
    steg5 = km.rangordna_bortval(alla, grupper=("nej",))
    assert [p["id"] for p in steg5] == ["KpNej", "MasteNej"]


def test_inget_kallmaterial_och_ingen_research_ar_ingen_bortvalsgrupp():
    """Tjänstefelen researchas om i steg 1; de rangordnas aldrig."""
    tjanstefel = _prospekt("Fel", rader=[_rad("underlag", MISS)],
                           dq=["Inget källmaterial: bolagets sidor gick inte att hämta"])
    assert km.bortvalsgrupp(tjanstefel) is None
    assert km.bortvalsgrupp({"id": "x", "niva": "A", "qualified": True}) is None


def test_skalet_bar_aldrig_webbrevisionen():
    p = _prospekt("Webb", rader=[_rad("kp", MISS), _rad("k1", TRAFF)],
                  webbrevision={"betyg": 3, "modernitet": 2}, webbniva="dålig")
    skal = km.pafyllnadsskal(p, km.bortvalsgrupp(p))
    assert skal and "betyg" not in skal.casefold() and "webbniv" not in skal.casefold()


# --- Storleksskälen --------------------------------------------------------


@pytest.mark.parametrize(
    ("skal", "vantat"),
    [
        ("För stort: 60 anställda (högst 49).", ("anstallda_max", 60, 49)),
        ("För litet: 2 anställda (minst 5).", ("anstallda_min", 2, 5)),
        ("För stort: 60 anställda enligt källan (högst 49).", ("anstallda_max", 60, 49)),
        ("För hög omsättning: 12000000 kr (högst 10000000 kr).", ("omsattning_max", 12_000_000, 10_000_000)),
        ("För låg omsättning: 100000 kr (minst 500000 kr).", ("omsattning_min", 100_000, 500_000)),
        ("Bransch kunden undviker: bemanning.", None),
        ("För hög omsättning: 12000000 kr.", None),
    ],
)
def test_tolkningen_av_storleksskalen(skal, vantat):
    assert km.tolka_storleksskal(skal) == vantat


def test_vidgningen_tar_de_narmaste_forst():
    nara = km.tolka_storleksskal("För stort: 55 anställda (högst 49).")
    langt = km.tolka_storleksskal("För stort: 90 anställda (högst 49).")
    assert km.inom_vidgning(nara, 0.25) and not km.inom_vidgning(langt, 0.25)
    assert not km.inom_vidgning(langt, 0.5) and km.inom_vidgning(langt, 1.0)
    litet = km.tolka_storleksskal("För litet: 2 anställda (minst 5).")
    assert not km.inom_vidgning(litet, 0.25) and km.inom_vidgning(litet, 0.5)
    assert km.vidgad_grans("anstallda_max", 49, 0.25) == 62
    assert km.vidgad_grans("anstallda_min", 5, 0.5) == 2


# --- Spärren ---------------------------------------------------------------


_OK = _prospekt("Okej", rader=[_rad("kp", MISS), _rad("k1", TRAFF)], orgnr="5566778899")


def test_sparren_slapper_ett_vanligt_bortval():
    assert km.far_fyllas_pa(_OK, profil={}) is None


@pytest.mark.parametrize(
    ("andring", "falt"),
    [
        ({"disqualifiers": [f"Bolaget: {AVVECKLAT}"]}, "avvecklat"),
        ({"avvecklas": True}, "avvecklat"),
        ({"orgnr": "8001011234"}, "enskild firma"),
        ({"bolagsform": "Enskild näringsidkare"}, "enskild firma"),
        ({"status": "suppressed"}, "kontakta inte"),
        ({"utfall": "kontakta_inte"}, "kontakta inte"),
        ({"status": "contacted"}, "redan kontaktat"),
        ({"status": "replied"}, "redan kontaktat"),
        ({"status": "lost"}, "redan kontaktat"),
        ({"contact_email": None, "contact_phone": "070-1234567"}, "mottagare"),
        ({"disqualifiers": ["Uteslutet — bemanningsföretag: r"]}, "uteslutet"),
        ({"orgnr": "2120001234"}, "offentlig"),
        ({"spar": "ring"}, "listspår"),
        ({"spar": "ej_kvalificerad"}, "listspår"),
        ({"score_breakdown": [_rad("ort", MISS), _rad("kp", MISS)]}, "området"),
    ],
)
def test_sparren_faller_vart_och_ett_av_fallen(andring, falt):
    skal = km.far_fyllas_pa({**_OK, **andring}, profil={})
    assert skal, falt
    assert falt in skal.casefold(), (falt, skal)


def test_sparren_faller_redan_kontaktat_ur_mangden():
    from app.leads import upptagna

    kontaktade = upptagna.bolagsnycklar([_OK])
    assert km.far_fyllas_pa(_OK, profil={}, kontaktade=kontaktade)


def test_offentlig_sektor_slapps_nar_profilen_pekar_ut_den():
    assert km.far_fyllas_pa({**_OK, "orgnr": "2120001234"}, profil={"offentlig_sektor": True}) is None


def test_sparren_faller_en_adress_pa_suppressionslistan():
    skal = km.far_fyllas_pa(_OK, profil={}, sparrade={"INFO@okej.se".casefold()})
    assert skal and "kontakta inte" in skal.casefold()


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.anyio
async def test_anroparna_hamtar_kontakta_inte_ur_samtal_och_suppressionslistan():
    """Granskningen 2026-11-25: spärren fick aldrig mängden i drift. Nu hämtar
    api/leads.py:_pafyllnadens_sparrar den ur lagringen: ett samtal med
    utfallet Kontakta inte och en adress på suppressionslistan fäller bolaget
    även när prospektets egen status inte säger det."""
    from app.api.leads import _pafyllnadens_sparrar
    from app.storage.memory import MemoryStorage

    tenant = "00000000-0000-0000-0000-00000000a1b3"
    storage = MemoryStorage()
    ringd = await storage.create_prospect(tenant, company_name="Ringd AB", origin="iris")
    await storage.add_lead_samtal(tenant, prospect_id=ringd["id"], utfall="kontakta_inte",
                                  aterkom_datum=None, anteckning=None)
    await storage.add_suppression(tenant, email="Info@Avregistrerad.se", reason="avregistrering")
    kontaktade, sparrade = await _pafyllnadens_sparrar(storage, tenant)

    ringd_rad = {**_OK, "id": ringd["id"], "company_name": "Ringd AB", "orgnr": None,
                 "website": "https://ringd.se", "contact_email": "info@ringd.se"}
    skal = km.far_fyllas_pa(ringd_rad, profil={}, kontaktade=kontaktade, sparrade=sparrade)
    assert skal and "redan kontaktat" in skal.casefold()
    avreg = {**_OK, "company_name": "Avregistrerad AB", "orgnr": None,
             "website": "https://avregistrerad.se", "contact_email": "info@avregistrerad.se"}
    skal = km.far_fyllas_pa(avreg, profil={}, kontaktade=kontaktade, sparrade=sparrade)
    assert skal and "kontakta inte" in skal.casefold()
    # Ett bolag utan någon av dem släpps som förut.
    assert km.far_fyllas_pa(_OK, profil={}, kontaktade=kontaktade, sparrade=sparrade) is None


# --- Skälets kod -----------------------------------------------------------


def test_skalet_ar_en_kod_som_granssnittet_oversatter():
    """Granskningen 2026-11-25: skälet var svensk text som en engelsk kund
    läste efter "Filled in:". Nu sparas en kod som
    components/leads/pafyllnad.ts översätter."""
    tröskel = _prospekt("Troskel", rader=[_rad("kp", TRAFF), _rad("k1", TRAFF)],
                        dq=["Under tröskeln: träffsäkerhet 62 av 70 krävda"])
    assert km.pafyllnadsskal(tröskel, km.bortvalsgrupp(tröskel)) == "a:62:70"
    for grupp in (*km.BORTVALSGRUPPER, "nej"):
        assert km.pafyllnadsskal(_OK, grupp) == grupp
    assert km.pafyllnadsskal(_OK, None) == "ovrigt"
    pafyllnad = {"ursprung": {"anstallda_max": 49, "omsattning_min": 1_000_000}, "vidgad": {"anstallda_max": 62}}
    assert km.utanfor_ursprung(pafyllnad, {"anstallda": 55}) == "storlek:anstallda:max:55:49"
    assert km.utanfor_ursprung(pafyllnad, {"omsattning": 800_000}) == "storlek:omsattning:min:800000:1000000"
    assert km.utanfor_ursprung(pafyllnad, {"anstallda": 40}) is None


# --- Vilande ---------------------------------------------------------------


def test_vilande_vacks_en_gang_per_dygn():
    nu = datetime(2026, 11, 24, 12, tzinfo=timezone.utc)
    k = _k()
    km.vila(k, "registret", nu=nu)
    assert k["vilande"]["skal"] == "registret" and not k["klar"]
    assert not km.ska_vackas(k, nu + timedelta(hours=23))
    assert km.ska_vackas(k, nu + timedelta(hours=km.VILA_TIMMAR, minutes=1))
    k["pafyllnad"] = {"klara": list(km.PAFYLLNADSSTEG)}
    k["tomma_rundor"] = km.TOMMA_RUNDOR
    k["stopp"] = "kredittak"
    km.vakna(k)
    assert "vilande" not in k and not k.get("stopp") and not k.get("tomma_rundor")
    assert km.nasta_pafyllnad(k) == "omforsok"


def test_markningen_hor_till_bedomningens_protokoll():
    """pafylld och pafylld_skal ligger i BEDOMNINGSFALT (storage/base.py),
    så att varje väg som kopierar en bedömning (spara_bedomning,
    admin_flytt) bär märkningen med sig."""
    from app.storage.base import BEDOMNINGSFALT

    assert {"pafylld", "pafylld_skal"} <= set(BEDOMNINGSFALT)
