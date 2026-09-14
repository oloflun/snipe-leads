"""Semantisk svarscache (Fas R2, bd snipe-cku) — INV-CACHE-001.

En cachad chattreplik är en REN funktion av (tenant, fråga, KB-version,
konfigversion) och ingenting annat. Den här modulen bär tre lager:

1. Lagringsprotokollet (`Svarscache`) med `MinnesSvarscache`/`RedisSvarscache`
   — husets paritetsmönster, samma som `app/cache/embeddingcache.py` och
   `app/jobs/store.py`.
2. Grinden (`lookup_behorig`) och förberedelsen (`forbered`) som
   `run_support_agent` anropar med sina redan-hämtade värden — de görs INTE
   i agentfilen, för att hålla den läsbar.
3. De två utfallen av en TRÄFF: `svara_fran_cache` (läge "on" — bygger hela
   svarsdicten och gör bokföringen) och `logga_skuggtraff` (läge "shadow" —
   rör ingenting, mäter bara).

## Behörighetsgrinden, och varför den är så snäv

En lookup är BARA tillåten vid ett rent förstakontakt: tom historik (första
meddelandet i samtalet — inget att personalisera svaret mot), inga bilagor
(vision-beskrivningen är per-bild, inte en del av frågetexten som embeddas),
tomt kundminne (finns sparade fakta hade svaret kunnat/bort ta hänsyn till
dem — en cachad replik kan inte det), och personnummermaskeringen ska vara
en NO-OP (`maskera_personnummer(text) == text` — texten innehöll aldrig ett
personnummer). Alla fyra måste hålla SAMTIDIGT, både vid lookup och vid
STORE efteråt — annars vore cachen en läcka: kundens egna uppgifter skulle
kunna forma en replik som sedan serveras till en helt annan kund.

## Vilka kategorier som får sparas, och varför just de

`CACHEBARA_KATEGORIER` är en delmängd av `config.CATEGORIES` — de kategorier
som är RENA faktafrågor, där svaret bara beror på vad som står i
kunskapsbasen och aldrig på vem som frågar:

  * `teknisk_support`, `garanti`, `leverans`, `utbildning` — policy- och
    how-to-svar grundade i KB-artiklar som är skrivna generiskt (se
    `app/kb_articles.py`). Två olika förstagångskunder som ställer samma
    fråga ska få samma svar.
  * `orderstatus` INGÅR, trots namnet. Agenten har INGEN
    orderuppslagsfunktion — den enda källan är KB (se `_sok_kb` i
    `support_agent.py`, "ENDA tillåtna faktakällan"), och de seedade
    orderstatus-artiklarna ("Vad orderstatusen betyder", "Ändra eller
    komplettera en lagd order") är generisk policytext, inte en riktig
    orderslagning. En fråga om ETT specifikt ordernummer kan agenten redan
    idag bara svara på med en följdfråga eller en eskalering — ingendera
    kategori-STORE:as (se `escalated`-villkoret nedan), så en cachad
    orderstatus-post kan strukturellt bara vara den generiska sortens svar.
  * `betalning` och `retur_reklamation` UTESLUTS ALLTID, uttryckligen
    (uppdraget nämner betalning/juridik/klagomål/reklamation/uppsägning/
    retention). `retur_reklamation` bär både "retur" och "reklamation" —
    en reklamation är per definition kundspecifik (den här varan, det här
    köpet) och hör aldrig hemma i en delad cache.
  * `ovrigt` UTESLUTS. Det är taxonomins slasktratt, inte en faktakategori
    — allt som inte passade någon annan kategori hamnar här, och just
    därför säger kategorin ingenting om VAD frågan faktiskt handlar om.
    Hellre missa en cachebar övrigt-fråga än cacha något som borde varit
    en annan, känsligare kategori som triagen råkade missklassificera.

Notera: `juridik`/`uppsägning`/`retention` finns inte som EGNA kategorier i
`config.CATEGORIES` — de fångas i stället av att `_ar_kansligt`/
`cancellation_risk` redan tvingar fram en eskalering i `support_agent.py`
(se `sakerhetskritiskt`), och STORE-villkoret nedan utesluter allt som
eskalerade. Samma skydd, en annan mekanism.
"""

