"""Jev med Gemini som motor (2026-11-22): samma kontrakt som TypeSafe, och en
gissning utan belägg kan aldrig fälla ett bolag."""

from __future__ import annotations

import pytest

from app.config import get_settings
from app.leads import jev, jev_gemini

PROFIL = {"malgrupp": "B2B", "kriterier": [{"id": "k1", "krav": "maste", "text": "säljer till företag"}],
          "uteslut": [{"text": "en kommun"}]}


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
def gemini_pa(monkeypatch):
    monkeypatch.setenv("IRIS_JEV", "pa")
    monkeypatch.setenv("JEV_MOTOR", "gemini")
    monkeypatch.setenv("LLM_PROVIDER", "gemini")
    monkeypatch.setenv("GOOGLE_SERVICE_ACCOUNT_JSON", '{"project_id": "x"}')
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_motorn_ar_gemini_som_standard_och_typesafe_bara_uttryckligen(monkeypatch):
    monkeypatch.delenv("JEV_MOTOR", raising=False)
    get_settings.cache_clear()
    assert jev.motor() == "gemini"
    monkeypatch.setenv("JEV_MOTOR", "typesafe")
    get_settings.cache_clear()
    assert jev.motor() == "typesafe"
    get_settings.cache_clear()


def test_ai_studio_racker_inte(monkeypatch):
    """Inkorgen skickar kundmejl hit: bara Vertex, aldrig AI Studio."""
    monkeypatch.setenv("LLM_PROVIDER", "gemini")
    monkeypatch.setenv("GOOGLE_SERVICE_ACCOUNT_JSON", "")
    monkeypatch.setenv("GEMINI_API_KEY", "nyckel")
    get_settings.cache_clear()
    assert not jev_gemini.redo()
    get_settings.cache_clear()


@pytest.mark.anyio
async def test_triagen_faller_bara_pa_belagg(gemini_pa, monkeypatch):
    svar: dict = {}

    async def fraga(state, fragor):
        return jev_gemini.tolka(fragor, {"answers": svar})

    monkeypatch.setattr(jev_gemini, "fraga", fraga)
    svar.update(fit={"score": 0, "confidence": 0.9}, krav_k1={"noul": 0.0, "confidence": 0.99, "evidence": ""})
    utan = await jev.triage(PROFIL, {"company_name": "A AB"}, utdrag="Välkommen.", signaler=[])
    assert utan["beslut"] == "vidare" and utan["fall_skal"] == []

    svar.update(uteslut_u1={"noul": 0.97, "confidence": 0.95, "evidence": "Umeå kommun är en myndighet"})
    med = await jev.triage(PROFIL, {"company_name": "Umeå kommun"}, utdrag="Umeå kommun är en myndighet.",
                           signaler=[])
    assert med["beslut"] == "fall" and any("kommun" in s for s in med["fall_skal"])


def test_webbkriterier_fragas_aldrig_till_jev():
    """Regel 9: webbkriterier avgörs i kod. Umeå Webdesigns profil i main
    (2026-11-23) har två måste-krav som kunden menade som "eller"; läst
    bokstavligt fäller det andra varje bolag som har en sajt."""
    from app.leads import jev

    profil = {
        "malgrupp": "Bolag med gamla hemsidor eller bara Facebook",
        "kriterier": [
            {"id": "k1", "krav": "maste", "belagg": "webbsignal", "text": "Bolag med tråkiga och gamla hemsidor."},
            {"id": "k2", "krav": "maste", "belagg": "webbsignal", "text": "Bolag som saknar hemsida och endast har en Facebook-profil."},
            {"id": "k3", "krav": "maste", "belagg": "kalltext", "text": "Säljer till privatpersoner"},
        ],
    }
    fragor = jev._fragor(profil, [])
    assert "krav_k1" not in fragor and "krav_k2" not in fragor
    assert "krav_k3" in fragor
    # Ett säkert nej på ett webbkriterium kan alltså aldrig fälla.
    tolkat = jev._tolka(profil, {"krav_k2": {"noul": 0.01, "confidence": 0.99}}, [])
    assert tolkat["fall_skal"] == []
