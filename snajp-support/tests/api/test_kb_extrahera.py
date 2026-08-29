"""POST /api/kb/extrahera — PDF till text, med en SYNLIG förhandsvisning.

Fas 5.5 (Testchatt, snipe-0r9). Kunskapsbasens egen invändning mot PDF
(components/settings/Kunskapsbas.tsx) är att en halvläst PDF ger TYST
sönderhackad text agenten sedan citerar som korrekt. Den här endpointen gör
extraktionen SYNLIG i stället för att fortsätta utesluta PDF: den sparar
ingenting, returnerar bara text + sidantal + en varning när textlagret ser
tunt eller tomt ut. Kunden godkänner explicit efteråt via samma
POST /api/kb som resten av kunskapsbasen redan använder — den vägen testas
inte här, den finns redan (tests/api/test_kb_seedning.py m.fl.).

PDF-filerna byggs i testet med pypdf's egen writer, ingen fixturfil på disk.
"""

from __future__ import annotations

import base64
import io

import pytest
from httpx import ASGITransport, AsyncClient
from pypdf import PdfWriter
from pypdf.generic import ContentStream, DictionaryObject, NameObject

from app.config import get_settings
from app.main import app

DEMO = {"X-API-Key": get_settings().snajp_demo_api_key}


@pytest.fixture
def anyio_backend():
    return "asyncio"


def _client():
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


def _pdf_med_text(sidor: list[str]) -> bytes:
    """En liten flersidig PDF med RIKTIG, maskinläsbar text per sida.

    pypdf:s writer har ingen "skriv text"-metod (det är läsarens/redigerarens
    jobb, inte skaparens) — sidans innehållsström byggs därför för hand: ett
    Helvetica-typsnitt i sidans resurser och en BT/Tj-operation per rad.
    Verifierat manuellt mot den installerade pypdf-versionen (6.16.2) att
    PdfReader.extract_text() läser tillbaka exakt den skrivna texten.
    """
    writer = PdfWriter()
    for text in sidor:
        page = writer.add_blank_page(width=200, height=200)
        font = DictionaryObject(
            {
                NameObject("/Type"): NameObject("/Font"),
                NameObject("/Subtype"): NameObject("/Type1"),
                NameObject("/BaseFont"): NameObject("/Helvetica"),
            }
        )
        font_ref = writer._add_object(font)  # noqa: SLF001 — writer saknar publikt API för detta
        page[NameObject("/Resources")] = DictionaryObject(
            {NameObject("/Font"): DictionaryObject({NameObject("/F1"): font_ref})}
        )
        sakrad = text.replace("\\", r"\\").replace("(", r"\(").replace(")", r"\)")
        stream = ContentStream(None, writer)
        stream.set_data(f"BT /F1 12 Tf 10 180 Td ({sakrad}) Tj ET".encode("latin-1"))
        page[NameObject("/Contents")] = writer._add_object(stream)  # noqa: SLF001

    buffer = io.BytesIO()
    writer.write(buffer)
    return buffer.getvalue()


def _pdf_utan_text(antal_sidor: int = 1) -> bytes:
    """En giltig PDF helt utan innehållsström — motsvarar en skannad sida."""
    writer = PdfWriter()
    for _ in range(antal_sidor):
        writer.add_blank_page(width=200, height=200)
    buffer = io.BytesIO()
    writer.write(buffer)
    return buffer.getvalue()


def _data_url(data: bytes, mimetyp: str = "application/pdf") -> str:
    return f"data:{mimetyp};base64,{base64.b64encode(data).decode()}"


@pytest.mark.anyio
async def test_utan_nyckel_svarar_401():
    async with app.router.lifespan_context(app):
        async with _client() as client:
            svar = await client.post(
                "/api/kb/extrahera",
                json={"filename": "villkor.pdf", "data_url": _data_url(_pdf_utan_text())},
            )
            assert svar.status_code == 401


@pytest.mark.anyio
async def test_extraherar_riktig_text_utan_varning():
    data = _pdf_med_text(["Vi levererar till Norge inom 5-7 arbetsdagar."])
    async with app.router.lifespan_context(app):
        async with _client() as client:
            svar = await client.post(
                "/api/kb/extrahera",
                headers=DEMO,
                json={"filename": "villkor.pdf", "data_url": _data_url(data)},
            )
            assert svar.status_code == 200, svar.text
            kropp = svar.json()
            assert "Norge" in kropp["text"]
            assert kropp["sidor"] == 1
            assert kropp["varning"] is None