from __future__ import annotations

from ..redisnycklar import nyckel

import hashlib
import logging
import math
import struct
import time
from dataclasses import dataclass, replace
from typing import Any, Protocol
from uuid import uuid4

from ..config import CATEGORIES, CATEGORY_LABELS
from ..moderation.maskering import maskera_personnummer

logger = logging.getLogger("snajp-support.cache.svarscache")

#: 21 dagar — kortare än embeddingcachens 30 (TTL_SEKUNDER i
#: embeddingcache.py): ett SVAR åldras fortare än en vektor. Produkter,
#: priser och rutiner hinner ändras på tre veckor på ett sätt en fråga-vektor
#: inte gör.
TTL_SEKUNDER = 21 * 24 * 60 * 60

#: cosine-AVSTÅND <= 0.1, alltså cosine-LIKHET >= 0.9. Samma tal, två sätt
#: att uttrycka det — Redis FT.SEARCH sorterar på avstånd (`avstand`),
#: MinnesSvarscache räknar likhet direkt. `LIKHET_TROSKEL` är likheten.
LIKHET_TROSKEL = 0.9

#: Se moduldocstringens avsnitt om kategorival.
CACHEBARA_KATEGORIER = frozenset(
    {"teknisk_support", "garanti", "leverans", "utbildning", "orderstatus"}
)
assert CACHEBARA_KATEGORIER <= set(CATEGORIES), (
    "CACHEBARA_KATEGORIER innehåller ett namn som inte finns i config.CATEGORIES "
    "— taxonomin har ändrats utan att den här listan följde med."
)
# Uttryckligen ALDRIG cachebara, skrivet ut så motiveringen inte tystnar om
# någon lägger till en kategori ovan utan att läsa docstringen.
_ALDRIG_CACHEBARA = frozenset(set(CATEGORIES) - CACHEBARA_KATEGORIER)
assert _ALDRIG_CACHEBARA >= {"betalning", "retur_reklamation"}, (
    "betalning/retur_reklamation måste alltid vara uteslutna (INV-CACHE-001)."
)


def normalisera_fraga(text: str) -> str:
    """Trim, lowercase, ihopklämda mellanslag — inget mer. Stemming gissar
    (se `_tokenize` i `app/storage/memory.py` för ett exempel på just den
    sortens gissning, som duger för fulltextsökning men INTE för en nyckel
    som avgör om två kunder får exakt samma svar)."""
    return " ".join((text or "").strip().lower().split())


def lookup_behorig(*, history: list, attachments: list, fakta: list, message: str) -> bool:
    """INV-CACHE-001s fyra villkor, SAMTIDIGT. Gäller både lookup och STORE
    — anroparen (`forbered` nedan) kör den en gång per körning och
    återanvänder svaret till båda."""
    return (
        not history
        and not attachments
        and not fakta
        and maskera_personnummer(message) == message
    )


@dataclass(frozen=True)
class CachePost:
    tenant: str
    kbv: str
    cfgv: str
    vektor: tuple[float, ...]
    fraga_norm: str
    svar: str
    kategori: str
    #: Bara satt av en LOOKUP-träff (cosine-likheten mot den aktuella
    #: frågan). 1.0 i övrigt — meningslöst innan en lookup gjorts.
    likhet: float = 1.0


class Svarscache(Protocol):
    async def lookup(
        self, *, tenant: str, kbv: str, cfgv: str, vektor: list[float]
    ) -> CachePost | None: ...

    async def store(self, post: CachePost) -> None: ...


def _cosine(a: tuple[float, ...], b: list[float]) -> float:
    if len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0.0 or nb == 0.0:
        return 0.0
    return dot / (na * nb)


