"""INV-DATA-007: kundtext lämnar huset maskerad, och sökgrundningen stannar i leadssökningen.

Två vägar som dataskyddsbedömningen av Gemini (2026-11-18, A1, A2, A6) pekade ut:

  * Personnummer gick omaskerade till Google på två vägar: uppsägningsklassaren
    fick hela meddelandet, och inbäddningarna räknades på omaskerad kundtext.
    Huvudanropet och triagen var maskerade sedan tidigare. Maskeringen sitter
    nu där texten lämnar systemet: i `classify_cancellation_risk` och i
    `embed_text`, ett ställe per väg.
  * Sökgrundningen (Googles sökverktyg i Gemini) sparar sökfrågor härledda ur
    prompten i upp till tre dygn, och det går inte att stänga av. I dag får den
    bara målgrupp, kriterier och bolagsnamn. Testerna nedan fäller om verktyget
    börjar användas någon annanstans, eller om funktionerna som bygger frågan
    får nya indata som kan bära kundmejl.

Testerna fångar den faktiska strängen som skickas, med en falsk klient (samma
mönster som tests/test_maskering_wiring.py). Ett svar som inte upprepar numret
bevisar ingenting om vad som skickades.
"""

from __future__ import annotations

import ast
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.moderation.maskering import PLATSHALLARE


def _med_kontrollsiffra(nio: str) -> str:
    summa = 0
    for i, tecken in enumerate(nio):
        varde = int(tecken) * (2 if i % 2 == 0 else 1)
        summa += varde - 9 if varde > 9 else varde
    return nio + str((10 - summa % 10) % 10)


_TIO = _med_kontrollsiffra("850101123")
PNR = f"{_TIO[:6]}-{_TIO[6:]}"
ORDERNUMMER = "1234567890"

_APP = Path(__file__).resolve().parents[2] / "app"
_REPO = Path(__file__).resolve().parents[3]


@pytest.fixture
def anyio_backend():
    return "asyncio"


# -- Maskeringen: uppsägningsklassaren ------------------------------------------


def _klassarklient() -> MagicMock:
    svar = MagicMock()
    svar.choices = [MagicMock(message=MagicMock(content='{"uppsagningsavsikt": 0.1, "missnoje": 0.2}'))]
    klient = MagicMock()
    klient.chat.completions.create = AsyncMock(return_value=svar)
    return klient


def _skickat(klient: MagicMock) -> str:
    anrop = klient.chat.completions.create.await_args
    return "\n".join(str(m.get("content")) for m in anrop.kwargs["messages"])


@pytest.mark.anyio
async def test_klassaren_far_inte_personnumret():
    from app.agent import retention_classifier

    klient = _klassarklient()
    with patch.object(retention_classifier, "get_llm_client", return_value=klient):
        await retention_classifier.classify_cancellation_risk(
            f"Jag vill säga upp, mitt personnummer är {PNR} och ordern {ORDERNUMMER}."
        )
    skickat = _skickat(klient)
    assert PNR not in skickat and _TIO not in skickat.replace("-", "")
    assert PLATSHALLARE in skickat
    assert ORDERNUMMER in skickat, "ordernumret maskerades, för brett mönster"


@pytest.mark.anyio
async def test_klassaren_lamnar_vanlig_text_orord():
    from app.agent import retention_classifier

    text = "Hej! Jag vill avsluta mitt abonnemang 556677-8899 från den 1 december."
    klient = _klassarklient()
    with patch.object(retention_classifier, "get_llm_client", return_value=klient):
        await retention_classifier.classify_cancellation_risk(text)
    assert text in _skickat(klient)


# -- Maskeringen: inbäddningarna ------------------------------------------------


def _inbaddningsklient() -> MagicMock:
    svar = MagicMock()
    svar.data = [MagicMock(embedding=[0.1, 0.2])]
    klient = MagicMock()
    klient.embeddings.create = AsyncMock(return_value=svar)
    return klient


@pytest.fixture
def tom_cache(monkeypatch):
    """En egen minnescache per test, så att ingen vektor från ett annat test
    svarar i stället för klienten."""
    from app.agent import embeddings
    from app.cache.embeddingcache import MinnesEmbeddingCache

    cache = MinnesEmbeddingCache()
    monkeypatch.setattr(embeddings, "hamta_cache", lambda: cache)
    monkeypatch.setattr(embeddings, "_har_klagat", False)
    return cache


