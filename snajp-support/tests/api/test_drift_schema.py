"""GET /api/drift/schema (synkflytten steg 9): liggarens versioner för
PR-kontrollen, bakom den smala nyckeln SCHEMA_LASNYCKEL och inget annat."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import app

NYCKEL = "test-schemanyckel-inte-riktig-0000"


@pytest.fixture
def klient(monkeypatch):
    def bygg(nyckel: str | None):
        if nyckel is None:
            monkeypatch.delenv("SCHEMA_LASNYCKEL", raising=False)
        else:
            monkeypatch.setenv("SCHEMA_LASNYCKEL", nyckel)
        get_settings.cache_clear()
        return TestClient(app)

    yield bygg
    get_settings.cache_clear()


def test_utan_nyckel_i_miljon_ar_vagen_stangd(klient):
    with klient(None) as c:
        assert c.get("/api/drift/schema").status_code == 404
        assert c.get("/api/drift/schema", headers={"X-Schema-Nyckel": "vad-som-helst"}).status_code == 404


def test_fel_eller_saknad_nyckel_ger_401(klient):
    with klient(NYCKEL) as c:
        assert c.get("/api/drift/schema").status_code == 401
        assert c.get("/api/drift/schema", headers={"X-Schema-Nyckel": "fel"}).status_code == 401
        # Masternyckeln öppnar inte den här vägen.
        assert c.get("/api/drift/schema", headers={"X-API-Key": get_settings().snajp_master_api_key}).status_code == 401


def test_ratt_nyckel_ger_bara_versionerna(klient, monkeypatch):
    with klient(NYCKEL) as c:
        async def versioner():
            return ["b_002", "a_001"]

        monkeypatch.setattr(c.app.state.storage, "schema_versioner", versioner)
        svar = c.get("/api/drift/schema", headers={"X-Schema-Nyckel": NYCKEL})
    assert svar.status_code == 200
    data = svar.json()
    assert set(data) == {"miljo", "versioner"}
    assert data["versioner"] == ["a_001", "b_002"]


def test_minneslagret_har_ingen_liggare():
    import asyncio

    from app.storage.memory import MemoryStorage

    assert asyncio.run(MemoryStorage().schema_versioner()) == []