@pytest.mark.anyio
async def test_tomt_textlager_ger_varning():
    """Kärnan i 6.5: en skannad PDF (inget textlager) ska INTE tyst returnera
    tom text som om den vore ett fullgott svar."""
    data = _pdf_utan_text()
    async with app.router.lifespan_context(app):
        async with _client() as client:
            svar = await client.post(
                "/api/kb/extrahera",
                headers=DEMO,
                json={"filename": "skannad.pdf", "data_url": _data_url(data)},
            )
            assert svar.status_code == 200, svar.text
            kropp = svar.json()
            assert kropp["text"] == ""
            assert kropp["sidor"] == 1
            assert kropp["varning"], "Ett tomt textlager gav ingen varning."


@pytest.mark.anyio
async def test_glest_textlager_over_flera_sidor_ger_varning():
    """En enda kort rad utspridd över tre sidor är under tröskeln per sida —
    typiskt en PDF där bara enstaka artefakter lästes av, inte löptext."""
    data = _pdf_med_text(["Hej", "", ""])
    async with app.router.lifespan_context(app):
        async with _client() as client:
            svar = await client.post(
                "/api/kb/extrahera",
                headers=DEMO,
                json={"filename": "gles.pdf", "data_url": _data_url(data)},
            )
            assert svar.status_code == 200, svar.text
            kropp = svar.json()
            assert kropp["sidor"] == 3
            assert kropp["varning"], "Ett glest textlager (< 20 tecken/sida) gav ingen varning."


@pytest.mark.anyio
async def test_fel_mimetyp_avvisas():
    data_url = "data:text/plain;base64," + base64.b64encode(b"inte en pdf").decode()
    async with app.router.lifespan_context(app):
        async with _client() as client:
            svar = await client.post(
                "/api/kb/extrahera",
                headers=DEMO,
                json={"filename": "text.txt", "data_url": data_url},
            )
            assert svar.status_code == 422
            assert "text/plain" in svar.json()["detail"]


@pytest.mark.anyio
async def test_for_stor_fil_avvisas():
    # 500 KB över taket (8 MB) av rena nollor, ingen riktig PDF-struktur krävs
    # för att storlekskontrollen ska slå till FÖRE pypdf ens kallas. Base64-
    # längden (~11,9 miljoner tecken) ligger under schemats grova yttertak
    # (14 miljoner, se KbExtraheraRequest) så att det är ENDPOINTENS egen,
    # begripliga felmeddelande som testas här, inte pydantics.
    stor = b"0" * (8 * 1024 * 1024 + 500 * 1024)
    async with app.router.lifespan_context(app):
        async with _client() as client:
            svar = await client.post(
                "/api/kb/extrahera",
                headers=DEMO,
                json={"filename": "stor.pdf", "data_url": _data_url(stor)},
            )
            assert svar.status_code == 422
            assert "MB" in svar.json()["detail"]


@pytest.mark.anyio
async def test_trasig_data_url_avvisas_begripligt():
    async with app.router.lifespan_context(app):
        async with _client() as client:
            svar = await client.post(
                "/api/kb/extrahera",
                headers=DEMO,
                json={"filename": "trasig.pdf", "data_url": "inte-en-data-url"},
            )
            assert svar.status_code == 422
            assert "data-URL" in svar.json()["detail"]


@pytest.mark.anyio
async def test_extraktionen_skriver_ingenting_till_kunskapsbasen():
    """Den viktigaste gränsen: extraktion är läsning, inte en genväg förbi
    människans godkännande (samma princip som INV-LEARN-001)."""
    data = _pdf_med_text(["Vi levererar till Norge inom 5-7 arbetsdagar."])
    async with app.router.lifespan_context(app):
        async with _client() as client:
            innan = await client.get("/api/kb", headers=DEMO)
            antal_innan = len(innan.json()["articles"])

            svar = await client.post(
                "/api/kb/extrahera",
                headers=DEMO,
                json={"filename": "villkor.pdf", "data_url": _data_url(data)},
            )
            assert svar.status_code == 200, svar.text

            efter = await client.get("/api/kb", headers=DEMO)
            assert len(efter.json()["articles"]) == antal_innan
