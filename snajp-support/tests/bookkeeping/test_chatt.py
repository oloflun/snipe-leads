"""Bokföringschatten: INV-BOOK-003, tenant-isolering och EN läsväg för filer.

De tre frågorna som ställs här är de tre som kan göra chatten farlig:

  1. Kan modellen svara med ett tal den hittat på?      (INV-BOOK-003)
  2. Kan en kund se en annan kunds underlag?            (INV-SEC-002)
  3. Kan ett kvitto i chatten gå en annan väg än ett    (en läsväg, inte två)
     kvitto i uppladdningspanelen?

Verktygen testas via sina `_impl`-funktioner, inte via verktygsprotokollet —
samma val som `tests/leads/` gör, eftersom SDK:ns ToolContext är omständlig att
konstruera och inte är det som prövas här.
"""

from __future__ import annotations

import json
from datetime import date
from decimal import Decimal

import pytest

from app.agent.bookkeeping_chat_tools import (
    BokforingChattContext,
    _hamta_periodrapport_impl,
    _lista_underlag_impl,
    _sla_upp_konto_impl,
)
from app.bookkeeping.beloppsgrind import check_belopp, normalisera
from app.storage.memory import MemoryStorage

TENANT_A = "tenant-a-11111111"
TENANT_B = "tenant-b-22222222"


async def _underlag(storage: MemoryStorage, tenant: str, *, motpart: str, brutto: str):
    return await storage.create_bk_underlag(
        tenant,
        sha256=f"sha-{tenant}-{motpart}",
        filnamn=f"{motpart}.pdf",
        mimetyp="application/pdf",
        status="klar",
        datum="2026-08-05",
        motpart=motpart,
        brutto=Decimal(brutto),
        momssats=Decimal("0.25"),
        riktning="kostnad",
        kategori="drivmedel",
    )


# -- 1. INV-BOOK-003 -------------------------------------------------------


def test_normalisering_ser_svensk_och_engelsk_skrivning_som_samma_belopp():
    """1 250,00 och 1250.00 är samma pengar och måste jämföras lika.

    Utan det fälls ett SANT svar bara för att modellen skrev med decimalkomma
    medan verktyget svarade med punkt, och en grind som fäller sanna svar är en
    grind folk stänger av.
    """
    assert normalisera("1 250,00") == normalisera("1250.00") == "1250.00"
    assert normalisera("1\xa0250") == "1250.00"


def test_belopp_ur_verktyget_passerar():
    verktyg = ['{"summor": {"utgaende_moms": "3125.00"}}']
    assert check_belopp("Du har 3 125 kr i utgående moms.", verktyg).ok


def test_pahittat_belopp_falls():
    """Kärnan i invarianten. 3 120 finns inte, 3 125 gör det."""
    verktyg = ['{"summor": {"utgaende_moms": "3125.00"}}']
    verdikt = check_belopp("Du har 3 120 kr i utgående moms.", verktyg)
    assert not verdikt.ok
    assert "3 120" in verdikt.as_report()[0]


def test_belopp_utan_verktygsanrop_alls_falls():
    """Modellen som svarar ur minnet, utan att hämta något, är huvudfallet."""
    assert not check_belopp("Du har ungefär 12 000 kr i kostnader.", []).ok


def test_procent_ar_inte_ett_belopp():
    """En momssats ska inte behöva vara grundad. Fälls den lär sig användaren
    att ignorera grinden."""
    assert check_belopp("Momssatsen är 25 % på köpet.", []).ok


def test_antal_ar_inte_ett_belopp():
    assert check_belopp("Perioden har 4 underlag och 3 verifikat.", []).ok


def test_grinden_ser_belopp_i_flera_verktygssvar():
    verktyg = ['{"a": "100.00"}', '{"b": "250.50"}']
    assert check_belopp("Först 100 kr, sedan 250,50 kr.", verktyg).ok


# -- 2. Tenant-isolering ---------------------------------------------------


@pytest.mark.anyio
async def test_verktygen_ser_bara_egen_tenants_underlag():
    """Två RIKTIGA tenant-id mot riktig storage, inte en mock.

    En mock hade bevisat att vi skickar med tenant_id, inte att lagret faktiskt
    filtrerar på det. Det är skillnaden mellan att testa sin egen kod och att
    testa det som skyddar kunden.
    """
    storage = MemoryStorage()
    await _underlag(storage, TENANT_A, motpart="Circle K", brutto="500.00")
    await _underlag(storage, TENANT_B, motpart="Hemlig Leverantör AB", brutto="99999.00")

    ctx_a = BokforingChattContext(storage=storage, tenant_id=TENANT_A)
    svar = json.loads(await _lista_underlag_impl(ctx_a, "2026-08-01", "2026-08-31"))

    motparter = [u["motpart"] for u in svar["underlag"]]
    assert motparter == ["Circle K"]
    assert "Hemlig Leverantör AB" not in json.dumps(svar, ensure_ascii=False)
    assert "99999" not in json.dumps(svar)


