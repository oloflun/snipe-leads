"""Vektorns längd måste stämma med kolumnen den ska skrivas i.

`ss_knowledge_base.embedding` är `vector(1536)` sedan migration 002.
`gemini-embedding-001` returnerar 3072 värden om ingen ber om något annat.

Krocken har aldrig prövats i drift: Gemini-API:t var inte aktiverat på
Google-projektet, så VARJE embedding-anrop svarade 403 och noll av 159
artiklar bar en vektor. Först när nyckeln byttes mot en som fungerar kunde
felet nå databasen — och då som ett 500 på `POST /api/kb`, alltså en
fungerande försämring utbytt mot ett avbrott.

Testet mockar klienten. Det som ska bevisas är att anropet BEGÄR rätt längd,
inte att Google svarar rätt — det senare kräver nätverk och en nyckel.
"""

from __future__ import annotations

import pytest

from app.agent import embeddings as modul
from app.config import get_settings


class _FejkadKlient:
    def __init__(self) -> None:
        self.anrop: dict = {}
        self.embeddings = self

    async def create(self, **kwargs):
        self.anrop = kwargs

        class _Svar:
            data = [type("D", (), {"embedding": [0.0] * kwargs["dimensions"]})()]

        return _Svar()


@pytest.mark.anyio
async def test_anropet_begar_kolumnens_dimension(monkeypatch):
    klient = _FejkadKlient()
    monkeypatch.setattr(modul, "get_embedding_client", lambda: klient)

    vektor = await modul.embed_text("Vad kostar frakten till Norrland?")

    assert klient.anrop["dimensions"] == 1536, (
        "Anropet begär inte 1536 dimensioner. gemini-embedding-001 ger då 3072 "
        "värden, och kolumnen ss_knowledge_base.embedding är vector(1536) — "
        "varje KB-skrivning skulle falla."
    )
    assert len(vektor) == 1536


def test_installningen_stammer_med_migrationen():
    """Kolumnen är sanningen. Ändras den ska det här testet ändras med."""
    assert get_settings().embedding_dimensions == 1536


@pytest.fixture
def anyio_backend():
    return "asyncio"