@pytest.mark.anyio
async def test_inbaddningen_far_inte_personnumret(tom_cache):
    from app.agent import embeddings

    klient = _inbaddningsklient()
    with patch.object(embeddings, "get_embedding_client", return_value=klient):
        await embeddings.embed_text(f"Order {ORDERNUMMER} Hej, mitt personnummer är {PNR}.")
    skickat = klient.embeddings.create.await_args.kwargs["input"]
    assert PNR not in skickat and _TIO not in skickat.replace("-", "")
    assert PLATSHALLARE in skickat
    assert ORDERNUMMER in skickat


@pytest.mark.anyio
async def test_inbaddningen_via_vertex_far_inte_personnumret(tom_cache, monkeypatch):
    """Vertex-vägen (:predict) är den som körs i drift."""
    from app.agent import embeddings

    skickade: list[str] = []

    async def fanga(_settings, text):
        skickade.append(text)
        return [0.1]

    monkeypatch.setattr(embeddings, "_vertex_predict", fanga)
    monkeypatch.setattr(embeddings, "get_settings", lambda: MagicMock(google_service_account_json="{}"))
    with patch.object(embeddings, "get_embedding_client", return_value=MagicMock()):
        await embeddings.embed_text(f"mitt personnummer är {PNR}")
    assert skickade and PNR not in skickade[0] and PLATSHALLARE in skickade[0]


@pytest.mark.anyio
async def test_inbaddningen_lamnar_vanlig_text_och_kunskapsbasen_orord(tom_cache):
    """En kunskapsbasartikel med ordernummer, organisationsnummer och telefon
    går ut tecken för tecken som förut: samma text, samma vektor, samma
    cachenyckel."""
    from app.agent import embeddings

    artikel = "Returer\nSkicka till Snajp AB, org.nr 556677-8899, tel 070-123 45 67, ordernummer 1234567890."
    klient = _inbaddningsklient()
    with patch.object(embeddings, "get_embedding_client", return_value=klient):
        await embeddings.embed_text(artikel)
    assert klient.embeddings.create.await_args.kwargs["input"] == artikel


@pytest.mark.anyio
async def test_samma_maskering_vid_skrivning_och_lasning(tom_cache):
    """Cachen nycklas på den maskerade texten. Två texter som bara skiljer sig
    i vilket personnummer som står ger samma vektor och ett enda anrop."""
    from app.agent import embeddings

    annat = _med_kontrollsiffra("900202123")
    klient = _inbaddningsklient()
    with patch.object(embeddings, "get_embedding_client", return_value=klient):
        a = await embeddings.embed_text(f"Min order, personnummer {PNR}")
        b = await embeddings.embed_text(f"Min order, personnummer {annat[:6]}-{annat[6:]}")
    assert a == b
    assert klient.embeddings.create.await_count == 1


# -- Sökgrundningen -------------------------------------------------------------

#: Namnen Gemini-API:t godtar för sökverktyget (snake_case och camelCase, och
#: det äldre retrieval-verktyget).
_SOKVERKTYG = ("google_search", "googleSearch", "google_search_retrieval", "googleSearchRetrieval")

#: Den enda funktion som får konfigurera verktyget, och de enda som får anropa den.
_SOKFUNKTION = "_gemini_med_sokning"
_DISCOVERY = _APP / "leads" / "discovery.py"

#: Indata till funktionerna som bygger sökfrågan, namn för namn. Ett nytt
#: argument fäller testet: den som lägger till det ska pröva att det inte kan
#: bära kundmejl, och föra in det här.
_TILLATNA_INDATA = {
    "hitta_bolag": {"icp", "antal", "uteslut_namn", "profil", "ring", "listspar", "bortval", "bred"},
    "sla_upp_webbplats": {"company_name", "geografi"},
}

#: Moduler som bär kundmejl. Discovery får inte importera någon av dem.
_KUNDMEJLMODULER = ("email_pipeline", "inbox", "support_agent", "triage", "retention_classifier", "chatt")


