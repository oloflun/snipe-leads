"""Automationsreglerna per lead-typ (app/leads/automation.py) och deras fyra
konsumenter. Standardvärdena ska vara exakt beteendet före reglerna fanns."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from app.leads import automation
from app.leads.follow_up_generator import trad_som_ar_forfallna
from app.storage.memory import MemoryStorage

TENANT = "00000000-0000-4000-a000-000000000001"
NU = datetime(2026, 10, 2, 12, 0, tzinfo=timezone.utc)

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend():
    return "asyncio"


def _trad(**over):
    grund = {
        "id": "t-1",
        "outbound_sent_count": 1,
        "last_outbound_sent_at": (NU - timedelta(days=5)).isoformat(),
        "last_inbound_at": None,
        "has_pending_item": False,
        "origin": "iris",
    }
    grund.update(over)
    return grund


# -- normalisera och typ_av --------------------------------------------------


def test_trasigt_blir_standard():
    for trasigt in (None, "x", 3, [], {"per_typ": "nej"}, {"per_typ": {"iris": "nej"}}):
        assert automation.normalisera(trasigt) == automation.STANDARD


def test_dagar_klipps_och_bool_vaktas():
    regler = automation.normalisera(
        {
            "per_typ": {
                "iris": {"uppfoljning_dagar": 999, "utkast_auto": "ja"},
                "lista": {"uppfoljning_dagar": -3},
                "inkorg": {"uppfoljning_dagar": True, "utkast_auto": True},
            },
            "jev_bortval": False,
        }
    )
    assert regler["per_typ"]["iris"] == {"utkast_auto": True, "uppfoljning_dagar": 60}
    assert regler["per_typ"]["lista"]["uppfoljning_dagar"] == 0
    assert regler["per_typ"]["inkorg"] == {"utkast_auto": True, "uppfoljning_dagar": 4}
    assert regler["jev_bortval"] is False
    # STANDARD får aldrig muteras av en normalisering.
    assert automation.STANDARD["per_typ"]["iris"]["uppfoljning_dagar"] == 4


def test_typ_av():
    assert automation.typ_av("inkorg") == "inkorg"
    assert automation.typ_av("import") == "import"
    assert automation.typ_av("lista") == "lista"
    for annat in ("iris", "manual", "test", "example", None, ""):
        assert automation.typ_av(annat) == "iris"


# -- Konsument 1: uppföljningen ------------------------------------------------


def test_standard_ger_dagens_fyra_dagar():
    assert trad_som_ar_forfallna([_trad()], now=NU) == trad_som_ar_forfallna(
        [_trad()], now=NU, automation=automation.STANDARD
    )
    assert len(trad_som_ar_forfallna([_trad()], now=NU)) == 1
    tidig = _trad(last_outbound_sent_at=(NU - timedelta(days=3)).isoformat())
    assert trad_som_ar_forfallna([tidig], now=NU) == []


def test_noll_dagar_hoppar_over_traden_helt():
    regler = {"per_typ": {"import": {"uppfoljning_dagar": 0}}}
    importerad = _trad(origin="import")
    assert trad_som_ar_forfallna([importerad], now=NU, automation=regler) == []
    # Också senare steg: 0 betyder inga uppföljningar alls för typen.
    steg2 = _trad(origin="import", outbound_sent_count=2, last_outbound_sent_at=(NU - timedelta(days=30)).isoformat())
    assert trad_som_ar_forfallna([steg2], now=NU, automation=regler) == []
    # Andra typer påverkas inte.
    assert len(trad_som_ar_forfallna([_trad(origin="iris")], now=NU, automation=regler)) == 1


def test_egen_vantetid_galler_bara_forsta_steget():
    regler = {"per_typ": {"iris": {"uppfoljning_dagar": 10}}}
    assert trad_som_ar_forfallna([_trad()], now=NU, automation=regler) == []
    steg2 = _trad(outbound_sent_count=2, last_outbound_sent_at=(NU - timedelta(days=6)).isoformat())
    assert len(trad_som_ar_forfallna([steg2], now=NU, automation=regler)) == 1


async def test_lagringen_bar_origin_till_svepet():
    storage = MemoryStorage()
    p = await storage.create_prospect(TENANT, company_name="Alfa AB", origin="import")
    await storage.ensure_outreach_thread(TENANT, prospect_id=p["id"])
    [trad] = await storage.list_outreach_threads(TENANT)
    assert trad["origin"] == "import"


# -- Konsument 2: inkorgen -----------------------------------------------------


async def _inkorgslead(monkeypatch, storage) -> list[dict]:
    from app.api import leads as leads_api
    from app.email_pipeline import processor
    from app.jobs.store import MemoryJobStore
    from app.main import app

    koade: list[dict] = []

    async def _stubb(app_state, tenant, prospects, **kw):
        koade.append({"tenant": tenant, "prospects": prospects, **kw})
        return []

    monkeypatch.setattr(leads_api, "_lagg_prospektjobb", _stubb)
    monkeypatch.setattr(processor, "get_settings", lambda: SimpleNamespace(is_simulation=lambda: False))
    monkeypatch.setattr(app.state, "jobs", MemoryJobStore(), raising=False)
    mejl = {"id": "m-1", "from_email": "vd@nykund.se", "from_name": "Nykund AB", "body_text": "Hej"}
    await processor._hantera_lead(storage, TENANT, mejl, {"klass": "lead"})
    return koade


async def test_inkorgen_standard_koar_inget(monkeypatch):
    storage = MemoryStorage()
    assert await _inkorgslead(monkeypatch, storage) == []
    assert [p["origin"] for p in await storage.list_prospects(TENANT)] == ["inkorg"]


async def test_inkorgen_utkast_auto_koar_research_och_utkast(monkeypatch):
    storage = MemoryStorage()
    await storage.set_agent_settings(
        TENANT, agent_type="leads", settings={"automation": {"per_typ": {"inkorg": {"utkast_auto": True}}}}
    )
    [kod] = await _inkorgslead(monkeypatch, storage)
    assert kod["scope"] == "research_and_draft"
    assert kod["prospects"][0]["origin"] == "inkorg"
    assert kod["tenant"]["tenant_id"] == TENANT


# -- Konsument 3: Flytta till Iris ---------------------------------------------


async def _till_iris(monkeypatch, storage, *, kalla: str, regler: dict | None):
    from app.api import leads as leads_api
    from app.api.schemas import TillIrisRequest
    from app.jobs.store import MemoryJobStore

    if regler is not None:
        await storage.set_agent_settings(TENANT, agent_type="leads", settings={"automation": regler})
    lista = await storage.create_lead_list(TENANT, titel="L", icp={}, antal=1, kalla=kalla)
    await storage.add_lead_list_item(TENANT, list_id=lista["id"], company_name="Gamma AB")
    await storage.set_lead_list_status(TENANT, lista["id"], status="klar")

    scopes: list[str] = []

    async def _stubb(app_state, tenant, prospects, *, scope, **kw):
        scopes.append(scope)
        return []

    async def _ingen(*_a, **_k):
        return None

    monkeypatch.setattr(leads_api, "_lagg_prospektjobb", _stubb)
    monkeypatch.setattr(leads_api, "_require_live_llm", lambda: None)
    monkeypatch.setattr(leads_api, "_kraev_leads_budget", _ingen)
    app_state = SimpleNamespace(jobs=MemoryJobStore(), storage=storage, leadsstrom=None)
    req = SimpleNamespace(app=SimpleNamespace(state=app_state))
    ut = await leads_api.listan_till_iris(
        req, lista["id"], TillIrisRequest(), {"tenant_id": TENANT, "tenant_name": "Snajp"}
    )
    prospekt = await storage.list_prospects(TENANT)
    return ut["scope"], scopes, prospekt[0]["origin"]


async def test_till_iris_scope_none_standard_ger_utkast(monkeypatch):
    scope, koade, origin = await _till_iris(monkeypatch, MemoryStorage(), kalla="sok", regler=None)
    assert scope == "research_and_draft" and koade == ["research_and_draft"]
    assert origin == "lista"


async def test_till_iris_scope_none_foljer_importregeln(monkeypatch):
    regler = {"per_typ": {"import": {"utkast_auto": False}}}
    scope, koade, origin = await _till_iris(monkeypatch, MemoryStorage(), kalla="import", regler=regler)
    assert scope == "research" and koade == ["research"]
    assert origin == "import"
    # Samma regel rör inte en sökbyggd lista.
    scope2, _, _ = await _till_iris(monkeypatch, MemoryStorage(), kalla="sok", regler=regler)
    assert scope2 == "research_and_draft"


# -- Konsument 4: Jev-bortvalet ------------------------------------------------


async def test_jev_bortval_av_later_kandidaten_ga_vidare(monkeypatch):
    from app.leads import jev

    monkeypatch.setattr(jev, "aktiv", lambda: True)
    monkeypatch.setattr(jev, "lage", lambda: "pa")

    async def _svar(*_a, **_k):
        return {}

    monkeypatch.setattr(jev, "fraga", _svar)
    monkeypatch.setattr(jev, "_tolka", lambda *_a, **_k: {"fall_skal": ["fel bransch"]})
    kandidat = {"company_name": "Delta AB"}

    pa = await jev.triage({}, kandidat, utdrag="", signaler=[])
    assert pa["beslut"] == "fall", "standard (jev_bortval True) är dagens beteende"
    av = await jev.triage({"jev_bortval": False}, kandidat, utdrag="", signaler=[])
    assert av["beslut"] == "vidare" and av["skulle_falla"] is True

    monkeypatch.setattr(jev, "lage", lambda: "skugga")
    skugga = await jev.triage({}, kandidat, utdrag="", signaler=[])
    assert skugga["beslut"] == "vidare"


async def test_korningens_profil_bar_jev_bortval(monkeypatch):
    from app.api import leads as leads_api

    async def _profil(*_a, **_k):
        return {"version": 1}

    monkeypatch.setattr(leads_api, "sakerstall_profil", _profil)
    storage = MemoryStorage()
    profil, _ = await leads_api._korningens_profil(storage, TENANT, None)
    assert profil["jev_bortval"] is True
    await storage.set_agent_settings(TENANT, agent_type="leads", settings={"automation": {"jev_bortval": False}})
    profil, _ = await leads_api._korningens_profil(storage, TENANT, None)
    assert profil["jev_bortval"] is False
