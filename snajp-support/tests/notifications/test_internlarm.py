"""Internlarmet: en notis per händelse, och aldrig ett fel som når kunden.

De två frågorna som avgör om larmvägen är byggd rätt:

  1. Kan den spamma? (en notis per efterföljande meddelande i ett redan
     eskalerat ärende är hur man lär folk att filtrera bort larmet)
  2. Kan den fälla det den larmar om? (ett ärende som redan gått fel för
     kunden ska inte också bli ett uteblivet svar för att Gmail hade en
     dålig dag)

SMTP mockas på `smtplib.SMTP`. Ingen rad här öppnar en socket — sviten ska
vara hermetisk, se tests/conftest.py.
"""

from __future__ import annotations

import smtplib
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.config import get_settings
from app.notifications import internlarm
from app.notifications.internlarm import (
    MOTTAGARE,
    PRIORITETSMARKOR,
    arendelank,
    har_konfiguration,
    larma,
    nollstall_dubblettminne,
)


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture(autouse=True)
def _rent_dubblettminne():
    """Utan den läcker en testfils tillstånd in i nästa — modulen håller
    dubblettnycklarna i en modulnivå-dict."""
    nollstall_dubblettminne()
    yield
    nollstall_dubblettminne()


@pytest.fixture
def konfigurerad(monkeypatch):
    """Sätter larmvägens uppgifter OCH tömmer settings-cachen.

    `Settings` är lru_cachead, och modulen läser uppgifterna därifrån och inte
    med `os.getenv` (se `_konfiguration`). Utan cache_clear hade en tidigare
    `get_settings()` i samma process gjort setenv verkningslös — testet hade
    då blivit grönt eller rött beroende på anropsordningen.
    """
    monkeypatch.setenv("INTERNLARM_SMTP_ANVANDARE", "snajpsupport@gmail.com")
    monkeypatch.setenv("INTERNLARM_SMTP_LOSENORD", "app-losenord-16-tecken")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def smtp():
    """Fångar SMTP-sessionen. `server` är det som `with smtplib.SMTP(...)` ger."""
    with patch("smtplib.SMTP") as fabrik:
        server = MagicMock()
        fabrik.return_value.__enter__.return_value = server
        yield fabrik, server


def _skickade(server) -> list:
    return [anrop.args[0] for anrop in server.send_message.call_args_list]


# -- 1. Formen på mejlet ---------------------------------------------------


@pytest.mark.anyio
async def test_amnesraden_bar_prioritetsmarkoren(konfigurerad, smtp):
    _, server = smtp
    assert await larma(
        "Supportärende eskalerat",
        tenant_id="t-1",
        vad="Ärende 42 lämnades över.",
        varfor="Kunskapsbasen räckte inte.",
        nyckel="k1",
    )

    (mejl,) = _skickade(server)
    assert mejl["Subject"] == f"{PRIORITETSMARKOR} Supportärende eskalerat"
    assert mejl["To"] == MOTTAGARE


@pytest.mark.anyio
async def test_brodtexten_bar_tenant_vad_varfor_och_lank(konfigurerad, smtp):
    _, server = smtp
    await larma(
        "Rubrik",
        tenant_id="t-1",
        vad="Ärende 42 lämnades över.",
        varfor="Kunskapsbasen räckte inte.",
        lank="https://snajp.se/admin/kunder?arende=42",
        nyckel="k1",
    )

    text = _skickade(server)[0].get_content()
    assert "t-1" in text
    assert "Ärende 42 lämnades över." in text
    assert "Kunskapsbasen räckte inte." in text
    assert "https://snajp.se/admin/kunder?arende=42" in text


def test_arendelanken_ar_tom_utan_bas_url():
    """En länk som inte går någonstans är sämre än ingen länk — den ser ut att
    fungera."""
    assert arendelank("", "42") == ""
    assert arendelank("https://snajp.se", "") == ""
    assert arendelank("https://snajp.se/", "42") == "https://snajp.se/admin/kunder?arende=42"


# -- 2. En notis per händelse ---------------------------------------------


