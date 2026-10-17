"""Skapa om bara utkastet (scope 'utkast', 2026-10-17).

"Skapa om utkast" körde hela research_and_draft igen, och en ny research är en
ny bedömning: 23 av 104 leads föll till nivå C när Snajps utkast skrevs om
2026-10-16 (docs/UTKASTKEDJAN-REFERENS-2026-10-16.md, 8.5). Utkastet skrivs nu
ur leadets sparade research (app/leads/sparad_research.py). Testerna mäter att
researchen aldrig anropas, att underlaget kommer fram till utkaststeget och att
bedömningen står orörd.
"""
from __future__ import annotations

import json

import pytest

from app.api import leads as leads_api
from app.leads import sparad_research, utkaststatus
from app.storage.memory import MemoryStorage

pytestmark = pytest.mark.anyio

T = "t-utkast"
TENANT = {"tenant_id": T, "tenant_name": "Provbolaget"}
MATERIAL = (
    "## Källmaterial\nVi ger personlig rådgivning genom hela processen, från köp till underhåll.\n"
    "Öppet alla dagar."
)


@pytest.fixture
def anyio_backend():
    return "asyncio"


async def _lead(storage: MemoryStorage, **k) -> dict:
    p = await storage.create_prospect(
        T, company_name="Båtladan AB", contact_email="info@batladan.se", **k
    )
    await storage.spara_bedomning(
        T, p["id"],
        bedomning={
            "niva": "A", "qualified": True, "icp_fit": 0.9, "motivering": "Säljer båtar till privatpersoner.",
            "lagesbeskrivning": "Båthandel med verkstad.",
            "score_breakdown": [{"etikett": "Har kundtjänst", "utfall": "träff"}],
        },
    )
    return p


async def _research_korning(storage: MemoryStorage, prospect_id: str, *, med_post: bool) -> None:
    fynd = {
        "company_summary": "Båthandel i Gästrikland.",
        "evidence": ["personlig rådgivning genom hela processen", "ett citat som inte står på sidan"],
        "likely_pains": ["Många kundfrågor"],
        "trigger_events": [],
        "offer": {"name": "Supportagenten", "promise": "Svarar dygnet runt"},
        "produkt": "Supportagenten",
    }
    logg = [{"skill": "account-research", "raw_output": json.dumps(fynd), "user_message": MATERIAL}]
    if med_post:
        logg.append(
            sparad_research.underlagspost(
                {
                    "company_summary": "Ur posten.",
                    "citat": ["personlig rådgivning genom hela processen"],
                    "produkt": {"namn": "Supportagenten", "nytta": "Svarar på kundfrågor."},
                    "offer_summary": "Supportagenten · Svarar dygnet runt",
                    "research_evidence": ["personlig rådgivning genom hela processen"],
                    "qualified": False,
                }
            )
        )
    await storage.log_agent_run(
        T, agent_type="leads_research", pack_version="v", skills_used=["account-research"],
        input_text="", output_text="{}", step_log=logg, tokens_in=1, tokens_out=1, latency_ms=1,
        prospect_id=prospect_id,
    )


async def test_underlaget_las_ur_posten_och_bedomningen_ur_raden():
    storage = MemoryStorage()
    p = await _lead(storage)
    await _research_korning(storage, p["id"], med_post=True)
    u = await sparad_research.las(storage, T, p["id"])
    assert u["company_summary"] == "Ur posten."
    assert u["citat"] == ["personlig rådgivning genom hela processen"]
    # Postens qualified=False är körningens; raden bär den gällande bedömningen.
    assert u["qualified"] is True and u["lagesbeskrivning"] == "Båthandel med verkstad."


async def test_aldre_korning_utan_post_ger_bara_verifierade_citat():
    storage = MemoryStorage()
    p = await _lead(storage)
    await _research_korning(storage, p["id"], med_post=False)
    u = await sparad_research.las(storage, T, p["id"])
    assert u["citat"] == ["personlig rådgivning genom hela processen"]
    assert u["motivering"] == "Säljer båtar till privatpersoner."
    assert u["uppfyllda_kriterier"] == ["Har kundtjänst"]
    assert "Många kundfrågor" in u["research_evidence"]


