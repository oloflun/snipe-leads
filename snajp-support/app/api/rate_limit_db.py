"""Rate limiting som överlever en omstart — tre oberoende tak, räknade i
LLM-anrop.

Skiljer sig från `rate_limit.py` (som blir kvar för demons IP-tak, se nedan)
på den enda punkt som betyder något i drift: räknaren ligger i databasen, inte
i processminnet. Rendes free-tier spinner ner efter 15 minuter, och varje
uppvakning nollställde det gamla taket. Ett tak som nollställs vid inaktivitet
skyddar inte mot den enda trafik som faktiskt är farlig — den som kommer i
skov efter en tyst period.

Varför LLM-anrop och inte meddelanden: ett supportsvar är sex skill-steg, ett
research-steg åtta. Ett tak i meddelanden mäter alltså kostnaden med sex till
åtta gångers fel, och felet är olika stort för olika agenter.

Ordningen är kontrollera-först, bokför-efter. Kontrollen sker innan körningen
startar och bokföringen när den är klar, med det antal anrop den faktiskt
gjorde. Det betyder att en kund kan passera taket med som mest EN körning
(sex till åtta anrop) — priset för att slippa tråda en räknare genom varje
LLM-anropsplats i koden.

# ponytail: taket kan överskridas med en körning. Flytta kontrollen in i
# step_runner via en contextvar den dagen den precisionen är värd sitt pris.

Fail-open: går uppslaget inte att göra släpps anropet igenom och en varning
loggas. Att stoppa en betalande kunds support för att vår egen mätning
krånglar vore ett värre fel än att missa ett tak en timme.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

logger = logging.getLogger(__name__)

WINDOW = timedelta(hours=1)
LLM_CALL = "llm_call"

#: Taken. Vilket som helst som slår stoppar anropet.
#:
#: Tenant-taket är den bärande kostnadsspärren och ligger på TENANTEN, inte på
#: personen — annars blir kvoten en funktion av hur många kunden bjudit in, och
#: den kund som växer straffas för att den växer.
#:
#: Användartaket finns av ett annat skäl: det skyddar mot ett enskilt kapat
#: konto. Det är därför lägre än tenant-taket men inte en tredjedel av det —
#: en flitig människa ska aldrig träffa det.
TENANT_HOURLY_LLM_CALLS = 400
USER_HOURLY_LLM_CALLS = 120
#: Demo-workspace: ett lägre tak så provperioden inte kostar som ett fullt konto.
DEMO_USER_HOURLY_LLM_CALLS = 20

#: Demons IP-tak. Räknas i SVAR, inte i LLM-anrop — det är ett rent
#: kostnadstak och värdet (30/h) är oförändrat från den processlokala
#: versionen. Demon får ingen strypning av variationen; det är säljargumentet.
DEMO_RESPONSE = "demo_response"
DEMO_IP_HOURLY_RESPONSES = 30


class RateLimitDbExceededError(RuntimeError):
    """Ett tak nåddes. Bär vilket, så att anroparen kan skriva ett begripligt
    svenskt besked i stället för ett generiskt 429."""

    def __init__(self, scope_kind: str, used: int, cap: int) -> None:
        self.scope_kind = scope_kind
        self.used = used
        self.cap = cap
        super().__init__(
            f"Timtaket för {scope_kind} är nått ({used}/{cap} LLM-anrop senaste timmen)."
        )


@dataclass(frozen=True)
class Scope:
    scope_kind: str  # 'tenant' | 'user' | 'ip'
    id: str
    cap: int
    event_kind: str = LLM_CALL


def scopes_for(tenant_id: str | None, user_id: str | None, *, is_demo: bool = False) -> list[Scope]:
    """De tak som gäller för ett inloggat anrop. En saknad användare är inte
    ett fel — den anonyma demon har ingen, och den har sitt eget IP-tak."""
    scopes: list[Scope] = []
    if tenant_id:
        scopes.append(Scope("tenant", tenant_id, TENANT_HOURLY_LLM_CALLS))
    if user_id:
        cap = DEMO_USER_HOURLY_LLM_CALLS if is_demo else USER_HOURLY_LLM_CALLS
        scopes.append(Scope("user", user_id, cap))
    return scopes


def demo_ip_scope(ip: str) -> list[Scope]:
    return [Scope("ip", ip, DEMO_IP_HOURLY_RESPONSES, DEMO_RESPONSE)]


async def enforce(storage, scopes: list[Scope], *, now: datetime | None = None) -> None:
    """Kastar RateLimitDbExceededError om något tak redan är nått.

    Fail-open vid lagringsfel: en trasig mätning får inte bli ett avbrott."""
    if not scopes:
        return
    since = (now or datetime.now(timezone.utc)) - WINDOW
    for scope in scopes:
        try:
            used = await storage.count_rate_events(
                scope_kind=scope.scope_kind,
                scope_id=scope.id,
                kind=scope.event_kind,
                since=since,
            )
        except Exception as error:  # noqa: BLE001 — fail-open är avsiktligt
            logger.warning(
                "rate_limit_db: uppslaget för %s:%s misslyckades, släpper igenom (%s)",
                scope.scope_kind,
                scope.id,
                error,
            )
            return
        if used >= scope.cap:
            raise RateLimitDbExceededError(scope.scope_kind, used, scope.cap)


async def record(storage, scopes: list[Scope], llm_calls: int) -> None:
    """Bokför de LLM-anrop en avslutad körning faktiskt gjorde.

    Tyst vid fel av samma skäl som enforce() är fail-open — och för att den här
    anropas i en färdig-körning-väg där ett kastat undantag hade förvandlat ett
    lyckat svar till ett misslyckat jobb."""
    if llm_calls <= 0 or not scopes:
        return
    for scope in scopes:
        try:
            await storage.record_rate_events(
                scope_kind=scope.scope_kind,
                scope_id=scope.id,
                kind=scope.event_kind,
                count=llm_calls,
            )
        except Exception as error:  # noqa: BLE001
            logger.warning(
                "rate_limit_db: kunde inte bokföra %d anrop för %s:%s (%s)",
                llm_calls,
                scope.scope_kind,
                scope.id,
                error,
            )