@pytest.mark.anyio
async def test_samma_nyckel_skickar_bara_en_gang(konfigurerad, smtp):
    _, server = smtp
    argument = dict(tenant_id="t-1", vad="v", varfor="v", nyckel="support:t-1:arende-42")

    assert await larma("Första", **argument) is True
    assert await larma("Andra", **argument) is False
    assert await larma("Tredje", **argument) is False

    assert server.send_message.call_count == 1


@pytest.mark.anyio
async def test_olika_nycklar_skickar_var_sitt(konfigurerad, smtp):
    _, server = smtp
    await larma("A", tenant_id="t-1", vad="v", varfor="v", nyckel="a")
    await larma("B", tenant_id="t-1", vad="v", varfor="v", nyckel="b")

    assert server.send_message.call_count == 2


@pytest.mark.anyio
async def test_ett_misslyckat_larm_sparrar_inte_nasta_forsok(konfigurerad, smtp):
    """Dubblettspärren får inte göra ett tillfälligt fel permanent.

    Går sändningen inte fram har ingen blivit tillsagd, och då ska nästa
    försök få gå. Nyckeln plockas därför bort igen vid fel.
    """
    fabrik, server = smtp
    server.send_message.side_effect = smtplib.SMTPServerDisconnected("nätet dog")

    assert await larma("R", tenant_id="t-1", vad="v", varfor="v", nyckel="k") is False

    server.send_message.side_effect = None
    assert await larma("R", tenant_id="t-1", vad="v", varfor="v", nyckel="k") is True


# -- 3. Larmet får aldrig fälla det det larmar om -------------------------


@pytest.mark.anyio
@pytest.mark.parametrize(
    "fel",
    [
        smtplib.SMTPAuthenticationError(535, b"fel app-losenord"),
        smtplib.SMTPServerDisconnected("natet dog"),
        smtplib.SMTPRecipientsRefused({}),
        TimeoutError("Gmail svarade inte"),
        OSError("ingen route till host"),
        ValueError("nagot helt oväntat"),
    ],
)
async def test_ett_smtp_fel_kastar_aldrig(konfigurerad, smtp, fel):
    _, server = smtp
    server.send_message.side_effect = fel

    assert await larma("R", tenant_id="t-1", vad="v", varfor="v", nyckel="k") is False


@pytest.mark.anyio
async def test_ett_fel_redan_vid_anslutningen_kastar_aldrig(konfigurerad):
    with patch("smtplib.SMTP", side_effect=OSError("kunde inte ansluta")):
        assert await larma("R", tenant_id="t-1", vad="v", varfor="v", nyckel="k") is False


@pytest.mark.anyio
async def test_osatt_konfiguration_ar_tyst_och_ofarlig(monkeypatch):
    monkeypatch.setenv("INTERNLARM_SMTP_ANVANDARE", "")
    monkeypatch.setenv("INTERNLARM_SMTP_LOSENORD", "")
    get_settings.cache_clear()

    assert har_konfiguration() is False
    with patch("smtplib.SMTP") as fabrik:
        assert await larma("R", tenant_id="t-1", vad="v", varfor="v", nyckel="k") is False
        fabrik.assert_not_called()


@pytest.mark.anyio
async def test_halvsatt_konfiguration_skickar_inte(monkeypatch):
    """Användare utan lösenord är inte halvt konfigurerat, det är
    okonfigurerat — och ett inloggningsförsök utan lösenord är bara en
    misslyckad autentisering mot Google."""
    monkeypatch.setenv("INTERNLARM_SMTP_ANVANDARE", "snajpsupport@gmail.com")
    monkeypatch.setenv("INTERNLARM_SMTP_LOSENORD", "")
    get_settings.cache_clear()

    assert har_konfiguration() is False
    assert await larma("R", tenant_id="t-1", vad="v", varfor="v", nyckel="k") is False


@pytest.mark.anyio
async def test_ett_hangande_smtp_slapper_efter_tidstaket(konfigurerad, monkeypatch):
    """Taket är hela skälet till att larmet inte kan sakta ner en eskalering.

    Tiden kortas ned i testet — poängen är att `asyncio.wait_for` faktiskt
    omsluter sändningen, inte hur många sekunder den väntar.
    """
    import asyncio

    monkeypatch.setattr(internlarm, "_TIDSTAK_SEKUNDER", 0.05)

    async def aldrig_klar(*a, **kw):
        await asyncio.sleep(5)

    with patch.object(internlarm.asyncio, "to_thread", new=AsyncMock(side_effect=aldrig_klar)):
        assert await larma("R", tenant_id="t-1", vad="v", varfor="v", nyckel="k") is False


