"""Leverantörens kvot är inte en krasch, och ska inte se ut som en.

Ett 429 från modelleverantören renderades som "Något gick fel på vår sida.
Felet är loggat" — exakt samma svar som ett nullpointerfel. Den som felsökte
gick till loggen och hittade en stack som slutade i http-klienten; att frågan
egentligen var "kvoten är slut, kolla planen" tog en halvtimme att komma fram
till.

Det är samma klass av fel som resten av kodbasen redan jagat: ett tillstånd
som HAR en begriplig orsak, presenterat som ett okänt haveri.
"""

import pytest

from app.api.events import _ar_kvotfel


class _FejkatKvotfel(Exception):
    """Speglar openai.RateLimitError utan att importera biblioteket."""

    status_code = 429


class RateLimitError(Exception):
    """Namnet är det leverantörens klass heter."""


class ResourceExhausted(Exception):
    """Googles namn på samma sak."""


@pytest.mark.parametrize(
    "fel",
    [
        _FejkatKvotfel("nope"),
        RateLimitError("nope"),
        ResourceExhausted("nope"),
        Exception(
            "Error code: 429 - [{'error': {'code': 429, 'message': 'You exceeded "
            "your current quota, please check your plan and billing details.'}}]"
        ),
    ],
)
def test_kvotfel_kanns_igen(fel):
    assert _ar_kvotfel(fel)


@pytest.mark.parametrize(
    "fel",
    [
        ValueError("något helt annat"),
        Exception("Error code: 500 - internal"),
        Exception("429 kr exklusive moms"),  # ett belopp, inte en statuskod
        TypeError("NoneType is not subscriptable"),
    ],
)
def test_riktiga_fel_maskeras_inte_som_kvot(fel):
    """Det farliga är åt andra hållet: ett riktigt fel som rapporteras som
    'kvoten är slut' skickar felsökaren till leverantörens fakturasida i
    stället för till buggen."""
    assert not _ar_kvotfel(fel)


# -- Kreditslut: den permanenta halvan av 429-klassen -----------------------
#
# "Your prepayment credits are depleted" går inte över av tålamod — det går
# över av att en människa betalar. Uppmätt 2026-09-08: chatten sa "försök
# igen om en stund", en leadskörning blev stående, och råtexten läckte till
# kundytan via jobbläsvägen. Testerna nedan vaktar de tre svaren: klassa
# rätt, faila fort, tala svenska — och larma OSS, deduplicerat.

from unittest.mock import AsyncMock, patch

from app.kvotfel import (
    KUNDTEXT_KREDITSLUT,
    KUNDTEXT_KVOT,
    ar_kreditslut,
    kundtext_for,
    larma_kreditslut,
    oversatt_felstext,
)

#: Googles svar, ordagrant som det mättes 2026-09-08.
GOOGLE_KREDITTEXT = (
    "Error code: 429 - [{'error': {'code': 429, 'message': 'Your prepayment "
    "credits are depleted. Please go to AI Studio at https://ai.studio/projects "
    "to manage your project and billing. Learn more at "
    "https://ai.google.dev/gemini-api/docs/billing#prepay. ', "
    "'status': 'RESOURCE_EXHAUSTED'}}]"
)

MINUTKVOTTEXT = (
    "Error code: 429 - [{'error': {'code': 429, 'message': 'You exceeded your "
    "current quota: GenerateRequestsPerMinutePerProjectPerModel-FreeTier', "
    "'status': 'RESOURCE_EXHAUSTED'}}]"
)


def test_kreditslut_kanns_igen_pa_googles_egen_text():
    assert ar_kreditslut(Exception(GOOGLE_KREDITTEXT))
    assert ar_kreditslut(GOOGLE_KREDITTEXT)


