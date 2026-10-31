"""Uppföljningarna bär kundens erbjudande, ämnesrader och stilgrind (Sebbe
2026-10-31), och Skapa om utkast skriver om ett leads väntande uppföljning.

Bakgrund: 418 väntande uppföljningar i main bar fortfarande "svara 'pilot'" och
"era fem vanligaste kundfrågor", 174 hade bolagets namn i ämnesraden och 116
slutade med en fråga, för kedjan läste bara de tidigare mejlen."""

from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest

from app.agent.step_runner import StepResult
from app.leads import erbjudanden
from app.leads.follow_up_generator import (
    generate_due_follow_ups,
    skriv_om_uppfoljning,
    uppfoljningstrad,
)
from app.storage.memory import MemoryStorage

TENANT = "00000000-0000-4000-a000-000000000001"
NU = datetime(2026, 10, 31, 12, 0, tzinfo=timezone.utc)
KONTEXT = "## Kontextpaket\nSnajp säljer AI-agenter för support och leads."

PRODUKTER = [
    {"namn": "Iris, leadsagenten", "nytta": "hittar nya företagskunder"},
    {"namn": "Supportagenten", "nytta": "svarar på återkommande kundfrågor dygnet runt"},
]
PILOT = (
    "Just nu tar vi in 20 företag i en kostnadsfri pilot av Supportagenten i tre månader. "
    "Du får upp till 50 % rabatt om du stannar efteråt. Handling: titta på demon på snajp.se/demo."
)
#: Båda raderna bär siffror: ämnesraden väljs efter faktagrinden, som
#: annars fällde "24/7" (fullsviten 2026-10-31).
AMNEN = ["Support 24/7 för dina kunder", "Svar till dina kunder, även klockan 03:00"]
BRA = (
    "Hej,\n\nOm ni hann se mitt förra mejl: vår Supportagent svarar på återkommande kundfrågor "
    "dygnet runt. Just nu tar vi in 20 företag i en kostnadsfri pilot, med 50 % rabatt om ni "
    "stannar efteråt.\n\nTitta gärna på demon på snajp.se/demo när det passar."
)


@pytest.fixture
def anyio_backend():
    return "asyncio"


async def _snajp(storage) -> None:
    await storage.set_agent_settings(
        TENANT,
        agent_type="leads",
        settings={
            "produkter": PRODUKTER,
            "erbjudanden": {
                "aktiva": [{"nyckel": "pilot", "vikt": 1}],
                "egna": {"pilot": {"namn": "Piloten", "form": "rak"}},
                "villkor": {"pilot": {"Supportagenten": PILOT, "Iris, leadsagenten": PILOT}},
                "amnen": {"Supportagenten": AMNEN},
            },
        },
    )


async def _kontaktad(storage, *, forsta: str = "Vår Supportagent svarar på kundfrågorna.", vantar: str | None = None):
    prospect = await storage.create_prospect(
        TENANT, company_name="Godhems Zoologiska AB", contact_email="info@godhems.se"
    )
    trad = await storage.ensure_outreach_thread(TENANT, prospect_id=prospect["id"])
    skickat = await storage.queue_outreach_message(
        TENANT, thread_id=trad["id"], body=forsta, subject="Frågorna om hemkörning",
        humanizer_variant="v", scheduled_at=NU - timedelta(days=9),
    )
    await storage.mark_outreach_message_sent(TENANT, skickat["message"]["id"], (NU - timedelta(days=9)).isoformat())
    await storage.update_send_queue_status(TENANT, skickat["queue_item"]["id"], status="sent", gate_checks={})
    gammal = None
    if vantar is not None:
        gammal = await storage.queue_outreach_message(
            TENANT, thread_id=trad["id"], body=vantar, subject="En tanke om era kundfrågor",
            humanizer_variant="v", scheduled_at=NU, status="awaiting_review",
        )
    return prospect, trad, gammal