class MinnesSvarscache:
    """Process-lokal lista, linjär cosine över tenant/kbv/cfgv-skopade
    poster. Antalet poster per tenant är litet (bara förstakontaktsfrågor
    med rena faktakategorier lagras alls), så en linjärsökning kostar
    ingenting — det är inte den här implementationen R5-planens skala
    handlar om."""

    def __init__(self) -> None:
        self._poster: list[CachePost] = []

    async def lookup(
        self, *, tenant: str, kbv: str, cfgv: str, vektor: list[float]
    ) -> CachePost | None:
        basta: CachePost | None = None
        basta_likhet = 0.0
        for post in self._poster:
            if post.tenant != tenant or post.kbv != kbv or post.cfgv != cfgv:
                continue
            likhet = _cosine(post.vektor, vektor)
            if likhet >= LIKHET_TROSKEL and likhet > basta_likhet:
                basta, basta_likhet = post, likhet
        if basta is None:
            return None
        return replace(basta, likhet=basta_likhet)

    async def store(self, post: CachePost) -> None:
        self._poster.append(post)


class RedisSvarscache:
    """RÅA `FT.*`-kommandon via redis-py — inte redisvl. Fem kommandon
    (FT.CREATE, FT.SEARCH, HSET, EXPIRE) är inte värda ett andra bibliotek
    för samma sak `app/jobs/store.py` redan gör med råa kommandon.

    `fakeredis` stödjer INTE `FT.*` (se testfilen) — den här klassen är
    därför byggd för att vara GRACEFUL mot ett fel: ett `FT.*`-anrop som
    kastar loggas EN gång och ger None/no-op, aldrig ett kastat undantag
    upp till anroparen. Paritetslogiken (vilken post som VINNER vid en
    träff) bevisas i `MinnesSvarscache`, som körs mot riktiga vektorer i
    varje testkörning. En liveverifiering mot en riktig Redis med
    Query Engine görs separat (se plans/2026-08-29-redis-agentarkitektur.md
    §7 punkt 5).
    """

    INDEX = "svarscache_idx"
    PREFIX = "svarscache:"

    def __init__(self, client: Any) -> None:
        # Namnrymden sätts per INSTANS och inte på klassen: klassattributen
        # ovan är den råa formen, och ett importtidsberoende till settings
        # hade gjort modulen omöjlig att importera innan miljön är läst.
        # BÅDA måste namnrymdas — ett delat FT-index gör posterna sökbara
        # över miljögränsen även när nyckelnamnen skiljer sig.
        self.INDEX = nyckel(self.INDEX)
        self.PREFIX = nyckel(self.PREFIX)
        self._redis = client
        self._loggat_fel = False
        self._index_sakerstalld = False

    async def _sakerstall_index(self) -> bool:
        """True om indexet finns (nyskapat eller redan där). False vid fel
        — anroparen ska då ge upp för DEN HÄR gången, inte försöka
        FT.SEARCH/HSET mot ett index som kanske inte finns."""
        if self._index_sakerstalld:
            return True
        try:
            await self._redis.execute_command(
                "FT.CREATE",
                self.INDEX,
                "ON",
                "HASH",
                "PREFIX",
                "1",
                self.PREFIX,
                "SCHEMA",
                "tenant",
                "TAG",
                "kbv",
                "TAG",
                "cfgv",
                "TAG",
                "kategori",
                "TAG",
                "vec",
                "VECTOR",
                "HNSW",
                "6",
                "TYPE",
                "FLOAT32",
                "DIM",
                "1536",
                "DISTANCE_METRIC",
                "COSINE",
            )
        except Exception as fel:  # noqa: BLE001 — idempotent: redan skapat är OK
            if "already exists" not in str(fel).lower():
                self._logga_fel(f"FT.CREATE ({fel})")
                return False
        self._index_sakerstalld = True
        return True

    @staticmethod
    def _tag(varde: str) -> str:
        """Escapar ett TAG-värde för FT.SEARCH-frågesyntaxen.

        RediSearch tolkar bindestreck, kolon m.fl. som frågesyntax även INUTI
        {}-klamrar — och varje riktigt tenant-id är ett UUID med bindestreck,
        så en oescapad fråga ger "Syntax error at offset ..." på PRECIS varje
        produktionsanrop. Hittat i liveverifieringen mot dev-databasen
        2026-08-29, INTE av testsviten: fakeredis kan inte köra FT.SEARCH,
        och graceful-fallbacken hade gömt felet som en evig tyst miss.
        """
        return "".join(ch if ch.isalnum() else f"\\{ch}" for ch in varde)

    async def lookup(
        self, *, tenant: str, kbv: str, cfgv: str, vektor: list[float]
    ) -> CachePost | None:
        if not await self._sakerstall_index():
            return None
        try:
            packad = struct.pack(f"{len(vektor)}f", *vektor)
            fraga = (
                f"(@tenant:{{{self._tag(tenant)}}} @kbv:{{{self._tag(kbv)}}} "
                f"@cfgv:{{{self._tag(cfgv)}}})"
                "=>[KNN 1 @vec $v AS avstand]"
            )
            svar = await self._redis.execute_command(
                "FT.SEARCH",
                self.INDEX,
                fraga,
                "PARAMS",
                "2",
                "v",
                packad,
                "SORTBY",
                "avstand",
                "RETURN",
                "3",
                "svar",
                "kategori",
                "avstand",
                "DIALECT",
                "2",
            )
        except Exception as fel:  # noqa: BLE001 — se klassdocstringen
            self._logga_fel(f"FT.SEARCH ({fel})")
            return None
        post = self._tolka_traff(svar, tenant=tenant, kbv=kbv, cfgv=cfgv)
        if post is None or post.likhet < LIKHET_TROSKEL:
            return None
        return post

    def _tolka_traff(
        self, raw: Any, *, tenant: str, kbv: str, cfgv: str
    ) -> CachePost | None:
        """`FT.SEARCH`-svaret är en platt lista: [antal, key1, [fält...], ...].
        Ingen riktig Redis har körts mot den här koden ännu (se
        klassdocstringen) — tolkningen är skriven mot den dokumenterade
        formen, inte verifierad live."""
        try:
            if not raw or raw[0] in (0, b"0"):
                return None
            falt = raw[2]
            data = {
                (falt[i].decode() if isinstance(falt[i], bytes) else falt[i]): falt[i + 1]
                for i in range(0, len(falt), 2)
            }
            svar_text = data.get("svar") or data.get(b"svar")
            kategori = data.get("kategori") or data.get(b"kategori")
            avstand = data.get("avstand") or data.get(b"avstand")
            if isinstance(svar_text, bytes):
                svar_text = svar_text.decode("utf-8")
            if isinstance(kategori, bytes):
                kategori = kategori.decode("utf-8")
            likhet = 1.0 - float(avstand)
            return CachePost(
                tenant=tenant,
                kbv=kbv,
                cfgv=cfgv,
                vektor=(),
                fraga_norm="",
                svar=svar_text or "",
                kategori=kategori or "ovrigt",
                likhet=likhet,
            )
        except Exception as fel:  # noqa: BLE001 — ett oväntat svarsformat är en miss, inte en krasch
            self._logga_fel(f"FT.SEARCH-tolkning ({fel})")
            return None

    async def store(self, post: CachePost) -> None:
        if not await self._sakerstall_index():
            return
        try:
            nyckel = f"{self.PREFIX}{uuid4()}"
            packad = struct.pack(f"{len(post.vektor)}f", *post.vektor)
            await self._redis.hset(
                nyckel,
                mapping={
                    "tenant": post.tenant,
                    "kbv": post.kbv,
                    "cfgv": post.cfgv,
                    "vec": packad,
                    "fraga_norm": post.fraga_norm,
                    "svar": post.svar,
                    "kategori": post.kategori,
                },
            )
            await self._redis.expire(nyckel, TTL_SEKUNDER)
        except Exception as fel:  # noqa: BLE001 — se klassdocstringen
            self._logga_fel(f"HSET/EXPIRE ({fel})")

    def _logga_fel(self, vad: str) -> None:
        if not self._loggat_fel:
            self._loggat_fel = True
            logger.warning(
                "Svarscache mot Redis (%s) misslyckades — fortsätter utan cache "
                "för resten av processen (samma mönster som embeddings.py).",
                vad,
            )