def test_minutkvot_ar_inte_kreditslut():
    """Skillnaden BÄR åtgärden: kvot väntas ut, kredit betalas. En minutkvot
    som klassas som kreditslut hade fällt jobb som hade klarat sig."""
    assert not ar_kreditslut(Exception(MINUTKVOTTEXT))
    assert _ar_kvotfel(Exception(MINUTKVOTTEXT))


def test_kundtext_skiljer_de_tva():
    assert kundtext_for(Exception(GOOGLE_KREDITTEXT)) == KUNDTEXT_KREDITSLUT
    assert kundtext_for(Exception(MINUTKVOTTEXT)) == KUNDTEXT_KVOT
    assert kundtext_for(ValueError("riktigt fel")) is None


def test_lasvagen_oversatter_lagrad_ratext():
    """Jobbfel lästes ut ordagrant — 'Error code: 429 - [{...}]' nådde
    kundytan (uppmätt i Leadslistors mejlruta 2026-09-11). Prefix från
    fail-vägen ('Prospekt x: ...') ändrar inte klassningen."""
    assert oversatt_felstext(GOOGLE_KREDITTEXT) == KUNDTEXT_KREDITSLUT
    assert oversatt_felstext(f"Prospekt abc-123: {GOOGLE_KREDITTEXT}") == KUNDTEXT_KREDITSLUT
    assert oversatt_felstext(MINUTKVOTTEXT) == KUNDTEXT_KVOT


def test_lasvagen_ror_inte_riktiga_diagnoser():
    """Skyddsnätet får aldrig gömma ett riktigt fel bakom en kvotmening."""
    assert oversatt_felstext(None) is None
    assert oversatt_felstext("") == ""
    assert oversatt_felstext("Prospektet saknar mottagaradress.") == (
        "Prospektet saknar mottagaradress."
    )
    assert oversatt_felstext("429 kr exklusive moms") == "429 kr exklusive moms"


def test_kundtexterna_lovar_inget_falskt():
    """Kredittexten får inte be kunden försöka igen (det hjälper inte förrän
    vi agerat) och måste säga att larmet redan gått. Kvottexten får."""
    assert "försök igen" not in KUNDTEXT_KREDITSLUT.casefold()
    assert "larmats" in KUNDTEXT_KREDITSLUT
    assert "försök igen" in KUNDTEXT_KVOT.casefold()


# -- Larmet -----------------------------------------------------------------


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.anyio
async def test_larmet_skriver_handelse_och_mejlar_med_dygnsnyckel():
    from app.storage.memory import MemoryStorage

    storage = MemoryStorage()
    with patch("app.notifications.prioriterat_mejl.skicka_prioriterat", new=AsyncMock()) as mejl:
        await larma_kreditslut(storage, tenant_id="t-1", kalla="chat")

    mejl.assert_awaited_once()
    nyckel = mejl.await_args.kwargs["nyckel"]
    assert nyckel.startswith("kreditslut:"), "nyckeln ska vara dygnet, inte anropet"

    handelser = await storage.list_platform_events(limit=10)
    rader = [h for h in handelser if "krediterna är slut" in h["message"].casefold()]
    assert rader, "kreditslutet ska synas i Händelser"
    assert rader[0]["level"] == "error"


@pytest.mark.anyio
async def test_larmet_kastar_aldrig():
    """Larmet får inte skugga grundfelet — en trasig mejlväg eller lagring
    ska ge en loggvarning, inte ett nytt undantag ovanpå kreditslutet."""

    class _TrasigLagring:
        def __getattr__(self, namn):
            raise RuntimeError("lagringen är nere")

    with patch(
        "app.notifications.prioriterat_mejl.skicka_prioriterat",
        new=AsyncMock(side_effect=RuntimeError("mejlvägen är nere")),
    ):
        await larma_kreditslut(_TrasigLagring(), tenant_id=None, kalla="api")


# -- Tålamodsloopen: kreditslut väntas aldrig ut ----------------------------


