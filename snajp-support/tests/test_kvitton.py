"""Kvittohanterarens kedja: identifiering, avläsning, dubbletter, summor.

Körs helt deterministiskt (KVITTO_TOLKNING=deterministisk sätts per test via
monkeypatch på settings) — ingen modell, ingen nyckel, MemoryStorage. Det är
samma läge som demon och den lokala stacken kör i, så det som prövas här är
exakt det som visas.
"""

from __future__ import annotations

import pytest

from app.kvitton.mejl import FEJKMEJL, MockMejlkonto
from app.kvitton.sammanfattning import (
    sammanstall,
    summeringstext,
    svara_utan_modell,
    tolka_period_ur_fraga,
)
from app.kvitton.skanning import skanna_inkorg
from app.kvitton.tolkning import ar_kvittokandidat, tolka_deterministiskt
from app.storage.memory import MemoryStorage


@pytest.fixture(autouse=True)
def _deterministisk(monkeypatch):
    monkeypatch.setenv("KVITTO_TOLKNING", "deterministisk")
    from app import config

    config.get_settings.cache_clear()
    yield
    config.get_settings.cache_clear()


# -- Identifieringen --------------------------------------------------------


def test_nyhetsbrev_och_motesmejl_ar_inte_kandidater():
    kandidater = {m.id: ar_kvittokandidat(m) for m in FEJKMEJL}
    assert kandidater["mock-012"] is False, "Nyhetsbrevet togs för ett kvitto."
    assert kandidater["mock-013"] is False, "Mötesmejlet togs för ett kvitto."
    assert all(
        kandidater[m.id] for m in FEJKMEJL if m.id not in ("mock-012", "mock-013")
    ), "Ett kvittomejl identifierades inte som kandidat."


# -- Den deterministiska avläsningen ---------------------------------------


def test_svenskt_kvitto_lases_komplett():
    mejl = FEJKMEJL[0]  # Nordvik Drivmedel
    avlast = tolka_deterministiskt(mejl.text, avsandare=mejl.avsandare)
    assert avlast.falt["brutto"] == "623.50"
    assert avlast.falt["momssats"] == "25"
    assert avlast.falt["datum"] == "2026-09-02"
    assert avlast.falt["kategori"] == "drivmedel"
    assert avlast.falt["betalstatus"] == "betald"
    assert avlast.valuta == "SEK"


def test_tusenavskiljare_och_kommatecken():
    avlast = tolka_deterministiskt("Totalt: 1 245,00 kr")
    assert avlast.falt["brutto"] == "1245.00"


def test_utlandsk_valuta_raknas_inte_om():
    mejl = next(m for m in FEJKMEJL if m.id == "mock-004")
    avlast = tolka_deterministiskt(mejl.text, avsandare=mejl.avsandare)
    assert "brutto" not in avlast.falt, "Ett USD-belopp fick inte bli ett SEK-brutto."
    assert avlast.valuta == "USD"
    assert avlast.belopp_original == "45.00 USD"
    assert "USD" in avlast.anmarkning


def test_saknat_belopp_gissas_aldrig():
    mejl = next(m for m in FEJKMEJL if m.id == "mock-009")
    avlast = tolka_deterministiskt(mejl.text, avsandare=mejl.avsandare)
    assert "brutto" not in avlast.falt
    assert "Inget totalbelopp" in avlast.anmarkning


# -- Skanningen -------------------------------------------------------------


def _skanna(storage: MemoryStorage):
    import asyncio

    return asyncio.run(skanna_inkorg(storage, "t1", MockMejlkonto()))


def _lista(storage: MemoryStorage):
    import asyncio

    return asyncio.run(storage.list_bk_underlag("t1"))


def _verifikat(storage: MemoryStorage):
    import asyncio

    return asyncio.run(storage.list_bk_verifikat("t1"))


