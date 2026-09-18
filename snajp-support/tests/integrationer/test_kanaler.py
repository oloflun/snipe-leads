"""Kanalerna: signaturer, tolkning, webhookflödet och leverans av medarbetarsvar.

Ligger bredvid integrationstesterna för att dela det hermetiska nätet
(conftest.py): kanalernas utgående anrop går genom samma nätvakt.
"""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import time

import httpx
import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.api import kanaler as kanal_api
from app.config import get_settings
from app.kanaler import ADAPTRAR, KanalFel, lagring, leverans, mottagning
from app.kanaler.bas import dela_text
from app.storage.memory import MemoryStorage

TENANT = "00000000-0000-4000-a000-000000000001"
NYCKEL = {"X-API-Key": get_settings().snajp_demo_api_key}
META_HEMLIGHETER = {"access_token": "EAAG-token-123456", "app_secret": "app-hemlighet-123", "verify_token": "min-verifiering"}


def _meta_signatur(kropp: bytes, hemlighet: str = "app-hemlighet-123") -> str:
    return "sha256=" + hmac.new(hemlighet.encode(), kropp, hashlib.sha256).hexdigest()


def _whatsapp_payload(text: str = "Var är min order?", mid: str = "wamid.1", pnid: str = "PNID1") -> dict:
    return {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "id": "WABA",
                "changes": [
                    {
                        "field": "messages",
                        "value": {
                            "messaging_product": "whatsapp",
                            "metadata": {"display_phone_number": "46700000000", "phone_number_id": pnid},
                            "contacts": [{"profile": {"name": "Kim"}, "wa_id": "46701234567"}],
                            "messages": [
                                {"from": "46701234567", "id": mid, "timestamp": "1", "type": "text", "text": {"body": text}}
                            ],
                        },
                    }
                ],
            }
        ],
    }


# -- Adaptrar, utan nät ---------------------------------------------------------


def test_whatsapp_tolkar_text_och_ignorerar_andra_nummer_och_kvitton():
    wa = ADAPTRAR["whatsapp"]
    anslutning = {"id": "a", "extern_id": "PNID1", "konfig": {}}
    inkommande = wa.tolka(_whatsapp_payload(), anslutning)
    assert len(inkommande) == 1
    m = inkommande[0]
    assert (m.text, m.telefon, m.visningsnamn, m.extern_meddelande_id) == (
        "Var är min order?", "+46701234567", "Kim", "wamid.1"
    )
    assert wa.tolka(_whatsapp_payload(pnid="ANNAT"), anslutning) == []
    kvitto = _whatsapp_payload()
    kvitto["entry"][0]["changes"][0]["value"] = {"metadata": {"phone_number_id": "PNID1"}, "statuses": [{"id": "x"}]}
    assert wa.tolka(kvitto, anslutning) == []


def test_whatsapp_bild_blir_en_rad_om_vad_som_kom():
    payload = _whatsapp_payload()
    payload["entry"][0]["changes"][0]["value"]["messages"][0] = {
        "from": "46701234567", "id": "wamid.2", "type": "image", "image": {"id": "m1", "caption": "trasig"}
    }
    m = ADAPTRAR["whatsapp"].tolka(payload, {"id": "a", "extern_id": "PNID1"})[0]
    assert m.text == "[Kunden skickade en bild] trasig"


def test_meta_prenumeration_och_signatur():
    wa = ADAPTRAR["whatsapp"]
    params = {"hub.mode": "subscribe", "hub.verify_token": "min-verifiering", "hub.challenge": "1158201444"}
    assert wa.verifiera_prenumeration(params, META_HEMLIGHETER) == "1158201444"
    assert wa.verifiera_prenumeration({**params, "hub.verify_token": "fel"}, META_HEMLIGHETER) is None


@pytest.mark.anyio
async def test_meta_signatur_maste_stamma():
    wa = ADAPTRAR["whatsapp"]
    kropp = json.dumps(_whatsapp_payload()).encode()
    assert await wa.verifiera(kropp, {"X-Hub-Signature-256": _meta_signatur(kropp)}, META_HEMLIGHETER, {})
    assert not await wa.verifiera(kropp + b" ", {"X-Hub-Signature-256": _meta_signatur(kropp)}, META_HEMLIGHETER, {})
    assert not await wa.verifiera(kropp, {}, META_HEMLIGHETER, {})