_cache: Svarscache = MinnesSvarscache()


def konfigurera(redis_client: Any | None = None) -> None:
    """Samma modul-nivå-mönster som embeddingcache. `None` => en FÄRSK
    `MinnesSvarscache`, inte bara "ingen Redis" — testerna behöver isolering
    mellan körningar."""
    global _cache
    _cache = RedisSvarscache(redis_client) if redis_client is not None else MinnesSvarscache()


def hamta_cache() -> Svarscache:
    return _cache


@dataclass(frozen=True)
class CacheKontext:
    """Resultatet av EN förberedelse per körning (`forbered` nedan) —
    `run_support_agent` sparar den i en lokal variabel och läser den både
    vid lookup-beslutet OCH vid STORE-beslutet i slutet, så grinden bara
    utvärderas en gång och vektorn bara räknas ut en gång."""

    behorig: bool
    fraga_norm: str = ""
    vektor: list[float] | None = None
    traff: CachePost | None = None


async def forbered(
    tenant_id: str,
    *,
    history: list,
    attachments: list,
    fakta: list,
    message: str,
    kbv: str,
    cfgv: str,
) -> CacheKontext:
    """Grind + embed + lookup, i EN funktion så anroparen inte kan glömma
    ett av stegen. Görs bara meningsfullt när `lookup_behorig` håller —
    annars kostar den inte ens ett embedding-anrop."""
    if not lookup_behorig(history=history, attachments=attachments, fakta=fakta, message=message):
        return CacheKontext(behorig=False)

    fraga_norm = normalisera_fraga(message)
    if not fraga_norm:
        return CacheKontext(behorig=False)

    # Sen import: undviker en cirkelimport vid modulladdning
    # (app.agent.embeddings importerar INTE den här modulen, men
    # app.agent.support_agent importerar BÅDA — en toppnivåimport här hade
    # inte varit farlig i sig, men den sena importen matchar mönstret övriga
    # anrop till embed_text redan använder i den här kodbasen, se
    # `_sok_kb` i support_agent.py).
    from ..agent.embeddings import embed_text

    vektor = await embed_text(fraga_norm)
    if vektor is None:
        # Inga embeddings tillgängliga just nu (ingen nyckel, eller ett
        # tidigare misslyckat anrop — se embeddings.embeddings_tillgangliga).
        # Varken lookup eller STORE är meningsfullt utan en vektor.
        return CacheKontext(behorig=False, fraga_norm=fraga_norm)

    traff = await hamta_cache().lookup(tenant=tenant_id, kbv=kbv, cfgv=cfgv, vektor=vektor)
    return CacheKontext(behorig=True, fraga_norm=fraga_norm, vektor=vektor, traff=traff)