def test_skanningen_ger_ratta_utfall():
    storage = MemoryStorage()
    resultat = _skanna(storage)
    assert resultat.genomlasta == len(FEJKMEJL)
    assert resultat.nya_kvitton == 11

    utfall = {h["mejl_id"]: h["utfall"] for h in resultat.handelser}
    assert utfall["mock-012"] == "ej_kvitto"
    assert utfall["mock-013"] == "ej_kvitto"
    assert utfall["mock-004"] == "kvitto_granska"  # USD
    assert utfall["mock-009"] == "kvitto_granska"  # belopp saknas
    assert utfall["mock-011"] == "kvitto_granska"  # möjlig dubblett
    assert utfall["mock-001"] == "kvitto"


def test_samma_mejl_skannas_aldrig_tva_ganger():
    storage = MemoryStorage()
    _skanna(storage)
    andra = _skanna(storage)
    assert andra.nya_kvitton == 0
    assert andra.hoppade_dubbletter == 11
    rader = _lista(storage)
    assert len(rader) == 11, "Andra skanningen skapade nya rader — dubblettspärren läcker."


def test_omskickat_kvitto_flaggas_som_mojlig_dubblett():
    storage = MemoryStorage()
    _skanna(storage)
    rader = _lista(storage)
    dubbletten = next(r for r in rader if r["mejl_id"] == "mock-011")
    assert dubbletten["status"] == "granska_manuellt"
    assert "dubblett" in dubbletten["anmarkning"].lower()
    # Och den fick INGET verifikat — den får inte räknas i perioden.
    verifikat = _verifikat(storage)
    assert not any(v["underlag_id"] == dubbletten["id"] for v in verifikat)


# -- Summorna ---------------------------------------------------------------


def test_sammanfattningen_raknar_bara_klara():
    storage = MemoryStorage()
    _skanna(storage)
    rader = _lista(storage)
    samman = sammanstall(rader)

    assert samman["antal"] == 11
    assert samman["antal_klara"] == 8
    assert samman["antal_granska"] == 3
    # Handräknat: 623,50 + 486 + 1245 + 289 + 745 + 199 + 1890 + 2340.
    assert samman["totalt"] == "7817.50"
    # Momsen per kvitto, öresavrundad, summerad.
    assert samman["moms"] == "1194.60"

    text = summeringstext(samman, "2026-09-01", "2026-09-30")
    assert "7 817,50 kr" in text
    assert "3 kvitton flaggades" in text


def test_svarsmotorn_svarar_grundat_utan_modell():
    storage = MemoryStorage()
    _skanna(storage)
    rader = _lista(storage)

    # "Resor" i vardagligt tal är transport OCH logi: 289 + 745 + 1 890.
    resor = svara_utan_modell("Hur mycket la vi på resor?", rader, "2026-09-01", "2026-09-30")
    assert "2 924,00 kr" in resor, resor
    assert "Stadshotellet" in resor, "Hotellnatten föll ur svaret om resor."
    transport = svara_utan_modell("Och taxi?", rader, "2026-09-01", "2026-09-30")
    assert "289,00 kr" in transport and "Stadshotellet" not in transport

    granska = svara_utan_modell("Vilka kvitton flaggades?", rader, "2026-09-01", "2026-09-30")
    assert "3 kvitton" in granska


def test_resegruppen_raknas_i_kod():
    storage = MemoryStorage()
    _skanna(storage)
    samman = sammanstall(_lista(storage))

    # Kontona står kvar som två rader...
    etiketter = {p["etikett"]: p["summa"] for p in samman["per_kategori"]}
    assert etiketter["Resor & transport"] == "1034.00"
    assert etiketter["Logi"] == "1890.00"
    # ...och gruppen bär summan som modellen annars hade behövt addera.
    resor = next(g for g in samman["per_grupp"] if g["grupp"] == "resor")
    assert resor["summa"] == "2924.00"
    assert resor["antal"] == 3


