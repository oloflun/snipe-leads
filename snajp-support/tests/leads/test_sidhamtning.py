"""Sidhämtningen (plan 2026-10-05, fas 2): cache per kund, gratis först,
kredittak per körning. Antons fynd 2026-10-04: 109 krediter på en dag."""

from __future__ import annotations

import pytest

from app.config import get_settings
from app.leads import sidhamtning
from app.storage.memory import MemoryStorage

TENANT = "00000000-0000-4000-a000-0000000051d0"
pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
def betalda(monkeypatch):
    """Fejkad ScrapeGraph och direkthämtning; räknar anropen."""
    monkeypatch.setenv("SCRAPEGRAPHAI_API_KEY", "sgai-test")
    get_settings.cache_clear()
    anrop: dict[str, list[str]] = {"sg": [], "direkt": []}
    direktsvar: dict[str, str | None] = {}

    async def sg(url):
        anrop["sg"].append(url)
        return f"# {url}\n" + "innehåll " * 20, None

    async def direkt(url):
        anrop["direkt"].append(url)
        text = direktsvar.get(url)
        return (text, None) if text else (None, "direkthämtning: HTTP 403")

    monkeypatch.setattr(sidhamtning, "_scrapegraph", sg)
    monkeypatch.setattr("app.agent.research_tools._hamta_direkt", direkt)
    yield anrop, direktsvar
    get_settings.cache_clear()


async def test_cachen_overlever_en_ny_korning(betalda):
    anrop, _ = betalda
    storage = MemoryStorage()
    sidhamtning.starta(storage, TENANT)
    url = "https://www.merinfo.se/foretag/Alfa-Bygg-AB-5560000001/2k"
    assert (await sidhamtning.hamta(url, fas="bolag", direkt=False))[2] == "scrapegraphai"
    # En ny körning (ny kontext, samma lager) betalar inte igen.
    ny = sidhamtning.starta(storage, TENANT)
    text, _fel, via = await sidhamtning.hamta(url, fas="bolag", direkt=False)
    assert via == "cache" and text and len(anrop["sg"]) == 1 and ny.cachetraffar == 1


async def test_egen_sajt_hamtas_gratis_forst_och_scrapegraph_bara_som_reserv(betalda, monkeypatch):
    monkeypatch.delenv("LEADS_DIREKTHAMTNING", raising=False)  # driftläget
    anrop, direktsvar = betalda
    kontext = sidhamtning.starta(MemoryStorage(), TENANT)
    direktsvar["https://alfabygg.se"] = "Alfa Bygg AB bygger hus i Mölndal sedan 1998. Ring oss."
    assert (await sidhamtning.hamta("https://alfabygg.se", fas="webb", direkt=True))[2] == "direkt"
    assert anrop["sg"] == [] and kontext.totalt == 0
    # JS-skal: direkthämtningen räknas som misslyckad och ScrapeGraph tar vid.
    direktsvar["https://spa.se"] = "Please enable JavaScript to run this app."
    assert (await sidhamtning.hamta("https://spa.se", fas="webb", direkt=True))[2] == "scrapegraphai"
    assert kontext.anrop == {"webb": 1}


async def test_kredittaket_stoppar_nya_betalda_anrop(betalda):
    anrop, _ = betalda
    kontext = sidhamtning.starta(MemoryStorage(), TENANT, tak=2)
    for i in range(4):
        await sidhamtning.hamta(f"https://www.merinfo.se/foretag/x-{i}", fas="bolag", direkt=False)
    assert len(anrop["sg"]) == 2 and kontext.slut
    text, fel, via = await sidhamtning.hamta("https://www.merinfo.se/foretag/y", fas="bolag", direkt=False)
    assert text is None and via == "tak" and "kredittaket" in fel


async def test_utan_kontext_inget_tak_och_ingen_cache(betalda):
    anrop, _ = betalda
    sidhamtning._KONTEXT.set(None)
    for _ in range(2):
        await sidhamtning.hamta("https://www.merinfo.se/foretag/z", fas="bolag", direkt=False)
    assert len(anrop["sg"]) == 2


def test_summan_i_liggaren():
    k = sidhamtning.Skrapkontext(anrop={"bolag": 3}, cachetraffar=2)
    assert sidhamtning.summera({"bolag": 1, "lista": 2}, k) == {"bolag": 4, "lista": 2, "cache": 2}
    assert sidhamtning.betalda({"bolag": 4, "lista": 2, "cache": 9}) == 6


async def test_registersida_ar_aldrig_hemsida():
    from app.agent.leads_agent import _gissa_hemsida

    merinfo = "https://www.merinfo.se/foretag/Alfa-Bygg-AB-5560000001/2k"
    assert _gissa_hemsida([merinfo], None) is None
    assert _gissa_hemsida([merinfo, "https://alfabygg.se/"], None) == "https://alfabygg.se/"