def test_messenger_ignorerar_eko_och_tar_postback():
    ms = ADAPTRAR["messenger"]
    anslutning = {"id": "a", "extern_id": "PAGE1"}
    payload = {
        "object": "page",
        "entry": [
            {
                "id": "PAGE1",
                "messaging": [
                    {"sender": {"id": "PSID1"}, "recipient": {"id": "PAGE1"}, "message": {"mid": "m1", "text": "Hej"}},
                    {"sender": {"id": "PAGE1"}, "recipient": {"id": "PSID1"}, "message": {"mid": "m2", "text": "eko", "is_echo": True}},
                    {"sender": {"id": "PSID1"}, "recipient": {"id": "PAGE1"}, "postback": {"mid": "m3", "title": "Spåra order"}},
                    {"sender": {"id": "PSID1"}, "delivery": {"mids": ["m1"]}},
                ],
            }
        ],
    }
    assert [(m.extern_meddelande_id, m.text) for m in ms.tolka(payload, anslutning)] == [
        ("m1", "Hej"), ("m3", "Spåra order")
    ]


def _slack_signatur(kropp: bytes, ts: str, hemlighet: str = "slack-hemlighet") -> str:
    return "v0=" + hmac.new(hemlighet.encode(), f"v0:{ts}:".encode() + kropp, hashlib.sha256).hexdigest()


@pytest.mark.anyio
async def test_slack_signatur_med_tidsfonster():
    sl = ADAPTRAR["slack"]
    hemligheter = {"signing_secret": "slack-hemlighet", "bot_token": "xoxb-1"}
    kropp = b'{"type":"event_callback"}'
    nu = str(int(time.time()))
    ok = {"X-Slack-Request-Timestamp": nu, "X-Slack-Signature": _slack_signatur(kropp, nu)}
    assert await sl.verifiera(kropp, ok, hemligheter, {})
    gammal = str(int(time.time()) - 600)
    uppspelning = {"X-Slack-Request-Timestamp": gammal, "X-Slack-Signature": _slack_signatur(kropp, gammal)}
    assert not await sl.verifiera(kropp, uppspelning, hemligheter, {})


def test_slack_tolkar_dm_och_omnamnande_men_inte_botar():
    sl = ADAPTRAR["slack"]
    anslutning = {"id": "a", "extern_id": "T1"}

    def handelse(**event):
        return {"type": "event_callback", "team_id": "T1", "event_id": f"Ev{len(event)}", "event": event}

    dm = sl.tolka(handelse(type="message", channel_type="im", channel="D1", user="U1", text="Hej", ts="1.1"), anslutning)
    assert dm[0].adress == {"kanal": "D1"}
    omnamnande = sl.tolka(
        handelse(type="app_mention", channel="C1", user="U1", text="<@UBOT> var är min order?", ts="2.2"), anslutning
    )
    assert omnamnande[0].text == "var är min order?" and omnamnande[0].adress == {"kanal": "C1", "trad": "2.2"}
    assert sl.tolka(handelse(type="message", channel_type="im", channel="D1", bot_id="B1", text="x", ts="3"), anslutning) == []
    assert sl.tolka(handelse(type="message", channel_type="channel", channel="C1", user="U1", text="x", ts="4"), anslutning) == []
    assert sl.omedelbart_svar({"type": "url_verification", "challenge": "abc"}) == {"challenge": "abc"}


def test_teams_tolkar_och_tar_bort_omnamnanden():
    tm = ADAPTRAR["teams"]
    aktivitet = {
        "type": "message",
        "id": "act1",
        "serviceUrl": "https://smba.trafficmanager.net/emea/",
        "channelId": "msteams",
        "from": {"id": "29:x", "name": "Kim", "aadObjectId": "aad-1"},
        "conversation": {"id": "a:konv", "tenantId": "t1"},
        "text": "<at>Snajp</at> hej där",
    }
    m = tm.tolka(aktivitet, {"id": "a", "extern_id": "APP"})[0]
    assert (m.text, m.extern_anvandare, m.visningsnamn) == ("hej där", "aad-1", "Kim")
    assert m.adress["konversation"] == "a:konv"
    assert tm.tolka({**aktivitet, "type": "conversationUpdate"}, {"id": "a", "extern_id": "APP"}) == []


