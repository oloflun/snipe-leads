"""Självbetjänad inkorgskoppling + snabb synk (migration 077).

Två kontrakt prövas:

1. **Kopplingen**: adressens domän ger värd, inloggningen provas FÖRE
   sparande, lösenordet lagras Fernet-krypterat och läcker aldrig i svar
   eller lagring i klartext.
2. **Synken**: /api/inbox/sync svarar direkt (hämta + skriv in) och
   klassificerar i bakgrunden — det var den synkrona LLM-bearbetningen som
   sprängde proxyns tidsbudget och gav "Assistenten har svårt att nå sin
   motor" i kundens UI.

IMAP fejkas på modulnivå: inga nätverksanrop.
"""

import pytest
from httpx import ASGITransport, AsyncClient

from app.config import get_settings
from app.email_pipeline import poller
from app.email_pipeline.connectors import imap as imap_connector
from app.email_pipeline.models import InboundEmail
from app.main import app

settings = get_settings()
DEMO = {"X-API-Key": settings.snajp_demo_api_key}


@pytest.fixture
def anyio_backend():
    return "asyncio"


def _client():
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


@pytest.fixture
def imap_fejk(monkeypatch):
    """Godkänd inloggning + ett oläst mail per hämtning."""

    async def ok_inloggning(host, user, password):
        ok_inloggning.anrop.append((host, user, password))
        return None

    ok_inloggning.anrop = []

    async def ett_mail(host, user, password, folder="INBOX", **_):
        ett_mail.anrop.append((host, user, password))
        return (
            [
                InboundEmail(
                    provider="imap",
                    provider_message_id=f"riktigt-{len(ett_mail.anrop)}",
                    from_email="kund@exempel.se",
                    from_name="Kajsa Kund",
                    subject="Var är min beställning?",
                    body_text="Hej! Beställde i förra veckan och undrar var paketet är.",
                )
            ],
            None,
        )

    ett_mail.anrop = []

    monkeypatch.setattr(imap_connector, "prova_inloggning", ok_inloggning)
    monkeypatch.setattr(poller.imap, "fetch_new", ett_mail)
    return ok_inloggning, ett_mail


@pytest.mark.anyio
async def test_koppla_synka_och_koppla_ur(imap_fejk):
    ok_inloggning, ett_mail = imap_fejk
    async with app.router.lifespan_context(app):
        async with _client() as client:
            # Koppla: gmail-domänen ger värden, ingen imap_host behövs.
            svar = await client.post(
                "/api/inbox/mailboxes",
                headers=DEMO,
                json={"address": "Kajsa.Kund@GMAIL.com", "app_losenord": "abcd efgh ijkl mnop"},
            )
            assert svar.status_code == 200, svar.text
            inkorg = svar.json()["mailbox"]
            assert inkorg["address"] == "kajsa.kund@gmail.com"
            assert inkorg["provider"] == "gmail"
            assert inkorg["host"] == "imap.gmail.com"
            # Inloggningen provades mot rätt värd, med lösenordet.
            assert ok_inloggning.anrop == [("imap.gmail.com", "kajsa.kund@gmail.com", "abcd efgh ijkl mnop")]

            # Lagringen bär ALDRIG klartext, och API-svaret bär inget lösenord.
            storage = app.state.storage
            rader = [
                m
                for t in await storage.list_tenants()
                for m in await storage.list_mailboxes(t["id"])
                if m["address"] == "kajsa.kund@gmail.com"
            ]
            assert rader and rader[0]["secret_enc"]
            assert "abcd efgh ijkl mnop" not in str(rader[0]["secret_enc"])
            assert "losenord" not in svar.text and "abcd" not in svar.text

            # GET säger att den går att synka — utan env-variabel.
            lista = (await client.get("/api/inbox/mailboxes", headers=DEMO)).json()
            assert lista["kan_synka"] is True
            assert lista["mailboxes"][0]["kan_synka"] is True
            assert "secret_enc" not in str(lista)

            # Synka: svarar direkt med processing-flaggan; mailet ligger i
            # inkorgen och är klassificerat när bakgrundsuppgiften kört.
            synk = await client.post("/api/inbox/sync", headers=DEMO)
            assert synk.status_code == 200, synk.text
            kropp = synk.json()
            assert kropp["connected"] is True
            assert kropp["fetched"] == 1
            assert kropp["processing"] is True
            assert not kropp["error"]
            # Hämtningen använde det DEKRYPTERADE lösenordet.
            assert ett_mail.anrop[-1] == ("imap.gmail.com", "kajsa.kund@gmail.com", "abcd efgh ijkl mnop")

            inbox = (await client.get("/api/inbox", headers=DEMO)).json()["emails"]
            riktiga = [e for e in inbox if e["from_email"] == "kund@exempel.se"]
            assert riktiga, "det hämtade mailet ska synas i inkorgen"
            # Bakgrundsklassificeringen har hunnit köra i ASGI-transporten.
            assert riktiga[0]["status"] != "new"

            # Koppla ur: raden försvinner och synken säger "inget kopplat".
            bort = await client.delete(f"/api/inbox/mailboxes/{inkorg['id']}", headers=DEMO)
            assert bort.status_code == 200
            efter = await client.post("/api/inbox/sync", headers=DEMO)
            assert efter.json()["connected"] is False


