"""Uppstart och tidsgränser (Fas 0-fynden K4, K6 och H7, 2026-11-09).

Tre saker som var osynliga tills de hände i drift:

* Postgres onåbar vid uppstart gav tyst minnesläge med grön hälsokontroll.
* Ingen klient hade en egen tidsgräns: LLM-anropen ärvde SDK:ns 600 s,
  databasen och Redis väntade utan slut.
* Vertex-tokenen förnyades med ett blockerande nätanrop på händelseloopen.
"""

from __future__ import annotations

import asyncio
import json
import threading
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import httpx
import pytest

import app.agent.llm as llm
import app.main as main
from app.config import Settings
from app.redisnycklar import anslutningsval

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend():
    return "asyncio"


def _installningar(**k) -> Settings:
    return Settings(_env_file=None, **k)


# -- K4: uppstarten ----------------------------------------------------------


async def test_onabar_databas_faller_uppstarten_i_stallet_for_minneslage(monkeypatch):
    forsok = []

    async def connect(_dsn):
        forsok.append(1)
        raise ConnectionRefusedError("nej")

    import app.storage.postgres as pg

    monkeypatch.setattr(pg.PostgresStorage, "connect", staticmethod(connect))
    s = _installningar(database_url="postgresql://snajp_app:hemligt@db.intern:5432/railway", db_start_forsok=3)

    with pytest.raises(RuntimeError) as fel:
        await main._anslut_postgres(s, paus_s=0)

    assert len(forsok) == 3, "varje försök ska göras innan uppstarten ger upp"
    text = str(fel.value)
    assert "db.intern" in text and "minnesläge" in text
    assert "hemligt" not in text, "anslutningssträngens lösenord får aldrig hamna i felet"


async def test_databas_som_vaknar_pa_andra_forsoket_racker(monkeypatch):
    svar = iter([ConnectionRefusedError("startar"), "lagringen"])

    async def connect(_dsn):
        v = next(svar)
        if isinstance(v, Exception):
            raise v
        return v

    import app.storage.postgres as pg

    monkeypatch.setattr(pg.PostgresStorage, "connect", staticmethod(connect))
    s = _installningar(database_url="postgresql://u:p@db.intern:5432/railway")
    assert await main._anslut_postgres(s, paus_s=0) == "lagringen"


async def test_utan_database_url_ar_minneslaget_kvar():
    """Testsviten och den lokala demon startar utan databas. Det är ett val."""
    async with main.app.router.lifespan_context(main.app):
        assert main.app.state.storage.name == "memory"


# -- K6: tidsgränser ---------------------------------------------------------


def test_llm_klienten_har_en_egen_tidsgrans():
    gr = llm._tidsgrans(_installningar(llm_timeout_s=90))
    assert isinstance(gr, httpx.Timeout)
    assert gr.read == 90 and gr.connect == 10


def test_standardgransen_ar_langt_under_sdk_ns_tio_minuter():
    s = _installningar()
    assert s.llm_timeout_s <= 180
    assert s.llm_timeout_chatt_s < s.llm_timeout_s


def test_redis_klienterna_far_tidsgranser_och_livstecken():
    from app.jobs.stream import BLOCK_MS

    val = anslutningsval()
    assert val["socket_connect_timeout"] > 0
    assert val["health_check_interval"] > 0
    assert val["socket_timeout"] > BLOCK_MS / 1000, (
        "socket_timeout måste vara längre än köns blockerande läsning, "
        "annars bryts varje tom läsning som ett fel"
    )


def test_databaspoolen_skapas_med_tidsgranser():
    from pathlib import Path

    kalla = (Path(__file__).resolve().parents[1] / "app" / "storage" / "postgres.py").read_text(encoding="utf-8")
    pool = kalla[kalla.index("asyncpg.create_pool(") : kalla.index("return cls(pool)")]
    assert "command_timeout=" in pool and "timeout=float(" in pool


class _LLM:
    """Fejkad klient i samma form som tests/agent/test_step_runner_temperature.py."""

    def __init__(self, hang_antal: int):
        self.hang_antal = hang_antal
        self.anrop = 0
        self.chat = self
        self.completions = self

    async def create(self, *, model, response_format, temperature, messages, **kwargs):
        self.anrop += 1
        if self.anrop <= self.hang_antal:
            await asyncio.sleep(30)
        payload = {"sources_used": [], "context_refs": []}
        message = type("M", (), {"content": json.dumps(payload)})()
        usage = type("U", (), {"prompt_tokens": 10, "completion_tokens": 5})()
        return type("R", (), {"choices": [type("C", (), {"message": message})()], "usage": usage})()


