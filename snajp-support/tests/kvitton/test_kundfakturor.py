"""Kundfakturor som intäkter i Kvittohanteraren (Sebbe 2026-10-07).

Grundprompten är kundlevererad och känner bara leverantörsdokument, så
igenkänningen sitter i koden (`granskning._verifiera_riktning`): en faktura
där SÄLJAREN är företaget självt är företagets egen faktura till en kund.

Det som prövas:
- orgnumret avgör; namnet ensamt räcker bara med osäker_klassning
- flaggorna som förutsätter att företaget är köpare släpps
- raden sparas med riktning "intakt", kunden som motpart och ett
  försäljningsverifikat (1510/1930 mot 3001 + utgående moms)
- summorna: en kundfaktura blir aldrig ett utlägg, intäkterna står för sig
- människans väg: uppladdning som kundfaktura och riktningsbytet i granskningen
"""

from __future__ import annotations

import asyncio
from datetime import date
from decimal import Decimal

import pytest

from app.kvitton import granskning, hanterare, skanning, systemprompt
from app.kvitton.mejl import Mejl
from app.kvitton.sammanfattning import sammanstall, summeringstext
from app.kvitton.skanning import skanna_inkorg
from app.storage.memory import MemoryStorage

IDAG = date(2026, 10, 6)
ORGNR = "556012-5790"
PROFIL = systemprompt.Foretagsprofil(foretagsnamn="Testbolaget AB", orgnummer=ORGNR)


def _kor(coro):
    return asyncio.run(coro)


KUNDFAKTURA = (
    "Testbolaget AB\nOrg.nr 556012-5790\nFaktura 2042\nFakturadatum 2026-09-28\n"
    "Förfallodatum 2026-10-28\nKund: Kundbolaget AB\n"
    "Netto 8 000,00 kr\nMoms 25 % 2 000,00 kr\nAtt betala 10 000,00 kr\nBankgiro 5050-1055"
)


def _kundfaktura(**andra) -> dict:
    falt = dict(
        leverantör_namn="Testbolaget AB",
        leverantör_orgnummer=ORGNR,
        köpare_namn="Kundbolaget AB",
        dokumentnummer="2042",
        dokumentdatum="2026-09-28",
        förfallodatum="2026-10-28",
        valuta="SEK",
        totalbelopp="10000.00",
        belopp_exkl_moms="8000.00",
        momsbelopp_totalt="2000.00",
        betalstatus="obetald",
        bankgiro="5050-1055",
    )
    falt.update(andra)
    falt = {k: v for k, v in falt.items() if v is not None}
    u = {
        "dokumenttyp": "leverantörsfaktura",
        "fält": {k: {"värde": v, "säkerhet": "säker", "källa": "bilaga_1"} for k, v in falt.items()},
        "moms_per_sats": [{"sats": 25, "underlag": "8000.00", "moms": "2000.00"}],
        "flaggor": [],
        "källfiler": ["bilaga_1"],
        "kategori": "kontorsmateriel",
    }
    return {"klass": "UNDERLAG_BILAGA", "underlag": [u], "intern_notering": ""}


def _verifiera(rat: dict, text: str = KUNDFAKTURA, orgnr: str = ORGNR, namn: str = "Testbolaget AB") -> dict:
    res = granskning.normalisera_resultat(rat, "m-1")
    granskning.verifiera(
        res,
        kalltext=text,
        idag=IDAG,
        dagar_varning=7,
        foretag_orgnr=orgnr,
        foretag_namn=namn,
    )
    return res["underlag"][0]


# -- Igenkänningen --------------------------------------------------------------------


def test_eget_orgnummer_som_saljare_ar_en_intakt():
    u = _verifiera(_kundfaktura())
    assert u["riktning"] == "intakt"
    assert u["dokumenttyp"] == "kundfaktura"
    assert u["kategori"] is None, "En intäkt konteras på momssatsen, inte på en kostnadskategori."
    assert "fel_mottagare" not in u["flaggor"]
    assert u["status"] == granskning.KLAR, u["flaggor"]


def test_forfallen_kundfaktura_ar_inte_prioriterad():
    # Det är kunden som ska betala: en förfallen kundfaktura är en fordran,
    # inte en räkning företaget missat.
    u = _verifiera(_kundfaktura(förfallodatum="2026-09-30"), KUNDFAKTURA.replace("2026-10-28", "2026-09-30"))
    assert "förfallen" not in u["flaggor"]
    assert u["status"] != granskning.PRIORITERAD


def test_bara_namnet_kraver_bekraftelse():
    rat = _kundfaktura(leverantör_orgnummer=None)
    text = KUNDFAKTURA.replace("Org.nr 556012-5790\n", "")
    u = _verifiera(rat, text)
    assert u["riktning"] == "intakt"
    assert "osäker_klassning" in u["flaggor"]
    assert u["status"] == granskning.BEHOVER