def test_modellvagen_kan_svara_grundat_om_resor():
    """I drift svarar språkmodellen, inte svara_utan_modell. Den får inte
    räkna, så summan för resor måste stå i verktygssvaret. Utan per_grupp
    fälldes "2 924 kr" av beloppsspärren och modellen svarade med bara
    transporten (1 034 kr)."""
    import asyncio
    import json

    from app.agent.kvitto_chat_tools import (
        KvittoChattContext,
        _hamta_kvittosammanfattning_impl,
        _lista_kvitton_impl,
    )
    from app.bookkeeping.beloppsgrind import check_belopp

    storage = MemoryStorage()
    _skanna(storage)
    ctx = KvittoChattContext(storage=storage, tenant_id="t1")

    asyncio.run(_hamta_kvittosammanfattning_impl(ctx, "2026-09-01", "2026-09-30"))
    svar = "I september lade ni 2 924 kr på resor."
    assert check_belopp(svar, ctx.resultat).ok, "Resesumman finns inte i verktygssvaret."

    lista = json.loads(
        asyncio.run(_lista_kvitton_impl(ctx, "2026-09-01", "2026-09-30", kategori="resor"))
    )
    motparter = {k["motpart"] for k in lista["kvitton"]}
    assert lista["antal"] == 3
    assert any("Stadshotellet" in (m or "") for m in motparter), "Hotellet föll ur resorna."

    bara_transport = json.loads(
        asyncio.run(_lista_kvitton_impl(ctx, "2026-09-01", "2026-09-30", kategori="biljett"))
    )
    assert bara_transport["antal"] == 2


def test_perioden_laser_manadsnamn_ur_fragan():
    fran, till = tolka_period_ur_fraga(
        "Hur mycket la vi på resor i mars?",
        standard_fran="2026-09-01",
        standard_till="2026-09-30",
        ar=2026,
    )
    assert (fran, till) == ("2026-03-01", "2026-03-31")


# -- Tenant-spärren på mejlkontot --------------------------------------------


def _med_env(monkeypatch, **varden):
    from app import config

    for nyckel, varde in varden.items():
        monkeypatch.setenv(nyckel, varde)
    config.get_settings.cache_clear()


def test_riktig_leverantor_utan_agare_ger_ingen_koppling(monkeypatch):
    from app.kvitton.mejl import valj_mejlkonto

    _med_env(monkeypatch, KVITTO_MEJL_LEVERANTOR="gmail", KVITTO_MEJL_TENANT="")
    assert valj_mejlkonto("tenant-a") is None, (
        "En Gmail-koppling utan ägare gavs ut — då läser varje tenant samma inkorg."
    )


def test_riktig_leverantor_bara_for_agaren(monkeypatch):
    from app.kvitton.mejl import GmailKonto, valj_mejlkonto

    _med_env(monkeypatch, KVITTO_MEJL_LEVERANTOR="gmail", KVITTO_MEJL_TENANT="tenant-a")
    assert isinstance(valj_mejlkonto("tenant-a"), GmailKonto)
    assert valj_mejlkonto("tenant-b") is None, "En annan tenant fick ägarens inkorg."


def test_mocken_kan_begransas_till_en_tenant(monkeypatch):
    from app.kvitton.mejl import MockMejlkonto, valj_mejlkonto

    _med_env(
        monkeypatch,
        KVITTO_MEJL_LEVERANTOR="mock",
        KVITTO_MEJL_TENANT="",
        DATABASE_URL="",
        ENVIRONMENT="",
        RAILWAY_ENVIRONMENT_NAME="",
    )
    assert isinstance(valj_mejlkonto("vem-som-helst"), MockMejlkonto)
    _med_env(monkeypatch, KVITTO_MEJL_LEVERANTOR="mock", KVITTO_MEJL_TENANT="qa")
    assert valj_mejlkonto("annan") is None
    assert isinstance(valj_mejlkonto("qa"), MockMejlkonto)


