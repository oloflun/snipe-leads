"""Testsviten ska vara HERMETISK.

Innan riktiga nycklar fanns i snajp-support/.env passerade sviten av ren tur:
`is_simulation()` var sann, så inget test kunde råka nå ett riktigt API. Så
fort DEEPSEEK_API_KEY sattes började 17 tester göra skarpa nätverksanrop och
falla — testresultatet berodde alltså på om utvecklaren råkade ha nycklar.

Här tvingas simuleringsläge för ALLA tester. Ett test som medvetet vill köra
mot en riktig nyckel får sätta den själv (se t.ex.
tests/agent/test_support_agent_wiring.py, som sätter en fejkad nyckel och
mockar LLM-klienten — den gör fortfarande inga nätverksanrop).
"""

import pytest

from app.config import get_settings


@pytest.fixture(autouse=True)
def _force_simulation_mode(monkeypatch):
    # Tomma värden override:ar .env-filen (env-variabler har högre prioritet
    # i pydantic-settings). Det gör is_simulation() sann och håller varje
    # oavsiktlig live-väg stängd.
    for name in (
        "DEEPSEEK_API_KEY",
        "OPENAI_API_KEY",
        "GEMINI_API_KEY",
        "EMBEDDING_API_KEY",
        "SCRAPEGRAPHAI_API_KEY",
    ):
        monkeypatch.setenv(name, "")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()
