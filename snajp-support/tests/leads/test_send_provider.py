"""Sändvägens val och SmtpMailers kontrakt.

Valet är en säkerhetsordning (torrkörning > SMTP > logg) och kontraktet är
att 'sent' aldrig får vara en lögn: SmtpMailer kastar vid fel, och bara den
har `levererar = True`. Testerna kör mot en fejkad smtplib — ingen av dem
öppnar en socket.
"""

from __future__ import annotations

import smtplib

import pytest

from app.config import Settings
from app.leads import send_provider as modul
from app.leads.send_provider import (
    BlockeradSmtpPort,
    DryRunMailer,
    LoggingSendProvider,
    ResendMailer,
    SmtpMailer,
    get_send_provider,
)

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend():
    return "asyncio"


def _settings(**kwargs) -> Settings:
    return Settings(_env_file=None, **kwargs)


SMTP_KOMPLETT = dict(
    smtp_host="smtp.example.com",
    smtp_user="utskick@example.com",
    smtp_password="app-losenord",
)


# -- Valet ------------------------------------------------------------------


def test_default_ar_logging(monkeypatch):
    monkeypatch.delenv("SNAJP_OUTBOX_DIR", raising=False)
    provider = get_send_provider(_settings())
    assert isinstance(provider, LoggingSendProvider)
    assert provider.levererar is False


def test_komplett_smtp_ger_smtpmailer(monkeypatch):
    monkeypatch.delenv("SNAJP_OUTBOX_DIR", raising=False)
    provider = get_send_provider(_settings(**SMTP_KOMPLETT))
    assert isinstance(provider, SmtpMailer)
    assert provider.levererar is True
    # Tom smtp_from faller tillbaka på användaren.
    assert provider.avsandare == "utskick@example.com"


def test_halvsatt_smtp_ger_logging(monkeypatch):
    """En av tre variabler är inte en sändväg — och får inte se ut som en."""
    monkeypatch.delenv("SNAJP_OUTBOX_DIR", raising=False)
    provider = get_send_provider(_settings(smtp_host="smtp.example.com"))
    assert isinstance(provider, LoggingSendProvider)


def test_torrkorningen_vinner_over_komplett_smtp(monkeypatch, tmp_path):
    """Kollisionens värsta utfall ska vara en .eml-fil för mycket, aldrig ett
    riktigt mejl för mycket."""
    monkeypatch.setenv("SNAJP_OUTBOX_DIR", str(tmp_path))
    provider = get_send_provider(_settings(**SMTP_KOMPLETT))
    assert isinstance(provider, DryRunMailer)
    assert provider.levererar is False


def test_egen_avsandare_och_namn(monkeypatch):
    monkeypatch.delenv("SNAJP_OUTBOX_DIR", raising=False)
    provider = get_send_provider(
        _settings(**SMTP_KOMPLETT, smtp_from="hej@snajp.se", smtp_from_name="Snajp")
    )
    assert isinstance(provider, SmtpMailer)
    assert provider.avsandare == "hej@snajp.se"
    assert provider.avsandarnamn == "Snajp"


# -- SmtpMailer -------------------------------------------------------------


class _FejkServer:
    """Registrerar SMTP-sessionen i stället för att öppna en socket."""

    instanser: list["_FejkServer"] = []

    def __init__(self, host, port, timeout=None):
        self.host, self.port, self.timeout = host, port, timeout
        self.starttls_kord = False
        self.inloggad: tuple[str, str] | None = None
        self.skickade: list = []
        _FejkServer.instanser.append(self)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def starttls(self):
        self.starttls_kord = True

    def login(self, user, password):
        self.inloggad = (user, password)

    def send_message(self, meddelande):
        self.skickade.append(meddelande)


@pytest.fixture(autouse=True)
def _fejka_smtplib(monkeypatch):
    _FejkServer.instanser.clear()
    monkeypatch.setattr(smtplib, "SMTP", _FejkServer)
    monkeypatch.setattr(smtplib, "SMTP_SSL", _FejkServer)


def _mailer(**overrides) -> SmtpMailer:
    varden = dict(
        host="smtp.example.com", port=587, user="utskick@example.com",
        password="hemligt", avsandare="hej@snajp.se", avsandarnamn="Snajp",
    )
    varden.update(overrides)
    return SmtpMailer(**varden)


async def test_starttls_login_och_headers():
    await _mailer().send(to="kund@example.com", subject="Hej", body="Brödtext.")
    server = _FejkServer.instanser[0]
    assert server.starttls_kord is True
    assert server.inloggad == ("utskick@example.com", "hemligt")
    [meddelande] = server.skickade
    assert meddelande["To"] == "kund@example.com"
    assert meddelande["Subject"] == "Hej"
    assert "Snajp" in meddelande["From"] and "hej@snajp.se" in meddelande["From"]
    assert meddelande.get_content().strip() == "Brödtext."


