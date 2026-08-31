"""Urvalet mot ICP:t — rena funktioner, ingen Gemini-nyckel."""

import httpx
import pytest

from app.leads import discovery
from app.leads.discovery import (
    DiscoveryError,
    _gemini_med_sokning,
    _plocka_json,
    _rena_traffar,
    normalisera_webbplats,
    webbplats_ar_bolagets,
)


@pytest.fixture
def anyio_backend():
    return "asyncio"


def test_webbplats_ar_bolagets_egen_sajt():
    assert webbplats_ar_bolagets("https://acme.se")
    assert webbplats_ar_bolagets("acme.se")
    assert not webbplats_ar_bolagets("https://allabolag.se/foretag/acme")
    assert not webbplats_ar_bolagets("https://hitta.se/acme")
    assert not webbplats_ar_bolagets("https://acme.example")
    assert not webbplats_ar_bolagets("")


def test_plocka_json_ur_staket_och_rent():
    assert _plocka_json('[{"company_name": "A", "website": "https://a.se"}]')[0]["company_name"] == "A"
    text = 'Här: ```json\n[{"company_name": "B", "website": "https://b.se"}]\n```'
    assert _plocka_json(text)[0]["company_name"] == "B"


def test_rena_traffar_kastar_aggregat_exempel_och_dubbletter():
    rader = [
        {"company_name": "Riktiga AB", "website": "https://riktiga.se"},
        {"company_name": "Riktiga AB", "website": "https://riktiga.se/om"},
        {"company_name": "Fejk AB", "website": "https://fejk.example"},
        {"company_name": "Register AB", "website": "https://allabolag.se/x"},
        {"company_name": "Utesluten AB", "website": "https://utesluten.se"},
    ]
    rena = _rena_traffar(rader, uteslut={"utesluten ab"}, tak=10)
    assert [r["company_name"] for r in rena] == ["Riktiga AB"]
    assert rena[0]["website"].startswith("https://riktiga.se")


def test_normalisera_webbplats_lagger_https():
    assert normalisera_webbplats("www.acme.se/") == "https://www.acme.se"


# -- Kontaktfältets fallback-trappa (kundkrav: "ALLTID kontaktuppgifter") --


def test_rena_traffar_haller_en_namngiven_traff_i_den_sokta_rollen():
    rader = [
        {
            "company_name": "Rolltraff AB",
            "website": "https://rolltraff.se",
            "contact_name": "Anna Andersson",
            "contact_role": "Marknadschef",
            "contact_email": "anna@rolltraff.se",
            "contact_level": "named_role_match",
        }
    ]
    [rad] = _rena_traffar(rader, uteslut=set(), tak=10)
    assert rad["contact_name"] == "Anna Andersson"
    assert rad["contact_role"] == "Marknadschef"
    assert rad["contact_level"] == "named_role_match"
    assert rad["contact_form_url"] is None


def test_rena_traffar_haller_en_rollbaserad_adress_utan_namn():
    rader = [
        {
            "company_name": "Rolladress AB",
            "website": "https://rolladress.se",
            "contact_email": "info@rolladress.se",
            "contact_level": "role_address",
        }
    ]
    [rad] = _rena_traffar(rader, uteslut=set(), tak=10)
    assert rad["contact_name"] is None
    assert rad["contact_email"] == "info@rolladress.se"
    assert rad["contact_level"] == "role_address"


def test_rena_traffar_haller_ett_kontaktformular_som_sista_utvag():
    rader = [
        {
            "company_name": "Bara Formular AB",
            "website": "https://baraformular.se",
            "contact_email": None,
            "contact_level": "contact_form",
            "contact_form_url": "https://baraformular.se/kontakt",
        }
    ]
    [rad] = _rena_traffar(rader, uteslut=set(), tak=10)
    assert rad["contact_email"] is None
    assert rad["contact_level"] == "contact_form"
    assert rad["contact_form_url"] == "https://baraformular.se/kontakt"