def test_teams_serviceurl_maste_vara_microsoft():
    from app.kanaler.teams import tjanste_url_tillaten

    assert tjanste_url_tillaten("https://smba.trafficmanager.net/emea/")
    assert not tjanste_url_tillaten("https://evil.example.com/")
    assert not tjanste_url_tillaten("http://smba.trafficmanager.net/")
    assert not tjanste_url_tillaten("https://trafficmanager.net.evil.com/")


@pytest.mark.anyio
async def test_teams_jwt_valideras_mot_microsofts_nycklar(svara):
    import jwt
    from cryptography.hazmat.primitives.asymmetric import rsa

    from app.kanaler import teams

    teams.tom_cache()
    privat = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    jwk = json.loads(jwt.algorithms.RSAAlgorithm.to_jwk(privat.public_key()))
    jwk.update({"kid": "nyckel1", "endorsements": ["msteams"]})

    def microsoft(request):
        if request.url.path.endswith("openidconfiguration"):
            return httpx.Response(200, json={"jwks_uri": "https://login.botframework.com/v1/.well-known/keys"})
        return httpx.Response(200, json={"keys": [jwk]})

    svara(microsoft)
    service_url = "https://smba.trafficmanager.net/emea/"

    def token(**over):
        ansprak = {
            "iss": "https://api.botframework.com", "aud": "APP-ID", "exp": int(time.time()) + 600,
            "serviceurl": service_url, **over,
        }
        return jwt.encode(ansprak, privat, algorithm="RS256", headers={"kid": "nyckel1"})

    aktivitet = json.dumps({"type": "message", "serviceUrl": service_url, "channelId": "msteams"}).encode()
    anslutning = {"extern_id": "APP-ID"}
    tm = ADAPTRAR["teams"]
    assert await tm.verifiera(aktivitet, {"Authorization": f"Bearer {token()}"}, {}, anslutning)
    assert not await tm.verifiera(aktivitet, {"Authorization": f"Bearer {token(aud='ANNAN')}"}, {}, anslutning)
    assert not await tm.verifiera(
        aktivitet, {"Authorization": f"Bearer {token(serviceurl='https://evil.example.com/')}"}, {}, anslutning
    )
    assert not await tm.verifiera(aktivitet, {}, {}, anslutning)
    teams.tom_cache()


def test_dela_text_vid_meningsgrans():
    text = "Första meningen är här. " * 100
    delar = dela_text(text, 200)
    assert all(len(d) <= 200 for d in delar)
    assert all(d.endswith(".") for d in delar)
    assert " ".join(delar).split() == text.split()


# -- Webhook -> agent -> svar, via API:t ------------------------------------------


@pytest.fixture
def app(monkeypatch):
    app = FastAPI()
    app.include_router(kanal_api.router)
    app.state.storage = MemoryStorage()
    return app


async def _skapa_whatsapp(klient) -> dict:
    svar = await klient.post(
        "/api/kanaler",
        json={"kanal": "whatsapp", "namn": "Kundtjänst", "extern_id": "PNID1", "hemligheter": META_HEMLIGHETER},
        headers=NYCKEL,
    )
    assert svar.status_code == 201, svar.text
    return svar.json()


async def _vanta_pa_bakgrunden():
    for _ in range(100):
        if not mottagning._pagaende:
            return
        await asyncio.sleep(0.01)
    raise AssertionError("bakgrundsjobbet blev aldrig klart")