@pytest.mark.anyio
async def test_fel_losenord_sparar_ingenting(monkeypatch):
    async def nekad(host, user, password):
        return "Inloggningen nekades. Kontrollera app-lösenordet."

    monkeypatch.setattr(imap_connector, "prova_inloggning", nekad)
    async with app.router.lifespan_context(app):
        async with _client() as client:
            svar = await client.post(
                "/api/inbox/mailboxes",
                headers=DEMO,
                json={"address": "kajsa@icloud.com", "app_losenord": "fel-losen"},
            )
            assert svar.status_code == 422
            assert "nekades" in svar.json()["detail"]
            lista = (await client.get("/api/inbox/mailboxes", headers=DEMO)).json()
            assert lista["mailboxes"] == []


@pytest.mark.anyio
async def test_okand_doman_kraver_imap_vard(imap_fejk):
    async with app.router.lifespan_context(app):
        async with _client() as client:
            utan = await client.post(
                "/api/inbox/mailboxes",
                headers=DEMO,
                json={"address": "info@eget-bolag.se", "app_losenord": "hemligt-losen"},
            )
            assert utan.status_code == 400

            med = await client.post(
                "/api/inbox/mailboxes",
                headers=DEMO,
                json={
                    "address": "info@eget-bolag.se",
                    "app_losenord": "hemligt-losen",
                    "imap_host": "mail.eget-bolag.se",
                },
            )
            assert med.status_code == 200
            assert med.json()["mailbox"]["provider"] == "imap"
            assert med.json()["mailbox"]["host"] == "mail.eget-bolag.se"


def test_doman_uppslag_kanner_de_stora_leverantorerna():
    assert poller.imap_for_adress("a@gmail.com") == ("gmail", "imap.gmail.com")
    assert poller.imap_for_adress("a@Hotmail.com") == ("outlook", "outlook.office365.com")
    assert poller.imap_for_adress("a@icloud.com") == ("imap", "imap.mail.me.com")
    assert poller.imap_for_adress("a@eget-bolag.se") is None


@pytest.mark.anyio
async def test_isolering_annan_tenant_ser_inte_inkorgen(imap_fejk):
    async with app.router.lifespan_context(app):
        async with _client() as client:
            master = {"X-API-Key": settings.snajp_master_api_key}
            skapad = await client.post(
                "/api/keys", headers=master, json={"tenant_name": "Grannbolaget AB"}
            )
            granne = {"X-API-Key": skapad.json()["api_key"]}

            await client.post(
                "/api/inbox/mailboxes",
                headers=DEMO,
                json={"address": "kajsa@gmail.com", "app_losenord": "abcd efgh ijkl mnop"},
            )
            inkorg_id = (await client.get("/api/inbox/mailboxes", headers=DEMO)).json()[
                "mailboxes"
            ][0]["id"]

            assert (await client.get("/api/inbox/mailboxes", headers=granne)).json()[
                "mailboxes"
            ] == []
            stulen = await client.delete(f"/api/inbox/mailboxes/{inkorg_id}", headers=granne)
            assert stulen.status_code == 404