def test_rena_traffar_kastar_inte_rader_som_bara_saknar_ovriga_faltet():
    """Kravet ordagrant: en rad med kontaktuppgifter men utan t.ex. orgnr/ort
    ska aldrig försvinna här — company_name och website är de enda hårda
    kraven, oförändrat sedan innan trappan infördes."""
    rader = [
        {
            "company_name": "Bara Kontakt AB",
            "website": "https://barakontakt.se",
            "contact_email": "info@barakontakt.se",
            "contact_level": "role_address",
            # orgnr, ort, anstallda saknas helt
        }
    ]
    [rad] = _rena_traffar(rader, uteslut=set(), tak=10)
    assert rad["company_name"] == "Bara Kontakt AB"
    assert rad["contact_email"] == "info@barakontakt.se"
    assert rad["orgnr"] is None
    assert rad["ort"] is None


def test_rena_traffar_nedgraderar_en_pastadd_namngiven_traff_utan_namn():
    """En hallucinerad niva ska aldrig kunna få en okänd kontakt att se ut
    som en verifierad, namngiven träff i UI:t."""
    rader = [
        {
            "company_name": "Fejknamn AB",
            "website": "https://fejknamn.se",
            "contact_name": None,
            "contact_email": "info@fejknamn.se",
            "contact_level": "named_role_match",  # påstått, men inget namn med
        }
    ]
    [rad] = _rena_traffar(rader, uteslut=set(), tak=10)
    assert rad["contact_level"] == "role_address"


def test_rena_traffar_ignorerar_ett_kontaktformular_pa_annan_doman():
    rader = [
        {
            "company_name": "Extern Formular AB",
            "website": "https://externformular.se",
            "contact_email": None,
            "contact_level": "contact_form",
            "contact_form_url": "https://ett-helt-annat-bolag.se/kontakt",
        }
    ]
    [rad] = _rena_traffar(rader, uteslut=set(), tak=10)
    assert rad["contact_form_url"] is None
    assert rad["contact_level"] is None


@pytest.mark.anyio
async def test_hitta_bolag_kraver_kontakt_och_anvander_den_sokta_rollen(monkeypatch):
    """Prompten ska göra kontaktuppgift obligatorisk och nämna ICP:ts roll —
    inte lämna den som frivillig, vilket var hela boven i produktionsklagomålet."""
    sedd_prompt: dict[str, str] = {}

    async def _spion(prompt: str) -> str:
        sedd_prompt["prompt"] = prompt
        return "[]"

    monkeypatch.setattr(discovery, "_gemini_med_sokning", _spion)

    await discovery.hitta_bolag({"roles": ["Marknadschef"]}, 3)

    prompt = sedd_prompt["prompt"]
    assert "OBLIGATORISKT" in prompt
    assert "Marknadschef" in prompt
    assert "contact_level" in prompt
    assert "hitta inte pa personer" in prompt.lower()


class _FakeSettings:
    """Bara det _gemini_med_sokning läser — ingen riktig Settings-instans."""

    gemini_api_key = "fejk-" + "a" * 20
    model = "gemini-2.5-flash"

    def active_llm_key(self) -> str:
        return self.gemini_api_key


class _AlltidTimeout:
    """Ersätter httpx.AsyncClient — post() timar ut varje gång, som Gemini
    gör i produktion när google_search-grounding drar ut på tiden."""

    def __init__(self, *args, **kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    async def post(self, *args, **kwargs):
        raise httpx.ReadTimeout("gemini svarade inte i tid")


@pytest.mark.anyio
async def test_gemini_timeout_blir_discoveryerror_inte_ratt_httpx(monkeypatch):
    """Regression: httpx.ReadTimeout propagerade rått förbi hitta_bolags
    `except DiscoveryError`, vilket dödade hela batchkörningen (se
    app/api/leads.py _run_batch/_samla_korningens_prospekt). Anropskedjan
    litar på att _gemini_med_sokning ALDRIG läcker ett httpx-undantag."""
    monkeypatch.setattr(discovery, "get_settings", lambda: _FakeSettings())
    monkeypatch.setattr(discovery.httpx, "AsyncClient", _AlltidTimeout)
    monkeypatch.setattr(discovery.asyncio, "sleep", lambda *_a, **_k: _noop())

    with pytest.raises(DiscoveryError):
        await _gemini_med_sokning("hitta bolag")


async def _noop():
    return None
