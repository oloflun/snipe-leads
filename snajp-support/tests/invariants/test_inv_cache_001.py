"""INV-CACHE-001 — en cachad chattreplik är en ren funktion av
(tenant, fråga, KB-version, konfigversion) och ingenting annat.

Kör `run_support_agent` genom det RIKTIGA kodvägen (förvillkorsgrind,
sidoeffekter, agent_runs-loggen) med mockad LLM-klient och mockad
embedding-klient — samma mönster som `tests/agent/test_kundminne.py` och
`tests/agent/test_support_agent_wiring.py`, plus en deterministisk
embeddingklient så den semantiska cachen har något att jämföra.

Cache-modulerna (embeddingcache/svarscache/versioner) testas ISOLERAT i
`tests/test_svarscache.py`. Den här filen bevisar bara att GRINDEN och
STORE:en är kopplade rätt till `run_support_agent` — i läge "on" (a),
grindens fyra villkor var för sig (b–e), versionsbump (f), och
kategorimängden (g) — plus att "shadow" mäter utan att servera.
"""

from __future__ import annotations

import hashlib
import json
import re
from unittest.mock import AsyncMock, patch

import pytest

from app.agent.support_agent import run_support_agent
from app.cache import embeddingcache, svarscache, versioner
from app.config import get_settings
from app.storage.memory import MemoryStorage

TENANT = "00000000-0000-4000-a000-000000000001"

EXPECTED_ORDER_NORMAL = [
    "cs:ticket-triage",
    "cs:customer-research",
    "cs:draft-response",
    "cs:customer-escalation",
    "snajp:humanizer-svenska",
]


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture(autouse=True)
def _miljo(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "deepseek")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key-not-a-real-credential-000000")
    get_settings.cache_clear()
    embeddingcache.konfigurera(None)
    svarscache.konfigurera(None)
    versioner.konfigurera(None)
    yield
    get_settings.cache_clear()
    embeddingcache.konfigurera(None)
    svarscache.konfigurera(None)
    versioner.konfigurera(None)


def _lage(monkeypatch, varde: str) -> None:
    monkeypatch.setenv("SEMANTIC_CACHE", varde)
    get_settings.cache_clear()


class _FakeLLM:
    """Samma mönster som test_kundminne.py/test_support_agent_wiring.py:
    ett kontraktsenligt JSON-svar per skill, utläst ur systempromptens
    markör. `self.calls` är facit för "gjorde den här körningen NÅGRA
    LLM-anrop alls?"."""

    def __init__(
        self,
        *,
        category: str = "teknisk_support",
        escalate: bool = False,
        should_escalate: bool = False,
        sentiment: float = 0.8,
        kb_supports_answer: bool = True,
        draft: str = "Svaret finns i kunskapsbasen.",
        final_reply: str | None = None,
        kundfakta: list[str] | None = None,
    ) -> None:
        self.calls: list[str] = []
        self.chat = self
        self.completions = self
        self._category = category
        self._escalate = escalate
        self._should_escalate = should_escalate
        self._sentiment = sentiment
        self._kb_supports_answer = kb_supports_answer
        self._draft = draft
        self._final_reply = final_reply if final_reply is not None else draft
        self._kundfakta = kundfakta or []

    async def create(self, *, model, response_format, temperature, messages, **kwargs):
        system = messages[0]["content"]
        skill = re.search(r"styrs av skillen (\S+?),", system).group(1)
        self.calls.append(skill)

        payload = {"sources_used": ["kb-1"], "context_refs": ["context_pack"]}
        payload.update(
            {
                "cs:ticket-triage": {
                    "category": self._category,
                    "priority": "P3",
                    "sentiment": self._sentiment,
                    "escalate": self._escalate,
                    "kundfakta": self._kundfakta,
                },
                "cs:customer-research": {
                    "findings": "KB täcker frågan.",
                    "confidence": 0.8,
                    "kb_supports_answer": self._kb_supports_answer,
                },
                "cs:draft-response": {"draft": self._draft},
                "cs:customer-escalation": {
                    "should_escalate": self._should_escalate,
                    "reason": "test" if self._should_escalate else None,
                },
                "snajp:humanizer-svenska": {"final_reply": self._final_reply},
            }.get(skill, {})
        )
        message = type("M", (), {"content": json.dumps(payload, ensure_ascii=False)})()
        usage = type("U", (), {"prompt_tokens": 10, "completion_tokens": 5})()
        return type("R", (), {"choices": [type("C", (), {"message": message})()], "usage": usage})()


