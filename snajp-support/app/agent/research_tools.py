"""Fas B: det enda stället i hela kodbasen som gör ett riktigt utgående
nätverksanrop till en prospekts webbplats — och det gör det inte direkt.
G4 ("utgående nätverk allowlistas per körning") uppfylls på två nivåer:

1. Infra/host: förstahandsvägen är ScrapeGraphAI (via det officiella
   scrapegraph-py-SDK:t, host v2-api.scrapegraphai.com). Fallerar den hämtas
   SAMMA registrerade URL direkt (sedan 2026-09-15, se `_hamta_direkt`) -
   aldrig en annan, och en omdirigering till en annan domän godtas inte.
   Inget verktyg i leads-agenten gör ett rått HTTP-anrop till en godtycklig
   URL.
2. App/identitet: url-argumentet MÅSTE redan finnas registrerat som en
   prospect_sources-rad för DET HÄR prospektet (med källa, datum och
   laglig grund redan loggad — INV-DATA-001) INNAN skrapning. En modell
   kan alltså inte skrapa en URL en promptinjektion föreslagit i farten —
   bara URL:er vi medvetet registrerat i förväg.

Innehållet som kommer tillbaka är OPÅLITLIG text (G3) — wrappas alltid med
wrap_untrusted_content innan det lämnar den här modulen.
"""

import asyncio
import json
import logging
from urllib.parse import urlparse

import httpx
from agents import RunContextWrapper, function_tool

from ..config import get_settings
from ..leads.platshallare import html_till_text, platshallarskal
from ..leads.untrusted_content import wrap_untrusted_content
from .leads_context import ResearchContext

logger = logging.getLogger("snajp-support.research-tools")

#: Taket för ScrapeGraphAI innan reservhämtningen tar vid. SDK:ts eget
#: httpx-tak är 120 s. Uppmätt 2026-09-15: itkonsulterna.se gav "HTTP 502"
#: efter 54 s medan sidan svarade på 0,3 s direkt; lyckade skrapningar tog
#: upp till ~50 s, därför inte lägre.
SGAI_TAK_SEKUNDER = 60.0

_DIREKT_TIMEOUT = httpx.Timeout(10.0, connect=5.0)
_DIREKT_MAX_TECKEN = 500_000
_DIREKT_HEADERS = {
    "user-agent": "Mozilla/5.0 (compatible; snajp-leads/1.0; +https://snajp.se)",
    "accept": "text/html,application/xhtml+xml",
    "accept-language": "sv-SE,sv;q=0.9,en;q=0.5",
}


def _as_markdown(data: object) -> str:
    """ScrapeGraphAI returnerar results['markdown']['data'] som en LISTA av
    sidsegment, inte som en sträng — trots att fältet heter 'data'.

    Att inte hantera det gav två tysta fel samtidigt (hittade 2026-08-08 i
    en live-körning, inte av testerna, eftersom testmocken modellerade
    fältet som en sträng): `len(markdown)` blev 1 i stället för ~4000, så
    scraped_sources rapporterade "1 tecken hämtat", OCH innehållet
    injicerades i prompten som en Python-listrepr med LITERALA '\\n' i
    stället för riktiga radbrytningar. Modellen fick alltså sidan som en
    enda oformaterad rad.
    """
    if isinstance(data, (list, tuple)):
        return "\n\n".join(str(part) for part in data if part)
    return str(data or "")


async def _scrape_registered_source_impl(research: ResearchContext, url: str) -> str:
    registered = await research.storage.list_prospect_source_urls(
        research.tenant_id, research.prospect_id
    )
    if url not in registered:
        return json.dumps(
            {
                "error": (
                    f"'{url}' är inte registrerad som källa för det här prospektet. "
                    "Registrera källan (med datum och laglig grund) innan skrapning — "
                    "en URL som bara föreslås i samtalet kan inte skrapas."
                )
            },
            ensure_ascii=False,
        )

    settings = get_settings()
    if not settings.scrapegraphai_api_key:
        return json.dumps(
            {"error": "SCRAPEGRAPHAI_API_KEY saknas — research-skrapning är inte konfigurerad."}
        )

    markdown, sgai_fel = await _hamta_via_scrapegraph(settings.scrapegraphai_api_key, url)
    via = "scrapegraphai"
    if markdown is None:
        markdown, direkt_fel = await _hamta_direkt(url)
        via = "direkt"
        if markdown is None:
            return json.dumps(
                {"error": f"{sgai_fel} Reservhämtningen gav inget heller: {direkt_fel}."},
                ensure_ascii=False,
            )
        logger.info("ScrapeGraphAI fallerade för %s (%s) — direkthämtningen tog vid.", url, sgai_fel)

    platshallare = platshallarskal(markdown)
    post: dict = {"url": url, "length": len(markdown), "via": via}
    if platshallare:
        post["platshallare"] = platshallare
    research.scraped_sources.append(post)
    wrapped = wrap_untrusted_content(markdown, source=url)
    if platshallare:
        # Utanför wrappern med flit: det här är vår iakttagelse, inte sidans
        # text, och ska läsas som fakta om källan.
        wrapped = (
            f"KODNOTERING (inte från sidan): webbplatsen är en platshållare — "
            f"{platshallare}. Den innehåller ingen information om bolaget.\n\n{wrapped}"
        )
    return json.dumps({"content": wrapped}, ensure_ascii=False)


