"""Kundens egen feedback till sin agent: förhandsgranska, spara, återställ, tak (fas 8)."""

from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from app.agentcore.baka_in import Bakning
from app.config import get_settings
from app.leads import onskemal
from app.main import app

DEMO = {"X-API-Key": get_settings().snajp_demo_api_key}


def _bakning(dokument: str) -> Bakning:
    return Bakning(dokument=dokument, andringar=[{"typ": "lagg_till", "ny": dokument, "skal": "kundens önskan"}],
                   ej_tillampade=[], kalla="bakad", sammanfattning="", anmarkning="", borttaget_tecken=0,
                   varning="")


def test_forhandsgranska_sparar_inget_och_spara_aterstall_ger_historik():
    with TestClient(app) as client, patch(
        "app.api.leads.baka_in", new=AsyncMock(return_value=_bakning("Skriv kortare mejl."))
    ):
        prov = client.post("/api/agent/onskemal/leads/forhandsgranska", headers=DEMO,
                           json={"feedback": "Kortare mejl tack"})
        assert prov.status_code == 200 and prov.json()["dokument"] == "Skriv kortare mejl."
        fore = client.get("/api/agent/onskemal/leads", headers=DEMO).json()

        sparad = client.put("/api/agent/onskemal/leads", headers=DEMO,
                            json={"feedback": "Kortare mejl tack", "dokument": "Skriv kortare mejl."})
        assert sparad.status_code == 200
        client.put("/api/agent/onskemal/leads", headers=DEMO, json={"feedback": "x", "dokument": "Version två."})
        nu = client.get("/api/agent/onskemal/leads", headers=DEMO).json()
        assert nu["dokument"] == "Version två."
        assert len(nu["historik"]) == len(fore["historik"]) + 2

        forsta = next(h for h in nu["historik"] if h["content"] == "Skriv kortare mejl.")
        assert client.post(f"/api/agent/onskemal/leads/aterstall/{forsta['id']}", headers=DEMO).status_code == 200
        assert client.get("/api/agent/onskemal/leads", headers=DEMO).json()["dokument"] == "Skriv kortare mejl."


def test_okand_agent_och_dygnstak():
    with TestClient(app) as client:
        assert client.get("/api/agent/onskemal/bokforing", headers=DEMO).status_code == 404
        with patch.object(onskemal, "MAX_PER_DYGN", 0):
            svar = client.put("/api/agent/onskemal/support", headers=DEMO, json={"dokument": "x"})
        assert svar.status_code == 429