class _DeterministiskEmbeddingKlient:
    """Samma text => samma vektor, alltid — annars vore "samma fråga två
    gånger" inte ett garanterat cosine=1.0-test. Olika text => en annan
    vektor (praktiskt taget ortogonal, sha256 är inte konstruerad för att
    klustra liknande text nära varandra, vilket räcker gott för att hålla
    sig UNDER 0.9-tröskeln i de här testerna)."""

    def __init__(self) -> None:
        self.calls = 0
        self.embeddings = self

    async def create(self, *, model, input, dimensions):
        self.calls += 1
        digest = hashlib.sha256(input.encode("utf-8")).digest()
        vektor = [b / 255.0 for b in digest[:16]]
        return type("R", (), {"data": [type("D", (), {"embedding": vektor})()]})()


async def _kor(
    storage,
    llm,
    *,
    message: str,
    customer_email: str,
    subject: str = "",
    channel: str = "web",
    customer_name: str = "Testkund",
    attachments: list[str] | None = None,
):
    embed_klient = _DeterministiskEmbeddingKlient()
    with (
        patch("app.agent.step_runner.get_llm_client", return_value=llm),
        patch(
            "app.agent.support_agent.classify_cancellation_risk",
            new=AsyncMock(return_value=(0.0, 0.0)),
        ),
        patch("app.agent.embeddings.get_embedding_client", return_value=embed_klient),
    ):
        return await run_support_agent(
            storage,
            TENANT,
            message=message,
            subject=subject,
            channel=channel,
            customer_email=customer_email,
            customer_name=customer_name,
            attachments=attachments or [],
        )


def _med_kontrollsiffra(nio: str) -> str:
    summa = 0
    for i, tecken in enumerate(nio):
        varde = int(tecken) * (2 if i % 2 == 0 else 1)
        summa += varde - 9 if varde > 9 else varde
    return nio + str((10 - summa % 10) % 10)


GILTIGT_PERSONNUMMER = _med_kontrollsiffra("850101123")


# --- (a) Träff i läge "on": noll LLM-anrop, identiskt svar, full bokföring -


@pytest.mark.anyio
async def test_a_cachetraff_on_ger_identiskt_svar_utan_llm_anrop_och_full_bokforing(monkeypatch):
    _lage(monkeypatch, "on")
    storage = MemoryStorage()
    fraga = "Hur lång är leveranstiden på en vanlig order?"

    llm1 = _FakeLLM(category="leverans", final_reply="2-4 vardagar med PostNord.")
    resultat1 = await _kor(storage, llm1, message=fraga, customer_email="kund1@example.com")
    assert llm1.calls == EXPECTED_ORDER_NORMAL, "Första körningen (cachen tom) ska köra HELA kedjan."
    assert resultat1["reply"] == "2-4 vardagar med PostNord."

    llm2 = _FakeLLM(category="leverans", final_reply="ETT HELT ANNAT SVAR — får aldrig synas.")
    resultat2 = await _kor(storage, llm2, message=fraga, customer_email="kund2@example.com")

    assert llm2.calls == [], "Andra körningen (cacheträff, läge on) gjorde ett LLM-anrop den inte skulle."
    assert resultat2["reply"] == resultat1["reply"], "Cacheträffen svarade inte med den lagrade texten."
    assert resultat2["ticket_id"] != resultat1["ticket_id"], "Varje kontakt ska få sitt EGET ärende."

    for resultat in (resultat1, resultat2):
        ticket = await storage.get_ticket(TENANT, resultat["ticket_id"])
        assert ticket is not None, "Ärendet saknas — bokföringen hoppades över."
        riktningar = [m["direction"] for m in ticket["messages"]]
        assert riktningar == ["inbound", "outbound"], (
            f"Förväntade exakt ett inbound- och ett outbound-meddelande, fick {riktningar}."
        )
        assert ticket["messages"][1]["content"] == resultat1["reply"]

    # step_log för cacheträffen är ett PSEUDO-steg (nyckeln "step", inte
    # "skill") — se svara_fran_cache och rate-limit-kommentaren i chat.py.
    assert resultat2["step_log"][0]["step"] == "svarscache"
    assert resultat2["step_log"][0]["traff"] is True

    # Migration 055: cacheträffen körde ingen modell alls och ska INTE se ut
    # som en LLM-körning i agent_runs — "svarscache", inte provider:modell.
    # Den fulla första körningen ska däremot bära den riktiga providern.
    run1 = await storage.get_agent_run(resultat1["run_id"])
    run2 = await storage.get_agent_run(resultat2["run_id"])
    assert run1["model"] == "deepseek:deepseek-v4-flash"
    assert run2["model"] == "svarscache"