def test_annan_leverantor_ar_en_kostnad():
    u = _verifiera(_kundfaktura(), orgnr="556677-8899", namn="Annat Bolag AB")
    assert u["riktning"] == "kostnad"
    assert u["dokumenttyp"] == "leverantörsfaktura"


def test_platshallarnamnet_matchar_aldrig():
    # Profilens "företaget" (tenant utan namn) får inte göra fakturor till intäkter.
    rat = _kundfaktura(leverantör_orgnummer=None, leverantör_namn="Företaget")
    u = _verifiera(rat, KUNDFAKTURA.replace("Testbolaget AB", "Företaget"), orgnr="", namn="")
    assert u["riktning"] == "kostnad"


# -- Hela vägen: avläsning, lagring, verifikat ------------------------------------------


class FejkKonto:
    """Samma gränssnitt som test_kvittohanteraren.FejkKonto."""

    leverantor = "fejk"
    adress = "ekonomi@testbolaget.example"

    def __init__(self, mejl: list[Mejl]):
        self._mejl = mejl

    async def hamta_mejl(self, *, max_antal: int = 50) -> list[Mejl]:
        return self._mejl[:max_antal]

    async def sok_mejl(self, fraga: str, *, max_antal: int = 5) -> list[Mejl]:
        return []


@pytest.fixture
def modellvag(monkeypatch):
    monkeypatch.setattr(hanterare, "anvand_deterministisk", lambda: False)
    monkeypatch.setattr(hanterare, "dagens_datum", lambda nu=None: IDAG)

    async def profil(storage, tenant_id):
        return PROFIL

    monkeypatch.setattr(hanterare, "hamta_profil", profil)
    monkeypatch.setattr(skanning, "hamta_profil", profil)
    svar: dict = {"modell": None}

    async def kor_modellen(system, anvandare, ctx, trace):
        return svar["modell"]

    async def kontrollas(system, anvandare, trace):
        return None

    monkeypatch.setattr(hanterare, "_kor_modellen", kor_modellen)
    monkeypatch.setattr(hanterare, "_kontrollas", kontrollas)
    return svar


def test_kundfakturan_sparas_som_intakt_med_forsaljningsverifikat(modellvag):
    modellvag["modell"] = _kundfaktura()
    mejl = Mejl("kf-1", "Testbolaget AB", "faktura@testbolaget.example", "Faktura 2042", "2026-09-28", KUNDFAKTURA)
    storage = MemoryStorage()
    _kor(skanna_inkorg(storage, "t1", FejkKonto([mejl])))

    rad = _kor(storage.list_bk_underlag("t1"))[0]
    assert rad["riktning"] == "intakt"
    assert rad["motpart"] == "Kundbolaget AB", "Motparten på en intäkt är kunden, inte företaget självt."
    assert rad["status"] == "klar"
    assert rad.get("kategori") in (None, "")

    verifikat = _kor(storage.list_bk_verifikat("t1"))
    assert len(verifikat) == 1
    konton = {r["konto"]: r for r in verifikat[0]["rader"]}
    assert Decimal(str(konton["1510"]["debet"])) == Decimal("10000.00"), "Obetald kundfaktura ska mot kundfordringar."
    assert Decimal(str(konton["3001"]["kredit"])) == Decimal("8000.00")
    utgaende = [r for k, r in konton.items() if k.startswith("26")]
    assert utgaende and Decimal(str(utgaende[0]["kredit"])) == Decimal("2000.00")


def test_kundfaktura_utan_kund_gar_till_granskning(modellvag):
    modellvag["modell"] = _kundfaktura(köpare_namn=None)
    text = KUNDFAKTURA.replace("Kund: Kundbolaget AB\n", "")
    mejl = Mejl("kf-2", "Testbolaget AB", "faktura@testbolaget.example", "Faktura 2042", "2026-09-28", text)
    storage = MemoryStorage()
    _kor(skanna_inkorg(storage, "t1", FejkKonto([mejl])))
    rad = _kor(storage.list_bk_underlag("t1"))[0]
    assert rad["riktning"] == "intakt"
    assert rad["status"] == "granska_manuellt"
    assert "Kunden framgår inte" in rad["anmarkning"]


# -- Summorna --------------------------------------------------------------------------


RADER = [
    {"status": "klar", "riktning": "kostnad", "brutto": Decimal("125.00"), "momssats": Decimal("0.25"), "kategori": "kontorsmateriel"},
    {"status": "klar", "riktning": "intakt", "brutto": Decimal("10000.00"), "momssats": Decimal("0.25"), "betalstatus": "obetald"},
    {"status": "klar", "riktning": "intakt", "brutto": Decimal("1120.00"), "momssats": Decimal("0.12"), "betalstatus": "betald"},
    {"status": "granska_manuellt", "riktning": "intakt", "brutto": Decimal("500.00"), "momssats": Decimal("0.25")},
]