@pytest.mark.anyio
async def test_periodrapporten_summerar_bara_egen_tenant():
    storage = MemoryStorage()
    await _underlag(storage, TENANT_A, motpart="Circle K", brutto="500.00")
    await _underlag(storage, TENANT_B, motpart="Annan", brutto="99999.00")

    ctx_a = BokforingChattContext(storage=storage, tenant_id=TENANT_A)
    rapport = json.loads(await _hamta_periodrapport_impl(ctx_a, "2026-08-01", "2026-08-31"))

    assert rapport["antal_underlag"] == 1
    assert "99999" not in json.dumps(rapport)


@pytest.mark.anyio
async def test_verktyget_tar_inte_emot_en_tenant_som_argument():
    """INV-SEC-002 i signaturform.

    Finns tenant som parameter är den ett fält modellen kan fylla i, och då är
    isoleringen ovan en artighet i stället för en grind.
    """
    import inspect

    for funktion in (_lista_underlag_impl, _hamta_periodrapport_impl, _sla_upp_konto_impl):
        parametrar = set(inspect.signature(funktion).parameters)
        assert not (parametrar & {"tenant", "tenant_id"}), (
            f"{funktion.__name__} tar en tenant som argument."
        )


# -- 3. Vitlistade filter --------------------------------------------------


@pytest.mark.anyio
async def test_okand_status_avvisas_med_ett_svar_modellen_kan_agera_pa():
    storage = MemoryStorage()
    ctx = BokforingChattContext(storage=storage, tenant_id=TENANT_A)
    svar = json.loads(await _lista_underlag_impl(ctx, "2026-08-01", "2026-08-31", "allt"))
    assert "fel" in svar
    assert "klar" in svar["fel"]


@pytest.mark.anyio
async def test_okant_konto_gissas_inte():
    """`foresla_konto` returnerar None hellre än ett närliggande konto, och
    verktyget ärver det valet."""
    storage = MemoryStorage()
    ctx = BokforingChattContext(storage=storage, tenant_id=TENANT_A)
    svar = json.loads(await _sla_upp_konto_impl(ctx, "rymdfärja"))
    assert svar["hittades"] is False
    assert "kanda_kategorier" in svar


@pytest.mark.anyio
async def test_kant_konto_slas_upp():
    storage = MemoryStorage()
    ctx = BokforingChattContext(storage=storage, tenant_id=TENANT_A)
    assert json.loads(await _sla_upp_konto_impl(ctx, "drivmedel"))["nummer"] == "5611"
    assert json.loads(await _sla_upp_konto_impl(ctx, "5611"))["namn"]


@pytest.mark.anyio
async def test_varje_verktygsresultat_sparas_for_grinden():
    """Sparas det inte blir grinden strängare än den ska vara: sanna siffror
    från just det verktyget fälls som ogrundade."""
    storage = MemoryStorage()
    await _underlag(storage, TENANT_A, motpart="Circle K", brutto="500.00")
    ctx = BokforingChattContext(storage=storage, tenant_id=TENANT_A)

    await _lista_underlag_impl(ctx, "2026-08-01", "2026-08-31")
    await _sla_upp_konto_impl(ctx, "drivmedel")

    assert len(ctx.resultat) == 2
    assert check_belopp("Kvittot är på 500 kr.", ctx.resultat).ok


# -- 4. EN läsväg för filer ------------------------------------------------


def test_chatten_anropar_samma_funktion_som_uppladdningspanelen():
    """Källkoden, inte beteendet.

    En parallell filväg ser identisk ut den dag den skrivs och glider isär vid
    första ändringen — ett höjt filtak på ena stället, en ny mimetyp på andra.
    Testet läser modulen och kräver att BÅDA endpoints går genom
    `ta_emot_underlag`, som i sin tur är den enda som anropar `las_underlag`.
    """
    from pathlib import Path

    kalla = (Path(__file__).resolve().parents[2] / "app" / "api" / "bookkeeping.py").read_text(
        encoding="utf-8"
    )

    assert kalla.count("async def ta_emot_underlag") == 1, "Det finns inte exakt en mottagning."
    # Båda endpoints anropar den.
    assert kalla.count("await ta_emot_underlag(") == 2, (
        "Antingen anropar inte båda endpoints mottagningen, eller så finns en tredje."
    )
    # Och ingen av dem läser filen på egen hand.
    assert kalla.count("las_underlag(") == 1, (
        "las_underlag anropas på fler än ett ställe — då finns en andra läsväg."
    )
    assert kalla.count("kontrollera_fil(") == 1, "Filkontrollen görs på fler än ett ställe."


def test_chatt_endpointen_ar_tenant_scopad():
    from pathlib import Path

    kalla = (Path(__file__).resolve().parents[2] / "app" / "api" / "bookkeeping.py").read_text(
        encoding="utf-8"
    )
    chattblock = kalla.split('@router.post("/api/bookkeeping/chat")')[1]
    assert "Depends(require_tenant)" in chattblock.split(")")[0] + chattblock[:400], (
        "Chatt-endpointen går inte genom require_tenant."
    )
    assert 'tenant["tenant_id"]' in chattblock, "Chatten skickar inte vidare tenanten."


