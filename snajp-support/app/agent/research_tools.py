"""Fas B: det enda stället i hela kodbasen som gör ett riktigt utgående
nätverksanrop till en prospekts webbplats — och det gör det inte direkt.
G4 ("utgående nätverk allowlistas per körning") uppfylls på två nivåer:

1. Infra/host: den ENDA externa tjänsten den här koden någonsin kontaktar
   är ScrapeGraphAI (via det officiella scrapegraph-py-SDK:t, host
   v2-api.scrapegraphai.com). Inget annat verktyg i leads-agenten gör ett
   rått HTTP-anrop till en godtycklig URL.
2. App/identitet: url-argumentet MÅSTE redan finnas registrerat som en
   prospect_sources-rad för DET HÄR prospektet (med källa, datum och
   laglig grund redan loggad — INV-DATA-001) INNAN skrapning. En modell
   kan alltså inte skrapa en URL en promptinjektion föreslagit i farten —
   bara URL:er vi medvetet registrerat i förväg.

Innehållet som kommer tillbaka är OPÅLITLIG text (G3) — wrappas alltid med
wrap_untrusted_content innan det lämnar den här modulen.
"""

import json

from agents import RunContextWrapper, function_tool

from ..config import get_settings
from ..leads.untrusted_content import wrap_untrusted_content
from .leads_context import ResearchContext
from .skatteverket_tools import SKATTEVERKET_TOOLS


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

    from scrapegraph_py import ScrapeGraphAI

    client = ScrapeGraphAI(api_key=settings.scrapegraphai_api_key)
    result = client.scrape(url)

    if result.status != "success":
        return json.dumps(
            {"error": f"Skrapning misslyckades: {result.error or 'okänt fel'}"}, ensure_ascii=False
        )

    markdown = _as_markdown((result.data.results or {}).get("markdown", {}).get("data", ""))
    if not markdown:
        return json.dumps({"error": "Skrapningen gav inget markdown-innehåll."}, ensure_ascii=False)

    research.scraped_sources.append({"url": url, "length": len(markdown)})
    wrapped = wrap_untrusted_content(markdown, source=url)
    return json.dumps({"content": wrapped}, ensure_ascii=False)


@function_tool
async def scrape_registered_source(ctx: RunContextWrapper[ResearchContext], url: str) -> str:
    """Hämtar innehållet från en REDAN REGISTRERAD källa för det här
    prospektet. Kan inte skrapa en godtycklig URL — bara en som redan
    finns i prospect_sources.

    Args:
        url: Käll-URL:en. Måste redan vara registrerad för prospektet.
    """
    return await _scrape_registered_source_impl(ctx.context, url)


# Uppslaget gäller tenantens eget bolag, aldrig prospektet som researchas.
RESEARCH_TOOLS = [scrape_registered_source, *SKATTEVERKET_TOOLS]