async def test_port_465_hoppar_over_starttls():
    """Implicit TLS: starttls() mot 465 hänger sig i stället för att fela."""
    await _mailer(port=465).send(to="kund@example.com", subject="x", body="y")
    assert _FejkServer.instanser[0].starttls_kord is False


async def test_ogiltig_mottagare_stoppas_fore_smtp():
    """scheduler.py:s fallback-adress 'okänd' ska stoppas synligt här, inte
    bli ett kryptiskt 501 från servern."""
    with pytest.raises(ValueError):
        await _mailer().send(to="okänd", subject="x", body="y")
    assert _FejkServer.instanser == []


async def test_smtpfel_kastas_vidare(monkeypatch):
    """Kontraktet: anroparen markerar 'sent' EFTER ett lyckat anrop, så ett
    fel måste nå anroparen — inte sväljas."""

    def spricker(*args, **kwargs):
        raise smtplib.SMTPServerDisconnected("borta")

    monkeypatch.setattr(smtplib, "SMTP", spricker)
    with pytest.raises(smtplib.SMTPServerDisconnected):
        await _mailer().send(to="kund@example.com", subject="x", body="y")


# -- Resend (HTTPS) ---------------------------------------------------------


def test_resend_nyckel_vinner_over_smtp(monkeypatch):
    """Den som satt en Resend-nyckel har gjort det för att SMTP är blockerat.
    En kvarglömd SMTP-konfiguration får inte skicka oss tillbaka i väggen."""
    monkeypatch.delenv("SNAJP_OUTBOX_DIR", raising=False)
    provider = get_send_provider(_settings(**SMTP_KOMPLETT, resend_api_key="re_x"))
    assert isinstance(provider, ResendMailer)
    assert provider.levererar is True


def test_email_provider_smtp_tvingar_smtp(monkeypatch):
    monkeypatch.delenv("SNAJP_OUTBOX_DIR", raising=False)
    provider = get_send_provider(
        _settings(**SMTP_KOMPLETT, resend_api_key="re_x", email_provider="smtp")
    )
    assert isinstance(provider, SmtpMailer)


def test_resend_utan_nyckel_skickar_inget(monkeypatch):
    monkeypatch.delenv("SNAJP_OUTBOX_DIR", raising=False)
    provider = get_send_provider(_settings(email_provider="resend"))
    assert isinstance(provider, LoggingSendProvider)


def test_torrkorningen_vinner_over_resend(monkeypatch, tmp_path):
    monkeypatch.setenv("SNAJP_OUTBOX_DIR", str(tmp_path))
    assert isinstance(get_send_provider(_settings(resend_api_key="re_x")), DryRunMailer)


async def test_blockerad_port_ger_egen_typ(monkeypatch):
    """Errno 101 är plattformens portspärr, inte ett fel i uppgifterna —
    och åtgärden är att byta kanal, inte att byta lösenord."""

    def blockerad(*args, **kwargs):
        raise OSError(101, "Network is unreachable")

    monkeypatch.setattr(smtplib, "SMTP", blockerad)
    with pytest.raises(BlockeradSmtpPort) as fangad:
        await _mailer().send(to="kund@example.com", subject="x", body="y")
    assert "RESEND_API_KEY" in str(fangad.value)


async def test_resend_skickar_och_kastar_vid_fel(monkeypatch):
    skickat = {}

    class _Svar:
        def __init__(self, kod): self.status_code, self.text = kod, "{}"

    class _Klient:
        def __init__(self, **kw): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *a): return False
        async def post(self, url, headers=None, json=None):
            skickat.update({"url": url, "headers": headers, "json": json})
            return _Svar(skickat.get("_kod", 200))

    import httpx
    monkeypatch.setattr(httpx, "AsyncClient", _Klient)

    m = ResendMailer(api_key="re_hemlig", avsandare="hej@snajp.se", avsandarnamn="Snajp")
    await m.send(to="kund@example.com", subject="Hej", body="Text")
    assert skickat["json"]["to"] == ["kund@example.com"]
    assert skickat["json"]["from"] == "Snajp <hej@snajp.se>"
    assert skickat["headers"]["Authorization"].startswith("Bearer ")

    skickat["_kod"] = 422
    with pytest.raises(RuntimeError):
        await m.send(to="kund@example.com", subject="Hej", body="Text")


async def test_resend_avvisar_ogiltig_mottagare():
    with pytest.raises(ValueError):
        await ResendMailer(api_key="re_x", avsandare="hej@snajp.se").send(
            to="okänd", subject="x", body="y"
        )
