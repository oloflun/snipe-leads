"""Omindexeringen fyller på vektorer för artiklar sparade utan (fas 9, 2026-10-06)."""

from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from app.config import DEFAULT_TENANT_ID, get_settings
from app.main import app


def test_torrkorning_raknar_och_apply_baddar_in():
    master = {"X-API-Key": get_settings().snajp_master_api_key}
    with TestClient(app) as client:
        storage = app.state.storage
        import asyncio

        asyncio.run(storage.add_kb_article(DEFAULT_TENANT_ID, title="Frakt", content="Fri frakt över 500 kr.",
                                           category="leverans"))
        utan_fore = len(asyncio.run(storage.kb_utan_vektor(DEFAULT_TENANT_ID, limit=1000)))
        torr = client.post("/api/admin/kb/badda-in", headers=master,
                           params={"tenant_id": DEFAULT_TENANT_ID}).json()
        assert torr["kvar"] >= 1 and not torr["apply"]
        assert len(asyncio.run(storage.kb_utan_vektor(DEFAULT_TENANT_ID, limit=1000))) == utan_fore

        with patch("app.agent.embeddings.embed_text", new=AsyncMock(return_value=[0.1] * 1536)):
            skarp = client.post("/api/admin/kb/badda-in", headers=master,
                                params={"tenant_id": DEFAULT_TENANT_ID, "apply": "true"}).json()
        assert skarp["kunder"][0]["inbaddade"] == min(utan_fore, 50)
        assert len(asyncio.run(storage.kb_utan_vektor(DEFAULT_TENANT_ID, limit=1000))) == max(0, utan_fore - 50)


def test_kraver_masternyckel():
    with TestClient(app) as client:
        assert client.post("/api/admin/kb/badda-in").status_code in (401, 403)