async def _hamta_via_scrapegraph(api_key: str, url: str) -> tuple[str | None, str | None]:
    """(markdown, fel). Det synkrona SDK:t körs i en tråd: `client.scrape` är
    ett blockerande nätverksanrop, och direkt i en async-funktion stod hela
    api-processens händelseloop still medan det pågick - 54 s för
    itkonsulterna.se 2026-09-15, med kundchatten i samma process."""
    from scrapegraph_py import ScrapeGraphAI

    try:
        client = ScrapeGraphAI(api_key=api_key)
        result = await asyncio.wait_for(
            asyncio.to_thread(client.scrape, url), timeout=SGAI_TAK_SEKUNDER
        )
    except asyncio.TimeoutError:
        return None, f"ScrapeGraphAI svarade inte inom {int(SGAI_TAK_SEKUNDER)} s."
    except Exception as fel:  # noqa: BLE001 — tjänstefel ska ge reservhämtning, inte krasch
        return None, f"ScrapeGraphAI: {type(fel).__name__}: {fel}."

    if result.status != "success":
        return None, f"Skrapning misslyckades: {result.error or 'okänt fel'}."
    markdown = _as_markdown((result.data.results or {}).get("markdown", {}).get("data", ""))
    if not markdown:
        return None, "Skrapningen gav inget markdown-innehåll."
    return markdown, None


def _samma_varddator(a: str, b: str) -> bool:
    def vard(url: str) -> str:
        host = urlparse(url).netloc.lower()
        return host[4:] if host.startswith("www.") else host

    return vard(a) == vard(b)


async def _hamta_direkt(url: str) -> tuple[str | None, str | None]:
    """Reservhämtning av SAMMA registrerade URL när ScrapeGraphAI fallerar.

    Allowlisten är redan passerad i anroparen. En omdirigering till en annan
    domän godtas inte - då hade vi läst en sida som aldrig registrerats
    (edza.se pekar t.ex. på en studentsida på uu.se).
    """
    try:
        async with httpx.AsyncClient(
            timeout=_DIREKT_TIMEOUT, follow_redirects=True, headers=_DIREKT_HEADERS
        ) as client:
            svar = await client.get(url)
    except httpx.HTTPError as fel:
        return None, f"direkthämtning: {type(fel).__name__}"
    if not _samma_varddator(url, str(svar.url)):
        return None, "direkthämtning: omdirigerades till en annan domän"
    if svar.status_code >= 400:
        return None, f"direkthämtning: HTTP {svar.status_code}"
    typ = (svar.headers.get("content-type") or "").lower()
    if typ and "html" not in typ and not typ.startswith("text/"):
        return None, f"direkthämtning: inte en webbsida ({typ.split(';')[0]})"
    text = html_till_text(svar.text[:_DIREKT_MAX_TECKEN])
    if not text:
        return None, "direkthämtning: sidan var tom"
    return text, None


@function_tool
async def scrape_registered_source(ctx: RunContextWrapper[ResearchContext], url: str) -> str:
    """Hämtar innehållet från en REDAN REGISTRERAD källa för det här
    prospektet. Kan inte skrapa en godtycklig URL — bara en som redan
    finns i prospect_sources.

    Args:
        url: Käll-URL:en. Måste redan vara registrerad för prospektet.
    """
    return await _scrape_registered_source_impl(ctx.context, url)


RESEARCH_TOOLS = [scrape_registered_source]