# -- 4. SMTP-sessionen ser ut som Gmail kräver ----------------------------


@pytest.mark.anyio
async def test_sessionen_kor_starttls_och_loggar_in(konfigurerad, smtp):
    fabrik, server = smtp
    await larma("R", tenant_id="t-1", vad="v", varfor="v", nyckel="k")

    fabrik.assert_called_once_with(
        internlarm.SMTP_VARD, internlarm.SMTP_PORT, timeout=internlarm._TIDSTAK_SEKUNDER
    )
    server.starttls.assert_called_once()
    server.login.assert_called_once_with("snajpsupport@gmail.com", "app-losenord-16-tecken")


# -- Larmet, inkopplat i de riktiga agenterna -----------------------------
#
# Testerna ovanför prövar modulen. De här prövar KOPPLINGEN: att larmet går
# en gång per eskaleringshändelse i det faktiska supportflödet, och att ett
# SMTP-fel aldrig får en kundvänd förfrågan att kasta.


@pytest.fixture
def _fake_key(monkeypatch):
    from app.config import get_settings

    monkeypatch.setenv("LLM_PROVIDER", "deepseek")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key-not-a-real-credential-000000")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.mark.anyio
async def test_ett_supportarende_larmar_en_gang_inte_en_gang_per_meddelande(
    konfigurerad, smtp, _fake_key
):
    """Kravet, i det riktiga flödet.

    Varje meddelande i chatten öppnar ett EGET ärende, så utan dedupen hade en
    pågående, redan överlämnad tråd larmat en gång per replik. Kunden skriver
    tre gånger, alla tre eskalerar — en notis.
    """
    from tests.agent.test_support_agent_wiring import _FakeLLM, _run
    from app.storage.memory import MemoryStorage

    _, server = smtp
    storage = MemoryStorage()
    llm = _FakeLLM(overrides={"cs:ticket-triage": {"sentiment": 0.05}})

    for meddelande in ("Det här är oacceptabelt!", "Har ni läst mitt mejl?", "Hallå?"):
        resultat = await _run(storage, llm, message=meddelande)
        assert resultat["escalated"] is True, "Testet mäter fel sak: ärendet eskalerade inte."

    assert server.send_message.call_count == 1, (
        f"{server.send_message.call_count} notiser för ett och samma ärende."
    )


@pytest.mark.anyio
async def test_tva_olika_kunder_larmar_var_sin_gang(konfigurerad, smtp, _fake_key):
    """Dedupen får inte bli så bred att den tystar en annan kunds ärende."""
    from unittest.mock import AsyncMock as _AsyncMock

    from tests.agent.test_support_agent_wiring import TENANT, _FakeLLM
    from app.agent.support_agent import run_support_agent
    from app.storage.memory import MemoryStorage

    _, server = smtp
    storage = MemoryStorage()
    llm = _FakeLLM(overrides={"cs:ticket-triage": {"sentiment": 0.05}})

    for adress in ("en@example.com", "annan@example.com"):
        with patch("app.agent.step_runner.get_llm_client", return_value=llm), patch(
            "app.agent.support_agent.classify_cancellation_risk",
            new=_AsyncMock(return_value=(0.0, 0.0)),
        ):
            await run_support_agent(
                storage,
                TENANT,
                message="Det här är oacceptabelt!",
                subject="",
                channel="web",
                customer_email=adress,
                customer_name="Test",
                attachments=[],
            )

    assert server.send_message.call_count == 2