# --- (b) Personnummer i meddelandet => aldrig lookup/store ------------------


@pytest.mark.anyio
async def test_b_personnummer_blockerar_lookup_och_store(monkeypatch):
    _lage(monkeypatch, "on")
    storage = MemoryStorage()
    fraga = f"Mitt personnummer är {GILTIGT_PERSONNUMMER[:6]}-{GILTIGT_PERSONNUMMER[6:]}, hjälp mig."

    llm = _FakeLLM(category="teknisk_support")
    await _kor(storage, llm, message=fraga, customer_email="pnr@example.com")

    assert llm.calls == EXPECTED_ORDER_NORMAL, "PII i meddelandet ska INTE hoppa över LLM-kedjan."
    cache = svarscache.hamta_cache()
    assert isinstance(cache, svarscache.MinnesSvarscache)
    assert cache._poster == [], "Ett meddelande med personnummer fick INTE lagras i svarscachen."


# --- (c) Kund med minnesfakta => aldrig lookup/store -------------------------


@pytest.mark.anyio
async def test_c_kundminne_blockerar_lookup_och_store(monkeypatch):
    _lage(monkeypatch, "on")
    storage = MemoryStorage()

    kund = await storage.find_or_create_customer(
        TENANT, email="minne@example.com", phone=None, name="Minnes Kund"
    )
    # Fakta sparas UTAN att skapa ett ärende — historiken ska vara tom, bara
    # minnesvillkoret ska fälla.
    await storage.add_customer_facts(TENANT, kund["id"], fakta=["Har en Android-telefon"])

    llm = _FakeLLM(category="teknisk_support")
    await _kor(storage, llm, message="Var hittar jag användarmanualen?", customer_email="minne@example.com")

    assert llm.calls == EXPECTED_ORDER_NORMAL
    cache = svarscache.hamta_cache()
    assert cache._poster == [], "En kund med sparade minnesfakta fick INTE lagras i svarscachen."


# --- (d) Pågående samtal (befintlig historik) => aldrig lookup/store --------


@pytest.mark.anyio
async def test_d_befintlig_historik_blockerar_lookup_och_store(monkeypatch):
    _lage(monkeypatch, "on")
    storage = MemoryStorage()
    fraga = "Vad ingår i garantin?"

    llm1 = _FakeLLM(category="garanti")
    await _kor(storage, llm1, message=fraga, customer_email="samma@example.com")
    cache = svarscache.hamta_cache()
    antal_efter_forsta = len(cache._poster)
    assert antal_efter_forsta == 1, "Första kontakten (tom historik) skulle lagrats."

    # Andra meddelandet från SAMMA kund — historiken är nu inte längre tom.
    llm2 = _FakeLLM(category="garanti")
    await _kor(storage, llm2, message=fraga, customer_email="samma@example.com")

    assert llm2.calls == EXPECTED_ORDER_NORMAL, (
        "En kund med befintlig historik ska INTE få en cacheträff — hela kedjan "
        "skulle ha körts."
    )
    assert len(cache._poster) == antal_efter_forsta, (
        "En andra kontakt med befintlig historik fick INTE lagra ännu en post."
    )


# --- (e) Svar som eskalerade => aldrig store --------------------------------


