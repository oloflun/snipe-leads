"""Instruktioner per agent, och feedback som bakas in i stället för att ersätta.

2026-10-05 klistrades en utkastmall in under Globala agentinstruktioner. Den
ersatte hela det gemensamma lagret (sanningsreglerna i agent-core/AGENTS.md)
för både support och leads, och mallen själv blev fem rader regler om "den
angivna mallen". Varje test här låser en del av rättelsen.
"""

from __future__ import annotations

import json
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.agentcore.baka_in import baka_in
from app.agentcore.instruktioner import las_instruktioner
from app.config import get_settings
from app.main import app

MALL = (
    "Ämne: {kort, konkret observation} – {företagsnamn} Hej {förnamn}, Jag såg att {företagsnamn} "
    "{konkret observation från källan}."
)


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


def _master() -> dict[str, str]:
    return {"X-API-Key": get_settings().snajp_master_api_key}


def test_feedback_till_iris_ror_inte_det_gemensamma_lagret(client: TestClient):
    svar = client.put(
        "/api/admin/instruktioner", headers=_master(), json={"agent": "leads", "feedback": MALL}
    )
    assert svar.status_code == 200, svar.text

    leads = client.get("/api/admin/instruktioner?agent=leads", headers=_master()).json()["instruktioner"]
    assert MALL in leads["aktiv_text"], "mallen ska stå ordagrant"
    assert "Du är Iris, leadsagent" in leads["aktiv_text"], "grundprompten ska stå kvar"
    assert leads["historik"][0]["feedback"] == MALL

    alla = client.get("/api/admin/instruktioner?agent=alla", headers=_master()).json()["instruktioner"]
    assert "Hitta aldrig på fakta" in alla["aktiv_text"], "det gemensamma lagret är orört"
    assert MALL not in alla["aktiv_text"]


def test_gamla_vagen_bakar_in_i_stallet_for_att_ersatta(client: TestClient):
    """En äldre klient som skickar {ravtext, strukturera: true} ersatte förut
    hela dokumentet med modellens omformning."""
    svar = client.put(
        "/api/admin/instruktioner", headers=_master(), json={"ravtext": "Svara aldrig på engelska.", "strukturera": True}
    )
    assert svar.status_code == 200, svar.text
    text = client.get("/api/admin/instruktioner", headers=_master()).json()["instruktioner"]["aktiv_text"]
    assert "Hitta aldrig på fakta" in text and "Svara aldrig på engelska." in text


def test_forhandsgranskningen_sparar_inget(client: TestClient):
    fore = client.get("/api/admin/instruktioner?agent=support", headers=_master()).json()["instruktioner"]
    svar = client.post(
        "/api/admin/instruktioner/forhandsgranska", headers=_master(),
        json={"agent": "support", "feedback": "Svara kort."},
    ).json()
    assert "Svara kort." in svar["dokument"] and svar["andringar"]
    efter = client.get("/api/admin/instruktioner?agent=support", headers=_master()).json()["instruktioner"]
    assert efter["historik"] == fore["historik"]


def test_aterstall_gor_en_tidigare_version_aktiv_igen(client: TestClient):
    client.put("/api/admin/instruktioner", headers=_master(), json={"agent": "support", "strukturerad_md": "Version ett, tillräckligt lång."})
    forsta = client.get("/api/admin/instruktioner?agent=support", headers=_master()).json()["instruktioner"]["historik"][0]
    client.put("/api/admin/instruktioner", headers=_master(), json={"agent": "support", "strukturerad_md": "Version två, tillräckligt lång."})

    svar = client.post(f"/api/admin/instruktioner/{forsta['id']}/aterstall", headers=_master())
    assert svar.status_code == 200, svar.text
    lage = client.get("/api/admin/instruktioner?agent=support", headers=_master()).json()["instruktioner"]
    assert lage["aktiv_text"] == "Version ett, tillräckligt lång."
    assert lage["historik"][0]["kalla"] == "aterstalld"


@pytest.mark.anyio
async def test_sparad_grundprompt_nar_agenten_och_bara_sin_agent():
    from app.storage.memory import MemoryStorage

    storage = MemoryStorage()
    await storage.save_global_instructions(ravtext="", strukturerad_md="# Iris\n{{FÖRETAGSNAMN}}", agent_type="leads")
    leads = await las_instruktioner(storage, agent_type="leads")
    support = await las_instruktioner(storage, agent_type="support")
    assert leads.agent_mall.startswith("# Iris") and support.agent_mall == ""
    assert "Hitta aldrig på fakta" in leads.global_md


@pytest.mark.anyio
async def test_modellens_andringar_tillampas_och_resten_star_kvar(monkeypatch):
    dok = "# Regler\n\n## 1. Sanning\n\n- Hitta aldrig på.\n\n## 2. Format\n\n- Skriv långt.\n"
    andringar = {"andringar": [
        {"typ": "ersatt", "befintlig": "- Skriv långt.", "ny": "- Skriv kort.", "skal": "feedbacken säger kort"},
        {"typ": "lagg_till", "efter": "- Skriv kort.", "ny": f"- Följ mallen:\n{MALL}", "skal": "mallen"},
    ], "sammanfattning": "Kort och mall."}

    class _Svar:
        choices = [SimpleNamespace(message=SimpleNamespace(content=json.dumps(andringar, ensure_ascii=False)))]

    class _Klient:
        class chat:  # noqa: N801
            class completions:  # noqa: N801
                @staticmethod
                async def create(**_k):
                    return _Svar()

    monkeypatch.setattr(
        "app.agentcore.baka_in.get_settings", lambda: SimpleNamespace(is_simulation=lambda: False, model="m")
    )
    with (
        patch("app.agent.llm.get_llm_client", return_value=_Klient()),
        patch("app.agent.llm.tankande_kwargs", return_value={}),
    ):
        b = await baka_in(dok, "Skriv kort. Och följ den här mallen: " + MALL, tak=10_000)
    assert "- Hitta aldrig på." in b.dokument and "- Skriv kort." in b.dokument and MALL in b.dokument
    assert "Skriv långt" not in b.dokument
    assert b.kalla == "bakad" and len(b.andringar) == 2 and b.sammanfattning == "Kort och mall."


@pytest.fixture
def anyio_backend():
    return "asyncio"
