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
    #
    # DATABASE_URL hörde inte till listan från början, och exakt det som
    # docstringen varnar för hände igen: så fort den sattes i .env körde hela
    # sviten mot den RIKTIGA databasen. Testerna skapade skräptenants i
    # produktion, skrev över en befintlig tenants namn (create_tenant gör
    # `on conflict (slug) do update set name`) och tog 6,5 minuter i stället
    # för 5 sekunder. Utan den här raden är sviten inte hermetisk — den är
    # destruktiv.
    for name in (
        "DEEPSEEK_API_KEY",
        "OPENAI_API_KEY",
        "GEMINI_API_KEY",
        "EMBEDDING_API_KEY",
        "SCRAPEGRAPHAI_API_KEY",
        "DATABASE_URL",
        "REDIS_URL",
        # IMAP hörde inte till listan, och samma sak hände en tredje gång: med
        # riktiga värden i .env öppnade ett test av /api/inbox/sync en SKARP
        # IMAP-anslutning mot en riktig brevlåda. Loggen visade
        # "[AUTHENTICATIONFAILED] Invalid credentials" — alltså ett verkligt
        # inloggningsförsök mot en extern server, från en testsvit som ska vara
        # hermetisk. Ett test som vill pröva IMAP sätter värdena själv.
        "IMAP_HOST",
        "IMAP_USER",
        "IMAP_PASSWORD",
    ):
        monkeypatch.setenv(name, "")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()
