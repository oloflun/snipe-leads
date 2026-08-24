"""Spärren som hindrar att kunddata skickas till DeepSeek (Kina).

Testet finns för att spärren är det slags skydd som är lätt att råka vända
tillbaka: någon sätter LLM_PROVIDER=deepseek i Railway för att spara pengar,
allt ser ut att fungera lokalt, och felet upptäcks först vid en tillsyn.
Ett rött test i CI är den billigaste platsen att upptäcka det på.

Se app/config.py: Settings.llm_provider_fault.
"""

import pytest

from app.agent.llm import ForbjudenProviderIMiljon, krav_tillaten_provider
from app.config import Settings, get_settings


def _settings(**kwargs) -> Settings:
    # _env_file=None: annars läses snajp-support/.env in och testet mäter
    # utvecklarens maskin i stället för koden.
    return Settings(_env_file=None, **kwargs)


@pytest.mark.parametrize("miljo", ["main", "MAIN", "production", "development", "dev"])
def test_deepseek_vagras_i_miljoer_med_kunddata(miljo):
    fel = _settings(llm_provider="deepseek", environment=miljo).llm_provider_fault()
    assert fel is not None
    assert "deepseek" in fel.lower()


def test_railway_variabeln_racker_ensam():
    """Railway sätter RAILWAY_ENVIRONMENT_NAME automatiskt. Spärren får inte
    kräva att någon dessutom kommer ihåg att sätta ENVIRONMENT — en spärr som
    kräver en manuell variabel skyddar bara den som redan var noggrann."""
    fel = _settings(
        llm_provider="deepseek", railway_environment_name="development"
    ).llm_provider_fault()
    assert fel is not None


def test_openai_ar_alltid_tillaten():
    for miljo in ("main", "development", "", "lokal"):
        assert _settings(llm_provider="openai", environment=miljo).llm_provider_fault() is None


def test_deepseek_tillaten_mot_syntetisk_data():
    """Okänd/lokal miljö = utveckling mot MemoryStorage. Se `har_riktig_kunddata`
    för varför det är rätt håll att falla."""
    assert _settings(llm_provider="deepseek", environment="").llm_provider_fault() is None
    assert _settings(llm_provider="deepseek", environment="lokal").llm_provider_fault() is None


def test_klientbygget_kastar_i_stallet_for_att_bygga(monkeypatch):
    """Bältet till hängslet: en ingång som inte går via lifespan ska också
    stoppas, och den ska stoppas INNAN en klient finns att ringa med."""
    monkeypatch.setenv("LLM_PROVIDER", "deepseek")
    monkeypatch.setenv("ENVIRONMENT", "main")
    get_settings.cache_clear()
    try:
        with pytest.raises(ForbjudenProviderIMiljon):
            krav_tillaten_provider()
    finally:
        get_settings.cache_clear()