def test_intakterna_star_for_sig_och_utlaggen_ar_orubbade():
    samman = sammanstall(RADER)
    assert samman["totalt"] == "125.00"
    assert samman["moms"] == "25.00"
    assert samman["antal"] == 1
    intakter = samman["intakter"]
    assert intakter["antal"] == 3
    assert intakter["antal_klara"] == 2
    assert intakter["antal_granska"] == 1
    assert intakter["totalt"] == "11120.00"
    assert intakter["moms"] == "2120.00"  # 2 000,00 + 120,00 utgående
    assert intakter["antal_obetalda"] == 1
    assert intakter["obetalt"] == "10000.00"


def test_summeringstexten_namner_intakterna():
    text = summeringstext(sammanstall(RADER), "2026-09-01", "2026-09-30")
    assert "2 kundfakturor" in text
    assert "utgående moms" in text
    bara = summeringstext(sammanstall(RADER[1:2]), "2026-09-01", "2026-09-30")
    assert bara.startswith("Inga kvitton hittades") and "1 kundfaktura" in bara


# -- Människans väg: API:et ------------------------------------------------------------


def _med_env(monkeypatch, **varden):
    from app import config

    for nyckel, varde in varden.items():
        monkeypatch.setenv(nyckel, varde)
    config.get_settings.cache_clear()


def test_riktningen_byts_i_granskningen_och_godkanns_som_forsaljning(monkeypatch):
    from fastapi.testclient import TestClient

    from app.config import DEFAULT_TENANT_ID, get_settings
    from app.main import app

    _med_env(monkeypatch, DATABASE_URL="", REDIS_URL="", GEMINI_API_KEY="", OPENAI_API_KEY="")
    nyckel = {"X-API-Key": get_settings().snajp_demo_api_key}
    with TestClient(app) as klient:
        storage = klient.app.state.storage
        rad = _kor(
            storage.create_bk_underlag(
                DEFAULT_TENANT_ID,
                sha256="test-kundfaktura-riktning",
                filnamn="faktura-2042.pdf",
                mimetyp="application/pdf",
                status="granska_manuellt",
                datum="2026-09-28",
                motpart="Testbolaget AB",
                brutto=Decimal("10000.00"),
                momssats=Decimal("0.25"),
                granskning={"fält": {"köpare_namn": {"värde": "Kundbolaget AB"}}},
            )
        )
        fel = klient.post(f"/api/kvitton/{rad['id']}/riktning", headers=nyckel, json={"riktning": "inkomst"})
        assert fel.status_code == 422

        byte = klient.post(f"/api/kvitton/{rad['id']}/riktning", headers=nyckel, json={"riktning": "intakt"})
        assert byte.status_code == 200, byte.text
        assert byte.json()["underlag"]["riktning"] == "intakt"
        assert byte.json()["underlag"]["motpart"] == "Kundbolaget AB"

        ok = klient.post(f"/api/kvitton/{rad['id']}/godkann", headers=nyckel, json={"betalstatus": "betald"})
        assert ok.json()["godkand"] is True, ok.text

        verifikat = [v for v in _kor(storage.list_bk_verifikat(DEFAULT_TENANT_ID)) if v["underlag_id"] == rad["id"]]
        konton = {r["konto"] for r in verifikat[0]["rader"]}
        assert {"1930", "3001"} <= konton, konton

        igen = klient.post(f"/api/kvitton/{rad['id']}/riktning", headers=nyckel, json={"riktning": "kostnad"})
        assert igen.status_code == 409, "Ett godkänt underlag bytte riktning förbi sitt verifikat."

        lista = klient.get("/api/kvitton?fran=2026-09-01&till=2026-09-30", headers=nyckel).json()["kvitton"]
        assert any(k["id"] == rad["id"] and k["riktning"] == "intakt" for k in lista), (
            "Kundfakturan saknas i kvittolistan — listan filtrerar fortfarande bort intäkter."
        )
        samman = klient.get("/api/kvitton/sammanfattning?fran=2026-09-01&till=2026-09-30", headers=nyckel).json()
        assert samman["intakter"]["antal_klara"] >= 1

        csv = klient.get("/api/kvitton/export.csv?fran=2026-09-01&till=2026-09-30", headers=nyckel).text
        rad_csv = next(r for r in csv.splitlines() if "Kundbolaget AB" in r)
        assert "Intäkt" in rad_csv and "Kundfaktura" in rad_csv, rad_csv


def test_uppladdning_vagrar_okand_riktning(monkeypatch):
    from fastapi.testclient import TestClient

    from app.config import get_settings
    from app.main import app

    _med_env(monkeypatch, DATABASE_URL="", REDIS_URL="", GEMINI_API_KEY="", OPENAI_API_KEY="")
    nyckel = {"X-API-Key": get_settings().snajp_demo_api_key}
    with TestClient(app) as klient:
        svar = klient.post(
            "/api/kvitton/underlag",
            headers=nyckel,
            files={"fil": ("f.pdf", b"%PDF-1.4", "application/pdf")},
            data={"riktning": "inkomst"},
        )
        assert svar.status_code == 422