class _Kreditfel(Exception):
    status_code = 429

    def __str__(self) -> str:  # pragma: no cover — trivialt
        return GOOGLE_KREDITTEXT


class _Minutkvotfel(Exception):
    status_code = 429

    def __str__(self) -> str:  # pragma: no cover
        return MINUTKVOTTEXT


class _AlltidFel:
    def __init__(self, fel: Exception):
        self._fel = fel
        self.chat = self
        self.completions = self

    async def create(self, **_kwargs):
        raise self._fel


def _fejksteg():
    class _Steg:
        skill = "test:steg"
        requires: tuple[str, ...] = ()
        overlay_names: tuple[str, ...] = ()
        thinking = None
        temperature = None
        model_setting = None

        def render(self) -> str:
            return "Testskillens text."

    return _Steg()


async def _kor_steg_mot(fel: Exception, monkeypatch) -> list[float]:
    """Kör run_step mot en klient som alltid kastar `fel`. Returnerar de
    pauser tålamodsloopen tog. Undantaget förväntas alltid nå ut."""
    from app.agentcore.packs import RunLedger
    from app.agent import step_runner
    from app.config import get_settings

    monkeypatch.setenv("LLM_PROVIDER", "deepseek")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key-not-a-real-credential-000000")
    get_settings.cache_clear()

    somnar: list[float] = []

    async def fejksomn(sekunder: float) -> None:
        somnar.append(sekunder)

    monkeypatch.setattr(step_runner.asyncio, "sleep", fejksomn)
    try:
        with patch("app.agent.step_runner.get_llm_client", return_value=_AlltidFel(fel)):
            with pytest.raises(type(fel)):
                await step_runner.run_step(
                    _fejksteg(),
                    RunLedger(),
                    step_runner.RunTrace(),
                    task="testa",
                    case_context="test",
                    talamod_429=True,
                )
    finally:
        get_settings.cache_clear()
    return somnar


@pytest.mark.anyio
async def test_kreditslut_far_inget_talamod(monkeypatch):
    """60 sekunders väntan på en tom kredit är 60 sekunder av processing
    som kunden tittar på — kreditslutet ska rakt upp till felvägen direkt."""
    somnar = await _kor_steg_mot(_Kreditfel(), monkeypatch)
    assert somnar == []


@pytest.mark.anyio
async def test_minutkvot_far_fortfarande_talamod(monkeypatch):
    """Kontrollgruppen: den transienta halvan ska bete sig exakt som förut
    (20 s + 40 s innan tredje försöket får kasta)."""
    somnar = await _kor_steg_mot(_Minutkvotfel(), monkeypatch)
    assert somnar == [20.0, 40.0]


# -- Jobbläsvägen -----------------------------------------------------------


@pytest.mark.anyio
async def test_jobblasvagen_oversatter_lagrat_kreditfel():
    """GET /api/jobs/{id} är den enda pollvägen (leads/jobb och
    testchatt/jobb proxar hit) — översättningen här täcker varje yta,
    gamla redan-lagrade fel inräknade."""
    from app.api.chat import get_job
    from app.jobs.store import MemoryJobStore

    jobs = MemoryJobStore()
    job_id = await jobs.create(tenant_id="t-1")
    await jobs.fail(job_id, GOOGLE_KREDITTEXT)

    class _State:
        pass

    class _App:
        state = _State()

    class _Request:
        app = _App()

    _Request.app.state.jobs = jobs

    svar = await get_job(_Request(), job_id, {"tenant_id": "t-1"})
    assert svar["error"] == KUNDTEXT_KREDITSLUT

    # Ett riktigt fel passerar orört — läsvägen får inte gömma diagnoser.
    job2 = await jobs.create(tenant_id="t-1")
    await jobs.fail(job2, "Prospektet saknar mottagaradress.")
    svar2 = await get_job(_Request(), job2, {"tenant_id": "t-1"})
    assert svar2["error"] == "Prospektet saknar mottagaradress."
