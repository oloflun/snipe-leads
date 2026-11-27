"""Bolagsuppgifter ur SCB:s företagsregister: uppslag och berikning.

SCB anropas aldrig: en falsk transport svarar i stället, och nätvakten ligger
kvar utanpå som i drift. Den falska transporten skickar med flit fält med
personnamn (firmatecknare, styrelse, innehavare) som registret aldrig får
lämna vidare.
"""

from __future__ import annotations

import json

import httpx
import pytest

from app.crm import lagring, scb
from app.integrationer import natvakt

from .conftest import ORGNR_A, ORGNR_B

V1 = "/api/crm/v1"
pytestmark = pytest.mark.anyio

#: Ett personnummer (tredje siffran under 2): en enskild firmas nummer.
PERSONNUMMER = "800101-0019"
PERSONNAMN = ("Anna Andersson", "Bertil Berg", "Cecilia Carlsson")


def _scb_svar(orgnr: str, **andra) -> dict:
    siffror = orgnr.replace("-", "")
    return {
        "peOrgNr": f"16{siffror}", "orgNr": siffror, "namn": "Byggarna Berggren AB",
        "postAdress": {"gatuAdress": "Storgatan 1", "coAdress": None, "postNr": "11122", "postOrt": "STOCKHOLM"},
        "kommunSate": "0180", "lanSate": "01", "aeAnt": 1, "anstKl": "4", "ftgStat": "1", "jurform": "49",
        "reklamSparrTyp": 21, "telefonSparrTyp": 0, "epostSparrTyp": 0, "bolStat": "0",
        "naringsgrenar": [{"rangordning": 2, "naringsgren": "43210"}, {"rangordning": 1, "naringsgren": "41200"}],
        "tel": "08-123 456 78", "epost": "info@berggren.se", "foretagsnamn": PERSONNAMN[0],
        # Fält registret inte har i dag men som aldrig får följa med om de kommer:
        "firmatecknare": [{"namn": PERSONNAMN[0]}], "styrelse": [{"namn": PERSONNAMN[1], "roll": "Ledamot"}],
        "innehavare": PERSONNAMN[2],
        **andra,
    }


class Scb:
    """SCB:s server. Svarar ur `bolag` (orgnr -> svar), 404 annars, eller med
    `status` när den är satt. Minns varje anrop."""

    def __init__(self) -> None:
        self.bolag: dict[str, dict] = {}
        self.status: int | None = None
        self.natfel = False
        self.anrop: list[httpx.Request] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.anrop.append(request)
        if self.natfel:
            raise httpx.ConnectError("nere", request=request)
        if self.status:
            return httpx.Response(self.status, json={"title": "fel"})
        pe = request.url.path.rstrip("/").split("/")[-2]
        svar = self.bolag.get(pe[2:])
        if svar is None:
            return httpx.Response(404, json={"title": "Not Found", "status": 404})
        return httpx.Response(200, json=svar)


@pytest.fixture
def register(monkeypatch) -> Scb:
    s = Scb()

    async def dns(vard: str, port: int) -> list[str]:
        return ["93.184.216.34"]

    monkeypatch.setattr(natvakt, "upplos", dns)
    monkeypatch.setattr(natvakt, "inre_transport", lambda: httpx.MockTransport(s))
    monkeypatch.setattr(scb, "_nyckel", lambda: "provnyckel")
    monkeypatch.setattr(scb, "_MELLANRUM", 0.0)
    scb.nollstall()
    return s


async def _bolag(k, **falt) -> dict:
    svar = await k.post(f"{V1}/companies", json={"name": "Berggren", **falt})
    assert svar.status_code == 201, svar.text
    return svar.json()


def _utan_personer(text: str) -> None:
    for namn in PERSONNAMN:
        assert namn not in text, namn


async def test_uppslaget_ger_bolagsniva_och_sparar_ingenting(buddy, register):
    register.bolag[ORGNR_A.replace("-", "")] = _scb_svar(ORGNR_A)
    async with buddy.klient() as k:
        svar = await k.get(f"{V1}/lookup/companies", params={"org_number": ORGNR_A})
        assert svar.status_code == 200, svar.text
        data = svar.json()["data"]
        assert data == {
            "org_number": ORGNR_A, "name": "Byggarna Berggren AB", "legal_form": "AB", "legal_form_code": "49",
            "registry_status": "active", "sni_codes": ["41200", "43210"],
            "registered_office": {"municipality": "0180", "county": "01"},
            "postal_address": {"street": "Storgatan 1", "co": None, "postal_code": "111 22", "city": "STOCKHOLM"},
            "employee_class": {"code": "4", "label": "10-19"}, "advertising_block": True,
            "codes": {"company_status": "1", "bolagsverket_status": "0", "advertising": 21}}
        _utan_personer(svar.text)
        assert "info@berggren.se" not in svar.text and "123 456" not in svar.text
        assert (await k.get(f"{V1}/companies")).json()["data"] == []
    # Nyckeln går i X-API-Key, numret som PeOrgNr med 16 först.
    anrop = register.anrop[0]
    assert anrop.headers["X-API-Key"] == "provnyckel"
    assert anrop.url.path == f"/v1/juridiskaenheter/16{ORGNR_A.replace('-', '')}/full"