def test_mocken_ger_inte_hittepakvitton_i_miljo_med_kunddata(monkeypatch):
    from app.kvitton.mejl import valj_mejlkonto

    _med_env(
        monkeypatch,
        KVITTO_MEJL_LEVERANTOR="mock",
        KVITTO_MEJL_TENANT="",
        ENVIRONMENT="development",
    )
    assert valj_mejlkonto("riktig-kund") is None, (
        "Mocken gällde alla tenants i en spegel av produktionen — varje kund "
        "som tryckte Skanna hade fått elva påhittade kvitton."
    )


# -- Beloppsläsaren: fallen granskningen hittade ----------------------------


@pytest.mark.parametrize(
    ("text", "brutto", "valuta"),
    [
        ("Totalt: 45,00 €", None, "EUR"),
        ("Total: EUR 45.00", None, "EUR"),
        ("Amount: 45.00\nCurrency: USD", None, "USD"),
        ("Subtotal: 40.00 kr\nTotal: $45.00", None, "USD"),
        ("Subtotal: 996,00 kr\nTotal: 1 245,00 kr", "1245.00", "SEK"),
        ("Summa 3 artiklar 450,00 kr", None, "SEK"),
        ("Total: 1,245.00 kr", "1245.00", "SEK"),
        ("Totalt: 1.245,00 kr", "1245.00", "SEK"),
        ("Rabatt amount: 50 kr\nAtt betala: 400 kr", "400", "SEK"),
    ],
)
def test_beloppslasaren(text, brutto, valuta):
    avlast = tolka_deterministiskt(text)
    assert avlast.falt.get("brutto") == brutto
    assert avlast.valuta == valuta


# -- Summorna räknar bara utlägg --------------------------------------------


def test_intakter_raknas_aldrig_som_utlagg():
    from decimal import Decimal

    rader = [
        {"status": "klar", "riktning": "kostnad", "brutto": Decimal("100.00"), "momssats": Decimal("0.25"), "kategori": "kontorsmateriel"},
        {"status": "klar", "riktning": "intakt", "brutto": Decimal("10000.00"), "momssats": Decimal("0.25"), "kategori": None},
    ]
    samman = sammanstall(rader)
    assert samman["totalt"] == "100.00", "En kundfaktura räknades som ett utlägg."
    assert samman["antal"] == 1


# -- Valutaspärren gäller även modellvägen ----------------------------------


def test_valutasparren_tar_bort_sek_belopp_ur_modellens_falt():
    from decimal import Decimal

    from app.kvitton.tolkning import valutaspärr

    modellens = {"brutto": Decimal("45.00"), "momssats": Decimal("0.25"), "motpart": "Figmara Inc."}
    falt, valuta, original, anmarkning = valutaspärr(modellens, "Total: $45.00 USD")
    assert "brutto" not in falt and "momssats" not in falt
    assert falt["motpart"] == "Figmara Inc."
    assert (valuta, original) == ("USD", "45.00 USD")
    assert "USD" in anmarkning


def test_valutasparren_ror_inte_svenska_kvitton():
    from decimal import Decimal

    from app.kvitton.tolkning import valutaspärr

    modellens = {"brutto": Decimal("623.50")}
    falt, valuta, original, _ = valutaspärr(modellens, "Totalt: 623,50 kr")
    assert falt == modellens and valuta == "SEK" and original is None


# -- Godkännandet via API:t --------------------------------------------------


def _klient():
    from fastapi.testclient import TestClient

    from app.main import app

    return TestClient(app)