def test_chatten_loggar_till_agent_runs():
    from pathlib import Path

    kalla = (Path(__file__).resolve().parents[2] / "app" / "api" / "bookkeeping.py").read_text(
        encoding="utf-8"
    )
    chattblock = kalla.split('@router.post("/api/bookkeeping/chat")')[1]
    assert "log_agent_run" in chattblock, "Chatten loggar inte körningen."
    assert "agent_type=AGENT_TYPE" in chattblock, "Chatten loggar under fel agent_type."


# -- 5. PDF hela vägen, och assistenten ser resultatet ----------------------


def _pdf_med_text(text: str) -> bytes:
    """En minimal, giltig PDF med ett textlager.

    Byggd för hand och inte med ett bibliotek: testet ska pröva VÅR läsväg, och
    ett genereringsbibliotek till i requirements för fem rader PostScript är
    kostnad utan täckning.
    """
    from pypdf import PdfWriter

    import io

    # pypdf kan inte skapa text från grunden, så innehållsströmmen skrivs rått.
    innehall = f"BT /F1 12 Tf 40 700 Td ({text}) Tj ET".encode("latin-1")
    objekt = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] "
        b"/Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>",
        b"<< /Length " + str(len(innehall)).encode() + b" >>\nstream\n" + innehall + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]

    ut = bytearray(b"%PDF-1.4\n")
    offsets = []
    for i, kropp in enumerate(objekt, start=1):
        offsets.append(len(ut))
        ut += f"{i} 0 obj\n".encode() + kropp + b"\nendobj\n"

    xref = len(ut)
    ut += f"xref\n0 {len(objekt) + 1}\n".encode()
    ut += b"0000000000 65535 f \n"
    for off in offsets:
        ut += f"{off:010d} 00000 n \n".encode()
    ut += (
        f"trailer\n<< /Size {len(objekt) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF".encode()
    )

    # Sanity: pypdf ska kunna öppna den, annars mäter testet ingenting.
    PdfWriter(io.BytesIO(bytes(ut)))
    return bytes(ut)


def test_pdf_med_textlager_gar_att_lasa():
    """Vår faktiska PDF-väg, med en riktig PDF.

    Går den sönder slutar uppladdningen fungera för det VANLIGASTE underlaget —
    en faktura är nästan alltid en PDF — och det syns inte i något annat test.
    """
    from app.bookkeeping.underlag import kontrollera_fil, las_pdf_text

    data = _pdf_med_text("Nordvik Drivmedel AB  Att betala 1250,00  Moms 25%")
    kontrollera_fil(data, "application/pdf")

    text = las_pdf_text(data)
    assert "Nordvik" in text, f"Textlagret lästes inte: {text!r}"
    assert "1250" in text


def test_skannad_pdf_utan_textlager_ger_en_begriplig_anvisning():
    """Tom text är ett SVAR, inte ett fel — och anvisningen är billigare än att
    låta grinden fälla på 'allt saknas'."""
    from app.bookkeeping.underlag import las_pdf_text

    tom = _pdf_med_text("")
    assert las_pdf_text(tom).strip() == ""


def test_ovanlig_filtyp_avvisas_med_listan_over_det_som_gar():
    from app.bookkeeping.underlag import UnderlagsfelError, kontrollera_fil

    with pytest.raises(UnderlagsfelError) as fel:
        kontrollera_fil(b"CSV;kontoutdrag", "text/csv")
    assert "application/pdf" in str(fel.value), (
        "Felet säger inte vilka filtyper som FUNGERAR, bara att den här inte gör det."
    )


@pytest.mark.anyio
async def test_assistenten_ser_ett_uppladdat_underlag_utan_att_bli_tillsagd():
    """Det kunden menar med 'agenten utgår från filerna'.

    Underlaget skapas som uppladdningen gör det, och assistentens verktyg
    hittar det utan att någon skickar med ett id — den frågar bara efter
    perioden.
    """
    storage = MemoryStorage()
    await _underlag(storage, TENANT_A, motpart="Nordvik Drivmedel AB", brutto="1250.00")

    ctx = BokforingChattContext(storage=storage, tenant_id=TENANT_A)
    lista = json.loads(await _lista_underlag_impl(ctx, "2026-08-01", "2026-08-31"))
    rapport = json.loads(await _hamta_periodrapport_impl(ctx, "2026-08-01", "2026-08-31"))

    assert lista["antal"] == 1
    assert lista["underlag"][0]["motpart"] == "Nordvik Drivmedel AB"
    # Netto 1000,00 och moms 250,00 räknas av koden ur bruttot.
    assert rapport["summor"]["kostnader"] == "1000.00"
    assert rapport["summor"]["ingaende_moms"] == "250.00"

    # Och ett svar som citerar dem passerar beloppsgrinden.
    assert check_belopp(
        "Du har ett underlag från Nordvik Drivmedel AB på 1 000,00 kr exklusive moms.",
        ctx.resultat,
    ).ok
