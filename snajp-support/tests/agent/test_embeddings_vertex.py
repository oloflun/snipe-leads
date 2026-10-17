"""Inbäddningar via Vertex egna API (:predict).

Den OpenAI-kompatibla vägen hos Vertex svarar 500 på varje inbäddningsanrop
(uppmätt 2026-09-12 och 2026-10-06), så kunskapsbasen söktes bara med fulltext.
"""

import json
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from app.agent import embeddings

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend():
    return "asyncio"


async def test_vertex_predict_ber_om_ratt_dimension_och_lasar_vektorn(monkeypatch):
    settings = SimpleNamespace(
        google_service_account_json=json.dumps({"project_id": "p1"}),
        google_cloud_region="europe-west1",
        embedding_model="gemini-embedding-001",
        embedding_dimensions=1536,
    )
    sedd: dict = {}

    class _Svar:
        def raise_for_status(self):
            return None

        def json(self):
            return {"predictions": [{"embeddings": {"values": [0.1] * 1536}}]}

    class _Klient:
        def __init__(self, *a, **k):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        async def post(self, url, headers, json):
            sedd.update(url=url, json=json)
            return _Svar()

    with (
        patch("httpx.AsyncClient", _Klient),
        patch("app.agent.llm._vertex_token", return_value="t"),
    ):
        vektor = await embeddings._vertex_predict(settings, "Hur bokar jag om?")
    assert len(vektor) == 1536
    assert sedd["url"].startswith("https://europe-west1-aiplatform.googleapis.com/v1/projects/p1/locations/europe-west1/")
    assert sedd["url"].endswith("/models/gemini-embedding-001:predict")
    assert sedd["json"]["parameters"]["outputDimensionality"] == 1536