async def test_uppslag_som_inte_finns_och_felaktigt_nummer(buddy, register):
    async with buddy.klient() as k:
        saknas = await k.get(f"{V1}/lookup/companies", params={"org_number": ORGNR_B})
        assert saknas.status_code == 404 and saknas.json()["detail"]["code"] == "company_not_in_registry"
        fel = await k.get(f"{V1}/lookup/companies", params={"org_number": "556036-0794"})
        assert fel.status_code == 422 and fel.json()["detail"]["fields"] == [
            {"field": "org_number", "code": "orgnr_kontrollsiffra"}]


async def test_enskild_firma_slas_inte_upp(buddy, register):
    async with buddy.klient() as k:
        svar = await k.get(f"{V1}/lookup/companies", params={"org_number": PERSONNUMMER})
        assert svar.status_code == 422 and svar.json()["detail"]["code"] == "not_a_company"
    assert register.anrop == []


async def test_registrets_enskilda_naringsidkare_och_dodsbon_lamnas_aldrig_ut(buddy, register):
    register.bolag[ORGNR_A.replace("-", "")] = _scb_svar(ORGNR_A, jurform="10", namn=PERSONNAMN[0])
    register.bolag[ORGNR_B.replace("-", "")] = _scb_svar(ORGNR_B, jurform="91", namn=f"Dödsbo efter {PERSONNAMN[1]}")
    async with buddy.klient() as k:
        for orgnr in (ORGNR_A, ORGNR_B):
            svar = await k.get(f"{V1}/lookup/companies", params={"org_number": orgnr})
            assert svar.status_code == 422 and svar.json()["detail"]["code"] == "not_a_company"
            _utan_personer(svar.text)


async def test_tomma_falt_fylls_och_fyllda_star_kvar(buddy, annan, register):
    register.bolag[ORGNR_A.replace("-", "")] = _scb_svar(ORGNR_A)
    async with buddy.klient() as k:
        bolag = await _bolag(k, org_number=ORGNR_A, address={"city": "Solna"})
        svar = await k.post(f"{V1}/companies/{bolag['id']}/enrich")
        assert svar.status_code == 200, svar.text
        ut = svar.json()
        assert ut["filled"] == ["legal_form", "sni_code", "address.street", "address.postal_code"]
        assert ut["skipped"] == ["name", "address.city"] and ut["protected"] == []
        assert ut["registry_status"] == "active" and ut["deregistered"] is False
        assert ut["advertising_block"] is True
        bolag = ut["company"]
        assert bolag["name"] == "Berggren" and bolag["address"]["city"] == "Solna"
        assert bolag["legal_form"] == "AB" and bolag["sni_code"] == "41200,43210"
        assert bolag["address"]["street"] == "Storgatan 1" and bolag["address"]["postal_code"] == "111 22"
        assert bolag["registry_status"] == "active" and bolag["registry_checked_at"]
        # Antal anställda är ett antal; registrets klass skrivs inte dit.
        assert bolag["employees"] is None and ut["registry"]["employee_class"]["label"] == "10-19"
        # Reklamspärren blir inte tyst kontakta inte.
        assert bolag["do_not_contact"] is False
        _utan_personer(svar.text)
        # Berikningen märker inte fälten som ändrade för hand.
        post = await lagring.hamta_post(buddy.app.state.storage, buddy.id, "bolag", bolag["id"])
        assert set(post["manuellt_andrade"]) <= {"postort"}
        # Händelseloggen bär fältens namn.
        flode = (await k.get(f"{V1}/changes")).json()["data"]
        assert flode[-1]["type"] == "updated" and "registry_status" in flode[-1]["fields"]
        _utan_personer(json.dumps(flode))
        # En gång till: inget nytt att fylla.
        igen = (await k.post(f"{V1}/companies/{bolag['id']}/enrich")).json()
        assert igen["filled"] == [] and igen["skipped"] == ["name", "address.city"]
    # Den andra kunden når inte bolaget.
    async with annan.klient() as k:
        assert (await k.post(f"{V1}/companies/{bolag['id']}/enrich")).status_code == 404