async def spara(
    tenant_id: str,
    *,
    kbv: str,
    cfgv: str,
    vektor: list[float],
    fraga_norm: str,
    svar: str,
    kategori: str,
) -> None:
    """STORE. Anroparen (`run_support_agent`) har redan kontrollerat att
    `cache_kontext.behorig`, att svaret inte eskalerade och att kategorin är
    i `CACHEBARA_KATEGORIER` — den här funktionen litar på det och bara
    skriver."""
    await hamta_cache().store(
        CachePost(
            tenant=tenant_id,
            kbv=kbv,
            cfgv=cfgv,
            vektor=tuple(vektor),
            fraga_norm=fraga_norm,
            svar=svar,
            kategori=kategori,
        )
    )


async def logga_skuggtraff(storage: Any, tenant_id: str, *, kontext: CacheKontext) -> None:
    """Läge "shadow": ändrar INGENTING i svaret, skriver bara en
    platform_events-rad så träffkvoten går att granska innan "on" slås på
    (plan §7 punkt 3). Frågetexten och svaret loggas ALDRIG — bara ett
    hash-prefix och likhetsvärdet, samma sekretessnivå som resten av
    plattformshändelserna (se app/api/events.py)."""
    if kontext.traff is None:
        return
    # Sen import: events.py importerar inget härifrån, men modulen hålls fri
    # från api-lagret på toppnivå av samma skäl som embed_text ovan.
    from ..api.events import log_event

    await log_event(
        storage,
        level="info",
        source="cache:svarscache",
        message="Skuggträff i semantisk svarscache (SEMANTIC_CACHE=shadow).",
        tenant_id=tenant_id,
        detail={
            "fraga_sha256_prefix": hashlib.sha256(kontext.fraga_norm.encode("utf-8")).hexdigest()[:16],
            "likhet": round(kontext.traff.likhet, 4),
            "kategori": kontext.traff.kategori,
        },
    )