async def test_utan_research_finns_inget_underlag():
    storage = MemoryStorage()
    p = await _lead(storage)
    assert await sparad_research.las(storage, T, p["id"]) is None


class _Jobb:
    def __init__(self):
        self.klart, self.fel = {}, {}

    async def start(self, job_id):
        pass

    async def complete(self, job_id, result):
        self.klart[job_id] = result

    async def fail(self, job_id, message):
        self.fel[job_id] = message


class _Tillstand:
    def __init__(self, storage, jobs):
        self.storage, self.jobs = storage, jobs


@pytest.fixture
def kedja(monkeypatch):
    sett: dict = {"research": 0, "utkast": []}

    async def falsk_context_pack(storage, tenant_id, *, overrides=None):
        return "KONTEXT", ()

    async def falsk_research(*a, **k):
        sett["research"] += 1
        return {"qualified": False, "disqualifiers": ["Ny research fällde bolaget"]}

    async def falskt_utkast(storage, tenant_id, **k):
        sett["utkast"].append(k)
        return {"subject": "Frågorna om underhåll", "queued": sett.get("koa", True),
                "escalation_reason": "Faktagrinden stoppade utkastet."}

    async def falsk_kontext(storage, tenant_id):
        return "Snajp säljer AI-agenter."

    monkeypatch.setattr(leads_api, "build_context_pack", falsk_context_pack)
    monkeypatch.setattr(leads_api, "_valj_leads_kedja", lambda: (falsk_research, falskt_utkast))
    monkeypatch.setattr("app.leads.business_context.require_business_context", falsk_kontext)
    monkeypatch.setattr("app.leads.discovery.mottagare", lambda p: p.get("contact_email"))
    return sett


async def test_bara_utkast_researchar_inte_och_bedomer_inte_om(kedja):
    storage = MemoryStorage()
    p = await _lead(storage)
    await _research_korning(storage, p["id"], med_post=True)
    jobb = _Jobb()
    await leads_api._run_batch_prospect(_Tillstand(storage, jobb), "job-u1", TENANT, prospect_id=p["id"], scope="utkast")
    assert not jobb.fel, jobb.fel
    assert kedja["research"] == 0
    assert len(kedja["utkast"]) == 1
    underlag = json.loads(kedja["utkast"][0]["research_summary"])
    assert underlag["citat"] == ["personlig rådgivning genom hela processen"]
    assert kedja["utkast"][0]["offer_summary"].startswith("Supportagenten: Svarar på kundfrågor.")
    rad = await storage.get_prospect(T, p["id"])
    assert rad["niva"] == "A" and rad["qualified"] is True
    assert (await storage.utkastjobb_lage(T))[p["id"]] == {"status": "completed", "error": None}


async def test_uteblivet_utkast_lamnar_skalet_i_liggaren(kedja):
    kedja["koa"] = False
    storage = MemoryStorage()
    p = await _lead(storage)
    await _research_korning(storage, p["id"], med_post=True)
    await leads_api._run_batch_prospect(_Tillstand(storage, _Jobb()), "job-u2", TENANT, prospect_id=p["id"], scope="utkast")
    lage = (await storage.utkastjobb_lage(T))[p["id"]]
    assert "Faktagrinden stoppade" in lage["error"]
    rad = utkaststatus.med_utkastjobb({"utkast_status": "avvisat", "utkast_skal": None}, lage)
    assert "Faktagrinden stoppade" in rad["utkast_skal"]


async def test_bolag_utan_sparad_research_far_hela_kedjan(kedja):
    storage = MemoryStorage()
    p = await _lead(storage)
    await leads_api._run_batch_prospect(_Tillstand(storage, _Jobb()), "job-u3", TENANT, prospect_id=p["id"], scope="utkast")
    assert kedja["research"] == 1


def test_pagaende_utkastjobb_visas_som_skrivs():
    ut = {"utkast_status": "vantar", "utkast_skal": None}
    assert utkaststatus.med_utkastjobb(ut, {"status": "processing", "error": None})["utkast_status"] == "skrivs"
    assert utkaststatus.med_utkastjobb(ut, None) == ut
    # Ett gammalt fel visas inte på ett lead som sedan fått ett utkast.
    assert utkaststatus.med_utkastjobb(ut, {"status": "completed", "error": "fel"}) == ut