async def test_overwrite_skriver_over_men_skyddar_manuellt_andrade(buddy, register):
    register.bolag[ORGNR_A.replace("-", "")] = _scb_svar(ORGNR_A)
    async with buddy.klient() as k:
        bolag = await _bolag(k, org_number=ORGNR_A, legal_form="HB")
        # Ett fält som ändrats för hand efter att posten skapades.
        await k.patch(f"{V1}/companies/{bolag['id']}", json={"address": {"city": "Solna"}})
        svar = (await k.post(f"{V1}/companies/{bolag['id']}/enrich", params={"overwrite": "true"})).json()
        assert "name" in svar["filled"] and svar["protected"] == ["address.city"] and svar["skipped"] == []
        assert svar["company"]["name"] == "Byggarna Berggren AB" and svar["company"]["address"]["city"] == "Solna"


async def test_handandrat_falt_ar_skyddat_och_ovriga_hoppas_bara_utan_overwrite(buddy, annan, register):
    """Skillnaden gränssnittet bygger knappen Skriv över med registrets på:
    `skipped` är det knappen skriver över, `protected` det den aldrig rör."""
    register.bolag[ORGNR_A.replace("-", "")] = _scb_svar(ORGNR_A)
    async with buddy.klient() as k:
        bolag = await _bolag(k, org_number=ORGNR_A, legal_form="HB")
        await k.patch(f"{V1}/companies/{bolag['id']}", json={"address": {"city": "Solna"}})
        utan = (await k.post(f"{V1}/companies/{bolag['id']}/enrich")).json()
        assert utan["protected"] == ["address.city"]
        assert utan["skipped"] == ["name", "legal_form"]
        assert "legal_form" not in utan["filled"] and "address.city" not in utan["filled"]
        med = (await k.post(f"{V1}/companies/{bolag['id']}/enrich", params={"overwrite": "true"})).json()
        assert med["protected"] == ["address.city"] and med["skipped"] == []
        assert med["filled"] == ["name", "legal_form"]
        assert med["company"]["legal_form"] == "AB" and med["company"]["address"]["city"] == "Solna"
        # Knappen kommer inte tillbaka: nästa hämtning har inget att skriva över.
        igen = (await k.post(f"{V1}/companies/{bolag['id']}/enrich")).json()
        assert igen["skipped"] == [] and igen["protected"] == ["address.city"] and igen["filled"] == []
    # Den andra kundens bolag med samma nummer berörs inte.
    async with annan.klient() as k:
        eget = await _bolag(k, org_number=ORGNR_A, legal_form="HB")
        ut = (await k.post(f"{V1}/companies/{eget['id']}/enrich")).json()
        assert ut["protected"] == [] and ut["skipped"] == ["name", "legal_form"]


async def test_reklamsparren_star_kvar_pa_bolaget_och_blir_aldrig_kontakta_inte(buddy, annan, register):
    register.bolag[ORGNR_A.replace("-", "")] = _scb_svar(ORGNR_A, reklamSparrTyp=21)
    async with buddy.klient() as k:
        bolag = await _bolag(k, org_number=ORGNR_A)
        assert bolag["registry_advertising_block"] is None
        svar = (await k.post(f"{V1}/companies/{bolag['id']}/enrich")).json()
        assert svar["advertising_block"] is True and svar["company"]["registry_advertising_block"] is True
        # Efter en omladdning står den kvar.
        hamtat = (await k.get(f"{V1}/companies/{bolag['id']}")).json()
        assert hamtat["registry_advertising_block"] is True and hamtat["do_not_contact"] is False
        assert (await k.get(f"{V1}/suppressions")).json()["data"] == []
        assert (await k.post(f"{V1}/suppressions/check", json={"channel": "all", "org_number": ORGNR_A})
                ).json()["blocked"] is False
        flode = (await k.get(f"{V1}/changes")).json()["data"]
        assert "registry_advertising_block" in flode[-1]["fields"]
        # Nästa hämtning säger att bolaget tar emot reklam: false, inte kvar som true.
        register.bolag[ORGNR_A.replace("-", "")] = _scb_svar(ORGNR_A, reklamSparrTyp=11)
        svar = (await k.post(f"{V1}/companies/{bolag['id']}/enrich")).json()
        assert svar["company"]["registry_advertising_block"] is False
        assert "registry_advertising_block" in (await k.get(f"{V1}/changes")).json()["data"][-1]["fields"]
        # Ett okänt värde blir null.
        register.bolag[ORGNR_A.replace("-", "")] = _scb_svar(ORGNR_A, reklamSparrTyp=None)
        svar = (await k.post(f"{V1}/companies/{bolag['id']}/enrich")).json()
        assert svar["company"]["registry_advertising_block"] is None
        assert svar["company"]["do_not_contact"] is False
        # Oförändrat värde loggas inte igen.
        antal = len((await k.get(f"{V1}/changes")).json()["data"])
        await k.post(f"{V1}/companies/{bolag['id']}/enrich")
        assert len((await k.get(f"{V1}/changes")).json()["data"]) == antal
    async with annan.klient() as k:
        eget = await _bolag(k, org_number=ORGNR_A)
        assert (await k.get(f"{V1}/companies/{eget['id']}")).json()["registry_advertising_block"] is None