async def svara_fran_cache(
    storage: Any,
    tenant_id: str,
    *,
    traff: CachePost,
    message: str,
    subject: str,
    channel: str,
    customer: dict,
    max_length: int,
    pack: str,
    started: float,
    aterta: dict[str, str] | None,
    vid_arende: Any,
    is_test: bool = False,
) -> dict[str, Any]:
    """Läge "on", TRÄFF. Bygger exakt den svarsdict `run_support_agent`
    annars bygger i slutet av en full körning — men LLM-STEGEN (triage,
    research, utkast, eskaleringsbedömning, KB-förslag, retention,
    humanizer) körs aldrig. Bokföringen är OFÖRÄNDRAD: kunden ska se sin
    historik och tenanten sitt ärende oavsett om svaret kom från cachen
    eller från en full körning, så ärendet/inbound/outbound skapas med
    exakt samma anrop (`create_ticket`/`save_message`) i exakt samma form,
    inklusive `aterta`/`vid_arende` (INV-JOB-001 gäller lika mycket här).

    `sentiment` returneras som None och `log_metric` anropas INTE: att
    fabricera ett sentimentvärde för ett meddelande ingen läst hade
    förorenat sentimenttrenden med ett gissat tal snarare än att lämna en
    lucka — en lucka syns, ett gissat värde gör det inte.
    """
    reply = traff.svar
    if len(reply) > max_length:
        reply = reply[: max_length - 1].rstrip() + "…"

    if aterta:
        ticket = {"id": aterta["ticket_id"], "conversation_id": aterta["conversation_id"]}
    else:
        ticket = await storage.create_ticket(
            tenant_id,
            customer_id=customer["id"],
            subject=subject or message[:80],
            category=traff.kategori,
            channel=channel,
            priority="normal",
        )
        await storage.save_message(
            tenant_id,
            conversation_id=ticket["conversation_id"],
            direction="inbound",
            content=message,
            sentiment=None,
            has_image=False,
        )
    if vid_arende:
        await vid_arende(ticket["id"], ticket["conversation_id"])

    await storage.save_message(
        tenant_id,
        conversation_id=ticket["conversation_id"],
        direction="outbound",
        content=reply,
        sentiment=None,
        has_image=False,
    )

    # Nyckeln "step" (inte "skill") skiljer det här pseudosteget från ett
    # riktigt LLM-steg i step_log — chat.py._process räknar bara "skill"-
    # poster mot kvoten (se kommentaren vid rate_limit_db.record-anropet).
    step_log = [
        {
            "step": "svarscache",
            "traff": True,
            "likhet": round(traff.likhet, 4),
            "kbv": traff.kbv,
            "cfgv": traff.cfgv,
        }
    ]
    latency_ms = int((time.monotonic() - started) * 1000)
    run = await storage.log_agent_run(
        tenant_id,
        agent_type="support",
        pack_version=pack,
        skills_used=[],
        input_text=message,
        output_text=reply,
        step_log=step_log,
        tokens_in=0,
        tokens_out=0,
        latency_ms=latency_ms,
        is_test=is_test,
        # Migration 055: en cacheträff körde ingen modell alls — "svarscache"
        # i stället för ett provider:modell-par, så jämförelsen inte läser en
        # cachad rad som om den vore en riktig LLM-körning.
        model="svarscache",
    )

    return {
        "reply": reply,
        # Samma kontrakt som den fulla körningen (Fas 6.2): feedbacken
        # kopplas via run_id, och en cachad replik ska gå att tumma ned
        # precis som en modellskriven.
        "run_id": (run or {}).get("id"),
        "ticket_id": ticket["id"],
        "customer_id": customer["id"],
        "category": traff.kategori,
        "category_label": CATEGORY_LABELS.get(traff.kategori, "Övrigt"),
        "sentiment": None,
        "escalated": False,
        "escalation_reason": None,
        "kb_sources": [],
        "returning_customer": False,
        "simulation": False,
        "skills_used": [],
        "step_log": step_log,
        "cancellation_risk": False,
        "pack_version": pack,
    }
