"""Snajps produktnamn i en annan kunds utkast stoppas i kod (kunddemon 2026-11-24).

En ny kund utan produktlista fick ett utkast som sålde Snajps egen
Supportagent: "Vår Supportagent svarar på de frågorna direkt på din webbplats"
är nästan ordagrant skrivstilens exempel (agent-core/prompts/leads-skrivstil.md).
Förbudet i grundprompten är en riktning; fyndet `snajp_produkt_hos_kund` är
garantin, och det stoppar köningen i stället för att skriva om.
"""

from app.leads import stilkontroll as stil

UTKAST = (
    "Hej,\n\nNi tar emot många frågor om leveranser varje vecka.\n\n"
    "Vår Supportagent svarar på de frågorna direkt på din webbplats, dygnet runt.\n\n"
    "Svara på mejlet så visar vi hur det fungerar."
)
KUNDENS = [{"namn": "Upphandling av företagstelefoni", "nytta": "lägre kostnad för telefoni"}]


def _koder(fynd):
    return [a.kod for a in fynd]


def test_snajps_produkt_hos_annan_kund_ger_fynd():
    fynd = stil.snajp_produkt_hos_kund(UTKAST, slug="testkund-ab12cd34", produkter=KUNDENS)
    assert _koder(fynd) == ["snajp_produkt_hos_kund"]
    assert fynd[0].allvarlig is True
    assert "supportagent" in fynd[0].beskrivning.casefold()


def test_samma_text_hos_snajp_ger_inget_fynd():
    assert stil.snajp_produkt_hos_kund(UTKAST, slug="snajp", produkter=[]) == []


def test_namnet_ar_kundens_egen_produkt():
    egna = [{"namn": "Supportagenten Pro", "nytta": "svarar på kundfrågor"}]
    assert stil.snajp_produkt_hos_kund(UTKAST, slug="kund-1234abcd", produkter=egna) == []


def test_iris_kvittohanteraren_och_snajp_fangas_ocksa():
    for namn in ("Iris", "Kvittohanteraren", "Snajp"):
        text = f"Hej,\n\nVår {namn} gör jobbet åt er.\n\nSvara på mejlet så berättar jag mer."
        fynd = stil.snajp_produkt_hos_kund(text, slug="kund-1234abcd", produkter=KUNDENS)
        assert _koder(fynd) == ["snajp_produkt_hos_kund"], namn


def test_mottagare_som_heter_iris_i_halsningen_ar_inget_fynd():
    """Iris är också ett förnamn: hälsningsraden är mottagaren, inte produkten."""
    text = "Hej Iris,\n\nNi växer i Umeå.\n\nVi sänker era telefonikostnader.\n\nSvara på mejlet."
    assert stil.snajp_produkt_hos_kund(text, slug="kund-1234abcd", produkter=KUNDENS) == []


def test_annan_kunds_text_utan_snajps_namn_ar_ren():
    text = "Hej,\n\nVi sänker era telefonikostnader genom en upphandling.\n\nSvara på mejlet."
    assert stil.snajp_produkt_hos_kund(text, slug="kund-1234abcd", produkter=KUNDENS) == []


_SNAJPMEJL = (
    "Hej,\n\nMed fri retur på allt ni säljer blir returfrågorna många.\n\n"
    "Vår Supportagent svarar på dem åt er.\n\nVill ni se hur räcker ett svar på mejlet."
)


async def _utkast_hos(slug: str):
    """Hela utkastkedjan med wiringtestets modellstubbe, där humanizerns
    slutliga text nämner Supportagenten."""
    from unittest.mock import patch

    from app.agent.leads_research_v2 import run_outreach_draft_v2
    from app.storage.memory import MemoryStorage
    from tests.agent.test_leads_v2_wiring import _FakeLLM

    storage = MemoryStorage()
    tenant = await storage.create_tenant(slug=slug, name="Telefonibolaget")
    await storage.save_context_doc(
        tenant["id"],
        kind="product_marketing",
        content=(
            "Vi säljer en svensk AI-supportagent till e-handlare. Den svarar på "
            "kundfrågor grundat i kundens egen kunskapsbas, eskalerar till människa "
            "när underlaget inte räcker, och skiljer sig från konkurrenterna genom "
            "att aldrig gissa. Supportagent. Erbjudande: pilot på returfrågor."
        ),
        source="test",
    )
    await storage.set_agent_settings(tenant["id"], agent_type="leads", settings={"produkter": KUNDENS})
    prospect = await storage.create_prospect(tenant["id"], company_name="Exempelbolaget")
    thread = await storage.ensure_outreach_thread(tenant["id"], prospect_id=prospect["id"])
    llm = _FakeLLM({"snajp:humanizer-svenska": {"final_subject": "Returfrågor", "final_body": _SNAJPMEJL}})
    with patch("app.agent.step_runner.get_llm_client", return_value=llm):
        result = await run_outreach_draft_v2(
            storage,
            tenant["id"],
            thread_id=thread["id"],
            prospect_email="kundservice@exempelbolaget.se",
            tenant_name="Telefonibolaget",
            company_name="Exempelbolaget",
            offer_summary="Supportagent · Färre repetitiva ärenden",
            context_pack="## Kontextpaket\nSupportagent för e-handel.",
            brief="",
            research_summary='{"company_summary": "Svensk e-handel."}',
            research_evidence=("Fri retur inom 30 dagar", "Många returfrågor"),
            is_test=True,
        )
    return result, await storage.list_review_queue(tenant["id"])


import pytest  # noqa: E402


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
def _deepseek(monkeypatch):
    from app.config import get_settings

    monkeypatch.setenv("LLM_PROVIDER", "deepseek")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key-not-a-real-credential-000000")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.mark.anyio
async def test_utkastet_koas_inte_hos_annan_kund(_deepseek):
    result, ko = await _utkast_hos("kund-ab12cd34")
    assert result["queued"] is False
    assert "Snajps egna namn" in (result["escalation_reason"] or "")
    assert ko == []


@pytest.mark.anyio
async def test_samma_utkast_koas_hos_snajp(_deepseek):
    result, ko = await _utkast_hos("snajp")
    assert result["queued"] is True, result["escalation_reason"]
    assert len(ko) == 1