def _fejk(svar: list[str], fall: list[dict]):
    """run_step som svarar med `svar` i tur och ordning (utkastet och varje
    omskrivning) och humaniserar utan ändring; `fall` samlar anropen."""
    kvar = list(svar)
    senast: dict = {}

    async def _run_step(step, ledger, trace, *, task, case_context, **kwargs):
        fall.append({"skill": step.skill, "task": task, "case": case_context})
        if step.skill == "sa:draft-outreach":
            senast.update(subject="Kort uppföljning om Godhems Zoologiska", body=kvar.pop(0) if len(kvar) > 1 else kvar[0])
            output = dict(senast)
        else:
            output = {"final_subject": senast["subject"], "final_body": senast["body"]}
        ledger.mark_skill_injected(step.skill)
        trace.steps.append(StepResult(
            skill=step.skill, output=output, attempts=1, escalated=False,
            escalation_reason=None, latency_ms=1, tokens_in=1, tokens_out=1,
        ))
        return output

    return _run_step


def test_produkten_hittas_pa_stammen_och_slaget():
    assert erbjudanden.produkt_nu(None, "Vår Supportagent svarar dygnet runt.", PRODUKTER)["namn"] == "Supportagenten"
    assert erbjudanden.produkt_nu(None, "hur vår AI-support skulle svara", PRODUKTER)["namn"] == "Supportagenten"
    assert erbjudanden.produkt_nu(None, "AI-agenten Iris hittar nya projekt", PRODUKTER)["namn"] == "Iris, leadsagenten"
    assert erbjudanden.produkt_nu(None, "Ett mejl om byggprojekt.", PRODUKTER) is None


@pytest.mark.anyio
async def test_uppfoljningen_bar_erbjudandet_amnet_ur_listan_och_villkoren():
    storage = MemoryStorage()
    await _snajp(storage)
    _, trad, _ = await _kontaktad(storage)
    fall: list[dict] = []
    with patch("app.leads.follow_up_generator.run_step", new=_fejk([BRA], fall)):
        [rad] = await generate_due_follow_ups(storage, TENANT, now=NU, tenant_name="Snajp", context_pack=KONTEXT)

    assert rad["queued"] is True, {k: rad.get(k) for k in ("stoppad", "status", "fel")}
    assert rad["produkt"] == "Supportagenten" and rad["erbjudande"] == "pilot"
    assert "## Erbjudandet i uppföljningen" in fall[0]["case"] and PILOT in fall[0]["case"]
    # Ämnesraden ur kundens lista, i ni-form ("Hej,"), aldrig modellens rad med bolagsnamnet.
    assert rad["subject"] in {erbjudanden.till_ni(a) for a in AMNEN}
    [koad] = [m for m in await storage.list_outreach_messages(TENANT, trad["id"]) if not m.get("sent_at")]
    assert "upp till 50 %" in koad["body"] and "20 företag" in koad["body"]


@pytest.mark.anyio
async def test_stilgrinden_skriver_om_en_uppfoljning_som_slutar_med_en_fraga():
    storage = MemoryStorage()
    await _snajp(storage)
    await _kontaktad(storage)
    fraga = BRA.replace("Titta gärna på demon på snajp.se/demo när det passar.", "Vill ni titta på demon på snajp.se/demo?")
    fall: list[dict] = []
    with patch("app.leads.follow_up_generator.run_step", new=_fejk([fraga, BRA], fall)):
        [rad] = await generate_due_follow_ups(storage, TENANT, now=NU, tenant_name="Snajp", context_pack=KONTEXT)

    omskrivningar = [f for f in fall if "FÄLLDES AV STILGRINDEN" in f["task"]]
    assert omskrivningar and "slutar med en fråga" in omskrivningar[0]["task"]
    assert rad["queued"] is True


@pytest.mark.anyio
async def test_skapa_om_ersatter_den_vantande_uppfoljningen():
    storage = MemoryStorage()
    await _snajp(storage)
    prospect, trad, gammal = await _kontaktad(storage, vantar="Svara 'pilot' så berättar jag mer.")
    tradrad = await uppfoljningstrad(storage, TENANT, prospect["id"])
    assert tradrad["outbound_sent_count"] == 1

    with patch("app.leads.follow_up_generator.run_step", new=_fejk([BRA], [])):
        rad = await skriv_om_uppfoljning(storage, TENANT, tradrad, tenant_name="Snajp", context_pack=KONTEXT)

    assert rad["queued"] is True and rad["sekvens"] == 1
    assert gammal["queue_item"]["status"] == "cancelled" and gammal["message"]["kasserad_at"]
    osanda = [m for m in await storage.list_outreach_messages(TENANT, trad["id"])
              if not m.get("sent_at") and not m.get("kasserad_at")]
    assert len(osanda) == 1 and "pilot" in osanda[0]["body"]