def _funktioner(trad: ast.AST):
    for nod in ast.walk(trad):
        if isinstance(nod, (ast.FunctionDef, ast.AsyncFunctionDef)):
            yield nod


def _ar_sokverktyg(n: ast.AST) -> bool:
    return isinstance(n, ast.Constant) and isinstance(n.value, str) and n.value in _SOKVERKTYG


def _anropar_sokfunktionen(n: ast.AST) -> bool:
    if not isinstance(n, ast.Call):
        return False
    f = n.func
    return (isinstance(f, ast.Name) and f.id == _SOKFUNKTION) or (
        isinstance(f, ast.Attribute) and f.attr == _SOKFUNKTION
    )


def _antal(nod: ast.AST, pred) -> int:
    return sum(1 for n in ast.walk(nod) if pred(n))


def test_sokverktyget_konfigureras_bara_i_leadssokningen():
    fynd = []
    for fil in sorted(_APP.rglob("*.py")):
        trad = ast.parse(fil.read_text(encoding="utf-8"))
        totalt = _antal(trad, _ar_sokverktyg)
        if not totalt:
            continue
        tillatna = 0
        if fil == _DISCOVERY:
            tillatna = sum(_antal(f, _ar_sokverktyg) for f in _funktioner(trad) if f.name == _SOKFUNKTION)
        if totalt != tillatna:
            fynd.append(str(fil.relative_to(_APP)))
    assert not fynd, f"Googles sökverktyg konfigureras utanför discovery.{_SOKFUNKTION}: {fynd}"


def test_sokverktyget_finns_inte_i_webbdelen():
    """Email Studio och övriga Next-vägar skickar kundens utkast till Gemini."""
    fynd = []
    for katalog in ("lib", "app"):
        for fil in sorted((_REPO / katalog).rglob("*.ts*")):
            if "node_modules" in fil.parts:
                continue
            text = fil.read_text(encoding="utf-8", errors="ignore")
            fynd += [f"{fil.relative_to(_REPO)}: {namn}" for namn in _SOKVERKTYG if namn in text]
    assert not fynd, f"Googles sökverktyg i webbdelen: {fynd}"


def test_sokfunktionen_anropas_bara_fran_leadssokningen():
    fynd = []
    for fil in sorted(_APP.rglob("*.py")):
        trad = ast.parse(fil.read_text(encoding="utf-8"))
        totalt = _antal(trad, _anropar_sokfunktionen)
        if not totalt:
            continue
        tillatna = 0
        if fil == _DISCOVERY:
            tillatna = sum(
                _antal(f, _anropar_sokfunktionen) for f in _funktioner(trad) if f.name in _TILLATNA_INDATA
            )
        if totalt != tillatna:
            fynd.append(str(fil.relative_to(_APP)))
    assert not fynd, f"{_SOKFUNKTION} anropas utanför hitta_bolag och sla_upp_webbplats: {fynd}"


def test_sokfragans_indata_kan_inte_bara_kundmejl():
    trad = ast.parse(_DISCOVERY.read_text(encoding="utf-8"))
    for funk in _funktioner(trad):
        if funk.name not in _TILLATNA_INDATA:
            continue
        a = funk.args
        namn = {x.arg for x in (*a.posonlyargs, *a.args, *a.kwonlyargs)}
        if a.vararg or a.kwarg:
            namn.add("*")
        assert namn == _TILLATNA_INDATA[funk.name], (
            f"{funk.name} har fått nya indata ({namn - _TILLATNA_INDATA[funk.name]}). "
            f"Sökgrundningens frågor sparas hos Google i tre dygn: pröva att indata "
            f"aldrig kan bära kundmejl innan listan i testet ändras."
        )


def test_leadssokningen_importerar_inga_kundmejlmoduler():
    trad = ast.parse(_DISCOVERY.read_text(encoding="utf-8"))
    importer = []
    for nod in ast.walk(trad):
        if isinstance(nod, ast.ImportFrom) and nod.module:
            importer.append(nod.module)
        elif isinstance(nod, ast.Import):
            importer += [a.name for a in nod.names]
    fynd = [m for m in importer if any(del_ in m.split(".") for del_ in _KUNDMEJLMODULER)]
    assert not fynd, f"discovery.py importerar moduler som bär kundmejl: {fynd}"