@pytest.mark.anyio
async def test_e_eskalerat_svar_lagras_aldrig(monkeypatch):
    _lage(monkeypatch, "on")
    storage = MemoryStorage()

    llm = _FakeLLM(category="teknisk_support", should_escalate=True)
    resultat = await _kor(
        storage, llm, message="Kan jag få hjälp med detta?", customer_email="eskalerad@example.com"
    )

    assert resultat["escalated"] is True
    cache = svarscache.hamta_cache()
    assert cache._poster == [], "Ett eskalerat svar fick INTE lagras i svarscachen."


# --- (f) KB-versionsbump mellan två körningar => miss -----------------------


@pytest.mark.anyio
async def test_f_kb_version_bump_ger_miss(monkeypatch):
    _lage(monkeypatch, "on")
    storage = MemoryStorage()
    fraga = "Hur uppdaterar jag firmware på enheten?"

    llm1 = _FakeLLM(category="teknisk_support")
    await _kor(storage, llm1, message=fraga, customer_email="fore-bump@example.com")
    assert llm1.calls == EXPECTED_ORDER_NORMAL

    await versioner.bumpa_kb(TENANT)

    llm2 = _FakeLLM(category="teknisk_support")
    await _kor(storage, llm2, message=fraga, customer_email="efter-bump@example.com")
    assert llm2.calls == EXPECTED_ORDER_NORMAL, (
        "Efter en KB-versionsbump ska den gamla posten vara omatchbar — miss, inte träff."
    )


# --- (g) Icke-cachebar kategori (betalning) => aldrig store -----------------


@pytest.mark.anyio
async def test_g_icke_cachebar_kategori_lagras_aldrig(monkeypatch):
    _lage(monkeypatch, "on")
    storage = MemoryStorage()

    llm = _FakeLLM(category="betalning")
    resultat = await _kor(
        storage, llm, message="Kan jag betala med faktura?", customer_email="betalning@example.com"
    )

    assert resultat["escalated"] is False, "Testet ska isolera kategorivillkoret, inte eskalering."
    cache = svarscache.hamta_cache()
    assert cache._poster == [], "Kategorin 'betalning' ska ALDRIG lagras (INV-CACHE-001)."


# --- Shadow: mäter utan att servera -----------------------------------------


@pytest.mark.anyio
async def test_shadow_traff_andrar_inte_svaret_men_skriver_eventraden(monkeypatch):
    _lage(monkeypatch, "shadow")
    storage = MemoryStorage()
    fraga = "Vad ingår i utbildningen?"

    llm1 = _FakeLLM(category="utbildning", final_reply="Tre filmer plus ett livepass.")
    resultat1 = await _kor(storage, llm1, message=fraga, customer_email="shadow1@example.com")
    assert llm1.calls == EXPECTED_ORDER_NORMAL
    assert resultat1["reply"] == "Tre filmer plus ett livepass."

    handelser_fore = await storage.list_platform_events(tenant_id=TENANT)
    skugghandelser_fore = [e for e in handelser_fore if e["source"] == "cache:svarscache"]
    assert skugghandelser_fore == [], "Ingen skuggträff ska loggas på en MISS (cachen var tom)."

    llm2 = _FakeLLM(category="utbildning", final_reply="Ett annat svar den här gången.")
    resultat2 = await _kor(storage, llm2, message=fraga, customer_email="shadow2@example.com")

    # Shadow rör INGENTING i flödet: hela kedjan kör, och svaret kommer från
    # den HÄR körningens egen humanizer — inte från cachen.
    assert llm2.calls == EXPECTED_ORDER_NORMAL, "Shadow-läge ska aldrig hoppa över LLM-kedjan."
    assert resultat2["reply"] == "Ett annat svar den här gången."
    assert resultat2["reply"] != resultat1["reply"]

    handelser_efter = await storage.list_platform_events(tenant_id=TENANT)
    skugghandelser_efter = [e for e in handelser_efter if e["source"] == "cache:svarscache"]
    assert len(skugghandelser_efter) == 1, "Skuggträffen skulle loggat exakt en platform_events-rad."
    detalj = skugghandelser_efter[0]["detail"]
    assert detalj["likhet"] >= svarscache.LIKHET_TROSKEL
    assert "fraga_sha256_prefix" in detalj
    # Frågetexten och svaret får ALDRIG stå i klartext i en plattformshändelse.
    assert fraga not in json.dumps(skugghandelser_efter[0], ensure_ascii=False)