@pytest.mark.anyio
async def test_stoppad_ny_uppfoljning_lamnar_den_gamla_kvar():
    storage = MemoryStorage()
    await _snajp(storage)
    prospect, _, gammal = await _kontaktad(storage, vantar="Den gamla uppföljningen.")
    tradrad = await uppfoljningstrad(storage, TENANT, prospect["id"])

    with patch("app.leads.follow_up_generator.run_step", new=_fejk([BRA + " Våra kunder växer 300 %."], [])):
        rad = await skriv_om_uppfoljning(storage, TENANT, tradrad, tenant_name="Snajp", context_pack=KONTEXT)

    assert rad["queued"] is False and rad["stoppad"]["grounding"]
    assert gammal["queue_item"]["status"] == "awaiting_review" and not gammal["message"].get("kasserad_at")


@pytest.mark.anyio
async def test_lead_utan_skickat_mejl_har_ingen_uppfoljningstrad():
    storage = MemoryStorage()
    prospect = await storage.create_prospect(TENANT, company_name="Ny AB", contact_email="info@ny.se")
    assert await uppfoljningstrad(storage, TENANT, prospect["id"]) is None


@pytest.mark.anyio
async def test_svepet_hoppar_over_ett_lead_vars_utkast_skrivs_om():
    storage = MemoryStorage()
    await _snajp(storage)
    prospect, _, _ = await _kontaktad(storage)
    await storage.set_leads_job_status(TENANT, job_id="j-1", status="processing", scope="utkast", prospect_id=prospect["id"])
    fall: list[dict] = []
    with patch("app.leads.follow_up_generator.run_step", new=_fejk([BRA], fall)):
        assert await generate_due_follow_ups(storage, TENANT, now=NU, tenant_name="Snajp", context_pack=KONTEXT) == []
    assert fall == []


def test_grinden_undantar_produkten_efter_loftet_men_jamfor_med_kon():
    """Provet i development 2026-10-31: `agent_efter_loftet` fällde fem av sex
    uppföljningar som namngav produkten i första stycket, och alla sex började
    likadant utan att grinden såg det."""
    from app.leads.follow_up_generator import _stilfynd

    text = (
        "Hej,\n\nVår Supportagent svarar på frågorna om hemkörning dygnet runt.\n\n"
        "Just nu tar vi in 20 företag i en kostnadsfri pilot av Supportagenten, med upp till 50 % rabatt "
        "efteråt.\n\nTitta gärna på demon på snajp.se/demo när det passar."
    )
    utkast = {"subject": "Support 24/7 för era kunder", "body": text}
    fynd = _stilfynd(utkast, villkor=PILOT, produkt="Supportagenten", bolag="Godhems Zoologiska AB",
                     amne_i_kod=True, andra=[])
    assert not any("namnges först efter löftet" in f for f in fynd), fynd
    med_kon = _stilfynd(utkast, villkor=PILOT, produkt="Supportagenten", bolag="Godhems Zoologiska AB",
                        amne_i_kod=True, andra=[text])
    assert any("samma ingång" in f for f in med_kon), med_kon


@pytest.mark.anyio
async def test_iris_ar_aldrig_hon_i_uppfoljningen():
    storage = MemoryStorage()
    await _snajp(storage)
    _, trad, _ = await _kontaktad(storage, forsta="Vår agent Iris hittar nya företagskunder.")
    text = BRA.replace("vår Supportagent svarar på återkommande kundfrågor dygnet runt.",
                       "Iris hittar nya företagskunder. Hon skriver också första mejlet.").replace(
                       "pilot,", "pilot av Iris,")
    with patch("app.leads.follow_up_generator.run_step", new=_fejk([text], [])):
        [rad] = await generate_due_follow_ups(storage, TENANT, now=NU, tenant_name="Snajp", context_pack=KONTEXT)

    assert rad["produkt"] == "Iris, leadsagenten" and rad["queued"] is True, rad
    [koad] = [m for m in await storage.list_outreach_messages(TENANT, trad["id"]) if not m.get("sent_at")]
    assert "Hon skriver" not in koad["body"] and "Den skriver också" in koad["body"]