@pytest.mark.anyio
async def test_hela_flodet_whatsapp(app, svara, monkeypatch):
    agentanrop: list[dict] = []

    async def falsk_agent(storage, tenant_id, **kw):
        agentanrop.append(kw)
        return {"reply": "Din order är skickad.", "step_log": [{"skill": "x"}]}

    monkeypatch.setattr("app.agent.support_agent.run_support_agent", falsk_agent)
    meta = svara(lambda r: httpx.Response(200, json={"messages": [{"id": "wamid.ut"}]}))

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as klient:
        anslutning = await _skapa_whatsapp(klient)
        assert "EAAG-token" not in json.dumps(anslutning)
        webhook = f"/api/kanaler/whatsapp/{TENANT}/{anslutning['id']}/webhook"

        verifiering = await klient.get(
            webhook, params={"hub.mode": "subscribe", "hub.verify_token": "min-verifiering", "hub.challenge": "42"}
        )
        assert verifiering.status_code == 200 and verifiering.text == "42"

        kropp = json.dumps(_whatsapp_payload()).encode()
        osignerad = await klient.post(webhook, content=kropp)
        assert osignerad.status_code == 401

        signerad = await klient.post(webhook, content=kropp, headers={"X-Hub-Signature-256": _meta_signatur(kropp)})
        assert signerad.status_code == 200
        await _vanta_pa_bakgrunden()

        # Meta skickar om samma webhook: inget andra svar.
        igen = await klient.post(webhook, content=kropp, headers={"X-Hub-Signature-256": _meta_signatur(kropp)})
        assert igen.status_code == 200
        await _vanta_pa_bakgrunden()

    assert len(agentanrop) == 1
    assert agentanrop[0]["channel"] == "whatsapp" and agentanrop[0]["kund_id"]
    assert len(meta) == 1
    utgaende = json.loads(meta[0].content)
    assert meta[0].url.path == "/v23.0/PNID1/messages"
    assert meta[0].headers["authorization"] == "Bearer EAAG-token-123456"
    assert utgaende["to"] == "46701234567" and utgaende["text"]["body"] == "Din order är skickad."

    # Kunden har telefonnumret hos oss och en kontakt för medarbetarsvar.
    kontakt = await lagring.hamta_kontakt(app.state.storage, TENANT, anslutning["id"], "46701234567")
    assert kontakt["customer_id"] == agentanrop[0]["kund_id"]


@pytest.mark.anyio
async def test_samma_kund_i_nasta_meddelande(app, svara, monkeypatch):
    kunder: list[str] = []

    async def falsk_agent(storage, tenant_id, **kw):
        kunder.append(kw["kund_id"])
        return {"reply": "", "step_log": []}  # tyst: en människa äger samtalet

    monkeypatch.setattr("app.agent.support_agent.run_support_agent", falsk_agent)
    meta = svara(lambda r: httpx.Response(200, json={}))
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as klient:
        anslutning = await _skapa_whatsapp(klient)
        webhook = f"/api/kanaler/whatsapp/{TENANT}/{anslutning['id']}/webhook"
        for mid in ("wamid.a", "wamid.b"):
            kropp = json.dumps(_whatsapp_payload(mid=mid)).encode()
            await klient.post(webhook, content=kropp, headers={"X-Hub-Signature-256": _meta_signatur(kropp)})
            await _vanta_pa_bakgrunden()
    assert len(kunder) == 2 and kunder[0] == kunder[1]
    assert meta == []  # tomt svar skickas aldrig


@pytest.mark.anyio
async def test_agentfel_ger_kort_arligt_svar_och_en_handelse(app, svara, monkeypatch):
    async def trasig_agent(storage, tenant_id, **kw):
        raise RuntimeError("modellen är nere")

    monkeypatch.setattr("app.agent.support_agent.run_support_agent", trasig_agent)
    meta = svara(lambda r: httpx.Response(200, json={}))
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as klient:
        anslutning = await _skapa_whatsapp(klient)
        kropp = json.dumps(_whatsapp_payload()).encode()
        await klient.post(
            f"/api/kanaler/whatsapp/{TENANT}/{anslutning['id']}/webhook",
            content=kropp, headers={"X-Hub-Signature-256": _meta_signatur(kropp)},
        )
        await _vanta_pa_bakgrunden()
    assert json.loads(meta[0].content)["text"]["body"] == mottagning.TEXT_TILLFALLIGT_FEL
    assert any(e["source"] == "kanal" for e in app.state.storage.platform_events)