@pytest.mark.anyio
async def test_ett_smtp_fel_far_inte_supportsvaret_att_kasta(konfigurerad, smtp, _fake_key):
    """Den viktigaste raden i hela filen.

    Ett ärende som eskalerar är redan ett ärende där något gått fel för
    kunden. Att svaret också uteblir för att Gmail hade en dålig dag vore att
    göra ett problem till två.
    """
    from tests.agent.test_support_agent_wiring import _FakeLLM, _run
    from app.storage.memory import MemoryStorage

    _, server = smtp
    server.send_message.side_effect = smtplib.SMTPAuthenticationError(535, b"fel losenord")

    storage = MemoryStorage()
    llm = _FakeLLM(overrides={"cs:ticket-triage": {"sentiment": 0.05}})
    resultat = await _run(storage, llm, message="Det här är oacceptabelt!")

    assert resultat["reply"], "Kunden fick inget svar när larmet föll."
    assert resultat["escalated"] is True

    # Och ärendet har rätt status i databasen, oavsett vad mejlet gjorde.
    arende = await storage.get_ticket("00000000-0000-4000-a000-000000000001", resultat["ticket_id"])
    assert arende["status"] == "escalated"


@pytest.mark.anyio
async def test_ett_smtp_fel_far_inte_en_leads_overlamning_att_kasta(konfigurerad, smtp):
    from app.agent.leads_context import OutreachContext
    from app.agent.leads_tools import _request_human_handoff_impl
    from app.storage.memory import MemoryStorage

    _, server = smtp
    server.send_message.side_effect = OSError("natet dog")

    context = OutreachContext(
        storage=MemoryStorage(), tenant_id="t-1", thread_id="trad-1", prospect_email="p@example.com"
    )
    svar = await _request_human_handoff_impl(context, "Grindningen hittade ostödda påståenden.")

    assert context.escalated is True
    assert "escalated" in svar


@pytest.mark.anyio
async def test_en_leads_trad_larmar_en_gang_aven_med_flera_overlamningar(konfigurerad, smtp):
    """Modellen kan anropa verktyget flera gånger, och kodvägarna i
    run_outreach_draft kan följa på varandra. Det är EN överlämning."""
    from app.agent.leads_context import OutreachContext
    from app.agent.leads_tools import _request_human_handoff_impl
    from app.storage.memory import MemoryStorage

    _, server = smtp
    context = OutreachContext(
        storage=MemoryStorage(), tenant_id="t-1", thread_id="trad-1", prospect_email="p@example.com"
    )
    await _request_human_handoff_impl(context, "Första skälet.")
    await _request_human_handoff_impl(context, "Andra skälet.")

    assert server.send_message.call_count == 1


@pytest.mark.anyio
async def test_larmet_bar_inte_prospektets_mejladress(konfigurerad, smtp):
    """Adressen är personuppgift om en utomstående. Tråd-id:t pekar ut samma
    sak för den som ska agera."""
    from app.agent.leads_context import OutreachContext
    from app.agent.leads_tools import _request_human_handoff_impl
    from app.storage.memory import MemoryStorage

    _, server = smtp
    context = OutreachContext(
        storage=MemoryStorage(),
        tenant_id="t-1",
        thread_id="trad-1",
        prospect_email="hemlig@example.com",
    )
    await _request_human_handoff_impl(context, "Skäl.")

    text = _skickade(server)[0].get_content()
    assert "hemlig@example.com" not in text
    assert "trad-1" in text


@pytest.mark.anyio
async def test_en_oforandrad_trasig_period_larmar_bara_en_gang(konfigurerad, smtp):
    """Periodrapporten hämtas varje gång någon öppnar vyn eller frågar
    chatten. Utan bristerna i nyckeln hade det blivit ett mejl per sidladdning."""
    from datetime import date
    from decimal import Decimal

    from app.bookkeeping.period import berakna_period
    from app.storage.memory import MemoryStorage

    _, server = smtp
    storage = MemoryStorage()
    # Ett underlag utan momssats => verifieringsgrinden fäller perioden.
    await storage.create_bk_underlag(
        "t-1",
        sha256="sha-1",
        filnamn="kvitto.pdf",
        mimetyp="application/pdf",
        status="granska_manuellt",
        datum="2026-08-05",
        motpart="Circle K",
        brutto=Decimal("500.00"),
        momssats=None,
        riktning="kostnad",
        kategori="drivmedel",
    )

    for _ in range(3):
        rapport = await berakna_period(storage, "t-1", date(2026, 8, 1), date(2026, 8, 31))

    assert rapport["status"] == "granska_manuellt", "Testet mäter fel sak: perioden gick ihop."
    assert server.send_message.call_count == 1