async def test_bolag_utan_nummer_och_enskild_firma_och_privatperson(buddy, register):
    async with buddy.klient() as k:
        utan = await _bolag(k)
        svar = await k.post(f"{V1}/companies/{utan['id']}/enrich")
        assert svar.status_code == 422 and svar.json()["detail"]["code"] == "org_number_required"
        ef = await _bolag(k, legal_form="Enskild firma")
        svar = await k.post(f"{V1}/companies/{ef['id']}/enrich")
        assert svar.status_code == 422 and svar.json()["detail"]["code"] == "not_a_company"
        privat = await _bolag(k, private_person=True)
        svar = await k.post(f"{V1}/companies/{privat['id']}/enrich")
        assert svar.status_code == 422 and svar.json()["detail"]["code"] == "not_a_company"
    assert register.anrop == []


async def test_avregistrerat_bolag_sags_i_svaret(buddy, register):
    register.bolag[ORGNR_A.replace("-", "")] = _scb_svar(ORGNR_A, bolStat="52", ftgStat="9")
    async with buddy.klient() as k:
        bolag = await _bolag(k, org_number=ORGNR_A)
        svar = (await k.post(f"{V1}/companies/{bolag['id']}/enrich")).json()
        assert svar["registry_status"] == "deregistered" and svar["deregistered"] is True
        assert svar["company"]["registry_status"] == "deregistered"


async def test_scb_nere_ger_502_och_aldrig_500(buddy, register):
    async with buddy.klient() as k:
        bolag = await _bolag(k, org_number=ORGNR_A)
        for satt in ({"status": 500}, {"status": 429}, {"status": 401}, {"natfel": True}):
            register.status, register.natfel = satt.get("status"), satt.get("natfel", False)
            for svar in (await k.get(f"{V1}/lookup/companies", params={"org_number": ORGNR_A}),
                         await k.post(f"{V1}/companies/{bolag['id']}/enrich")):
                assert svar.status_code == 502, (satt, svar.text)
                assert svar.json()["detail"]["code"] == "registry_unavailable"
                assert "provnyckel" not in svar.text
        # Bolaget är orört när registret inte svarade.
        assert (await k.get(f"{V1}/companies/{bolag['id']}")).json()["registry_status"] is None


async def test_okonfigurerat_ger_503(buddy, monkeypatch):
    monkeypatch.setattr(scb, "_nyckel", lambda: "")
    assert scb.konfigurerad() is False
    async with buddy.klient() as k:
        bolag = await _bolag(k, org_number=ORGNR_A)
        for svar in (await k.get(f"{V1}/lookup/companies", params={"org_number": ORGNR_A}),
                     await k.post(f"{V1}/companies/{bolag['id']}/enrich")):
            assert svar.status_code == 503 and svar.json()["detail"]["code"] == "enrichment_not_configured"


async def test_omfang_las_racker_for_uppslag_men_inte_for_berikning(buddy, register):
    register.bolag[ORGNR_A.replace("-", "")] = _scb_svar(ORGNR_A)
    las = await buddy.ny_nyckel(["crm:las"])
    async with buddy.klient() as k:
        bolag = await _bolag(k, org_number=ORGNR_A)
    async with buddy.klient(las) as k:
        assert (await k.get(f"{V1}/lookup/companies", params={"org_number": ORGNR_A})).status_code == 200
        svar = await k.post(f"{V1}/companies/{bolag['id']}/enrich")
        assert svar.status_code == 403 and svar.json()["detail"]["code"] == "scope_missing"


def test_reklamsparrens_koder_och_okanda_varden():
    def reklam(kod):
        return scb.tolka(ORGNR_A, {"jurform": "49", "reklamSparrTyp": kod}).reklamsparr

    assert reklam(21) is True and reklam(23) is True
    assert reklam(11) is False and reklam(13) is False
    assert reklam(None) is None and reklam(7) is None