@pytest.fixture
def _chattgrans(monkeypatch):
    from app.config import get_settings

    monkeypatch.setenv("LLM_PROVIDER", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key-not-a-real-credential-000000")
    monkeypatch.setenv("LLM_TIMEOUT_CHATT_S", "0.05")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


async def _kor_steg(monkeypatch, klient, **k):
    from app.agent.step_runner import RunTrace, run_step
    from app.agentcore.packs import PlaybookStep, RunLedger

    monkeypatch.setattr("app.agent.step_runner.get_llm_client", lambda: klient)
    steg = PlaybookStep(skill="cs:ticket-triage", requires=("context_pack",))
    return await run_step(steg, RunLedger(satisfied={"context_pack"}), RunTrace(), task="test", case_context="test", **k)


async def test_chattsteget_overlever_ett_hangt_anrop(monkeypatch, _chattgrans):
    """Första anropet hänger; steget ger upp det efter gränsen och lyckas på omtaget."""
    klient = _LLM(hang_antal=1)
    await _kor_steg(monkeypatch, klient)
    assert klient.anrop == 2


async def test_chattsteget_faller_nar_bada_forsoken_hanger(monkeypatch, _chattgrans):
    """Hänger omtaget också är leverantören nere: steget ska falla NU, inte om tio minuter."""
    klient = _LLM(hang_antal=5)
    with pytest.raises(asyncio.TimeoutError):
        await asyncio.wait_for(_kor_steg(monkeypatch, klient), timeout=5)
    assert klient.anrop == 2


# -- H7: Vertex-tokenen ------------------------------------------------------


class _Creds:
    def __init__(self, *, token, kvar_s):
        self.token = token
        self.expiry = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(seconds=kvar_s)
        self.fornyad = threading.Event()
        self.slapp = threading.Event()
        self.fornyelsetrad: str | None = None

    @property
    def expired(self) -> bool:
        return (self.expiry - datetime.now(timezone.utc).replace(tzinfo=None)).total_seconds() < 225

    def refresh(self, _anrop) -> None:
        self.fornyelsetrad = threading.current_thread().name
        self.slapp.wait(2)  # nätanropet: tar tid, och anroparen ska inte vänta på det
        self.token = "ny"
        self.expiry = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(seconds=3600)
        self.fornyad.set()


def _med_creds(monkeypatch, creds):
    monkeypatch.setattr(llm, "_vertex_credentials", lambda _json: creds)
    monkeypatch.setattr(llm, "_fornyelseanrop", lambda: object())
    return SimpleNamespace(google_service_account_json="{}")


def test_farsk_token_returneras_utan_fornyelse(monkeypatch):
    creds = _Creds(token="gammal", kvar_s=3000)
    s = _med_creds(monkeypatch, creds)
    assert llm._vertex_token(s) == "gammal"
    assert not creds.fornyad.wait(0.2)


def test_token_nara_utgangen_fornyas_i_en_egen_trad(monkeypatch):
    """Anroparen får den gamla (giltiga) tokenen direkt; nätet väntas inte in."""
    creds = _Creds(token="gammal", kvar_s=400)
    s = _med_creds(monkeypatch, creds)

    assert llm._vertex_token(s) == "gammal"
    assert not creds.fornyad.is_set(), "anroparen fick sitt svar innan nätanropet var klart"
    creds.slapp.set()
    assert creds.fornyad.wait(2), "förnyelsen ska ha startats i bakgrunden"
    assert creds.fornyelsetrad == "vertex-token"
    assert creds.fornyelsetrad != threading.current_thread().name
    assert llm._vertex_token(s) == "ny"


def test_utgangen_token_fornyas_direkt(monkeypatch):
    creds = _Creds(token="gammal", kvar_s=10)
    creds.slapp.set()
    s = _med_creds(monkeypatch, creds)
    assert llm._vertex_token(s) == "ny"


def test_fornyelsens_natanrop_har_tio_sekunders_grans(monkeypatch):
    sedda = {}

    class Request:
        def __call__(self, *a, **k):
            sedda.update(k)

    import google.auth.transport.requests as gar

    monkeypatch.setattr(gar, "Request", Request)
    llm._fornyelseanrop()(url="https://oauth2.googleapis.com/token", timeout=120)
    assert sedda["timeout"] == llm._FORNYELSE_TIMEOUT_S == 10