def test_godkann_hela_vagen_med_validering(monkeypatch):
    _med_env(
        monkeypatch,
        KVITTO_MEJL_LEVERANTOR="mock",
        KVITTO_MEJL_TENANT="",
        DATABASE_URL="",
        REDIS_URL="",
        GEMINI_API_KEY="",
        OPENAI_API_KEY="",
    )
    from app.config import get_settings

    nyckel = {"X-API-Key": get_settings().snajp_demo_api_key}
    with _klient() as klient:
        skan = klient.post("/api/kvitton/skanna", headers=nyckel)
        assert skan.status_code == 200, skan.text
        kvitton = klient.get("/api/kvitton", headers=nyckel).json()["kvitton"]
        usd = next(k for k in kvitton if k["belopp_original"] == "45.00 USD")

        dåligt = klient.post(f"/api/kvitton/{usd['id']}/godkann", headers=nyckel, json={"brutto": "473", "momssats": "7"})
        assert dåligt.status_code == 422, "En momssats som inte finns släpptes igenom."

        fel_kategori = klient.post(f"/api/kvitton/{usd['id']}/godkann", headers=nyckel, json={"kategori": "hittepa"})
        assert fel_kategori.status_code == 422, "En okänd kategori hade blivit ett 500 i verifikatbygget."

        # Float-belopp i JSON ska tas emot, inte tyst ignoreras.
        ok = klient.post(
            f"/api/kvitton/{usd['id']}/godkann",
            headers=nyckel,
            json={"brutto": 473.0, "momssats": "0"},
        )
        assert ok.status_code == 200 and ok.json()["godkand"] is True, ok.text
        assert ok.json()["underlag"]["brutto"] == "473.00"
        assert ok.json()["underlag"]["valuta"] == "SEK", "Kronbeloppet märktes fortfarande USD."

        igen = klient.post(f"/api/kvitton/{usd['id']}/godkann", headers=nyckel, json={"brutto": "1"})
        assert igen.status_code == 409, "Ett redan godkänt kvitto gick att rätta förbi sitt verifikat."

        okant = klient.post("/api/kvitton/inte-en-uuid/godkann", headers=nyckel, json={})
        assert okant.status_code == 404

        csv = klient.get("/api/kvitton/export.csv?fran=2026-09-01&till=2026-09-30", headers=nyckel)
        assert csv.content.startswith(b"\xef\xbb\xbfDatum;"), (
            "CSV:n börjar inte med BOM + rubrikrad — Excel på svensk Windows läser då å/ä/ö fel."
        )
        rad = next(r for r in csv.text.splitlines() if "Figmara" in r)
        assert "473.00" in rad and "45.00 USD" in rad, rad


def test_godkann_gissar_aldrig_betalstatus(monkeypatch):
    import asyncio

    _med_env(monkeypatch, DATABASE_URL="", REDIS_URL="", GEMINI_API_KEY="", OPENAI_API_KEY="")
    from decimal import Decimal

    from app.config import DEFAULT_TENANT_ID, get_settings

    nyckel = {"X-API-Key": get_settings().snajp_demo_api_key}
    with _klient() as klient:
        storage = klient.app.state.storage
        rad = asyncio.run(
            storage.create_bk_underlag(
                DEFAULT_TENANT_ID,
                sha256="test-betalstatus",
                filnamn="it-faktura.pdf",
                mimetyp="application/pdf",
                status="granska_manuellt",
                datum="2026-09-10",
                motpart="IT-bolaget AB",
                brutto=Decimal("12500.00"),
                momssats=Decimal("0.25"),
                kategori="it_tjanst",
            )
        )
        utan = klient.post(f"/api/kvitton/{rad['id']}/godkann", headers=nyckel, json={})
        assert utan.status_code == 200
        assert utan.json()["godkand"] is False, (
            "Kvittot godkändes utan betalstatus — koden gissade 'betald' och "
            "bokade en möjligen obetald faktura mot bankkontot."
        )
        med = klient.post(
            f"/api/kvitton/{rad['id']}/godkann", headers=nyckel, json={"betalstatus": "obetald"}
        )
        assert med.json()["godkand"] is True, med.text