@pytest.mark.anyio
async def test_slack_url_verification_och_fel_kanal_ger_404(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as klient:
        skapad = await klient.post(
            "/api/kanaler",
            json={"kanal": "slack", "extern_id": "T1", "hemligheter": {"bot_token": "xoxb-1", "signing_secret": "slack-hemlighet"}},
            headers=NYCKEL,
        )
        anslutning = skapad.json()
        kropp = json.dumps({"type": "url_verification", "challenge": "utmaning"}).encode()
        nu = str(int(time.time()))
        svar = await klient.post(
            f"/api/kanaler/slack/{TENANT}/{anslutning['id']}/webhook",
            content=kropp,
            headers={"X-Slack-Request-Timestamp": nu, "X-Slack-Signature": _slack_signatur(kropp, nu)},
        )
        assert svar.json() == {"challenge": "utmaning"}
        fel_kanal = await klient.post(f"/api/kanaler/whatsapp/{TENANT}/{anslutning['id']}/webhook", content=kropp)
        assert fel_kanal.status_code == 404
        skrap = await klient.post(f"/api/kanaler/slack/{TENANT}/inte-ett-id/webhook", content=kropp)
        assert skrap.status_code == 404


@pytest.mark.anyio
async def test_samma_nummer_kan_inte_anslutas_tva_ganger(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as klient:
        await _skapa_whatsapp(klient)
        igen = await klient.post(
            "/api/kanaler", json={"kanal": "whatsapp", "extern_id": "PNID1", "hemligheter": META_HEMLIGHETER},
            headers=NYCKEL,
        )
        assert igen.status_code == 409
        okand = await klient.post("/api/kanaler", json={"kanal": "fax", "extern_id": "1"}, headers=NYCKEL)
        assert okand.status_code == 422


@pytest.mark.anyio
async def test_prova_anslutning_mot_meta(app, svara):
    svara(lambda r: httpx.Response(200, json={"verified_name": "Butiken", "display_phone_number": "+46 70"}))
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as klient:
        anslutning = await _skapa_whatsapp(klient)
        prov = await klient.post(f"/api/kanaler/{anslutning['id']}/prova", headers=NYCKEL)
    assert prov.json()["ok"] is True and "Butiken" in prov.json()["besked"]


# -- Medarbetarsvar ut i kanalen ----------------------------------------------------


@pytest.mark.anyio
async def test_medarbetarsvar_levereras_i_kundens_kanal(svara):
    storage = MemoryStorage()
    anslutning = await lagring.skapa_anslutning(
        storage, TENANT, kanal="whatsapp", namn="", extern_id="PNID1", konfig={}, hemligheter=META_HEMLIGHETER
    )
    kund = await storage.find_or_create_customer(TENANT, email=None, phone="+46701234567", name="Kim")
    await lagring.spara_kontakt(
        storage, TENANT, anslutning_id=anslutning["id"], customer_id=kund["id"],
        extern_anvandare="46701234567", adress={"wa_id": "46701234567"}, visningsnamn="Kim",
    )
    meta = svara(lambda r: httpx.Response(200, json={}))
    assert await leverans.leverera(storage, TENANT, customer_id=kund["id"], kanal="whatsapp", text="Hej, Sara här.")
    assert json.loads(meta[0].content)["text"]["body"] == "Hej, Sara här."
    # Webbchatten hämtar själv — inget att leverera.
    assert await leverans.leverera(storage, TENANT, customer_id=kund["id"], kanal="web", text="x") is False


@pytest.mark.anyio
async def test_whatsapps_24_timmarsfonster_blir_ett_begripligt_fel(svara):
    storage = MemoryStorage()
    anslutning = await lagring.skapa_anslutning(
        storage, TENANT, kanal="whatsapp", namn="", extern_id="PNID1", konfig={}, hemligheter=META_HEMLIGHETER
    )
    await lagring.spara_kontakt(
        storage, TENANT, anslutning_id=anslutning["id"], customer_id="k1",
        extern_anvandare="46701234567", adress={"wa_id": "46701234567"}, visningsnamn=None,
    )
    svara(lambda r: httpx.Response(400, json={"error": {"code": 131047, "message": "Re-engagement message"}}))
    with pytest.raises(KanalFel, match="24 timmar"):
        await leverans.leverera(storage, TENANT, customer_id="k1", kanal="whatsapp", text="Hej")
