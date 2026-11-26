"""Händelseloggen, ändringsflödet, papperskorgen och webhooks ut (migration 162).

Leveransen prövas mot en mottagare i minnet: nätvakten ligger kvar utanpå, så
att adresskontrollen är densamma som i drift.
"""

from __future__ import annotations

import hashlib
import hmac
import json
from datetime import datetime, timedelta, timezone

import httpx
import pytest

from app.crm import lagring, webhooks
from app.integrationer import natvakt

from .conftest import ORGNR_A, ORGNR_B

V1 = "/api/crm/v1"
pytestmark = pytest.mark.anyio


@pytest.fixture(autouse=True)
def _rent():
    webhooks.nollstall()
    yield
    webhooks.nollstall()


class Mottagare:
    """Kundens server. Svarar med `status` och minns varje anrop."""

    def __init__(self) -> None:
        self.status = 200
        self.anrop: list[httpx.Request] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.anrop.append(request)
        return httpx.Response(self.status, json={"ok": True})


@pytest.fixture
def mottagare(monkeypatch) -> Mottagare:
    m = Mottagare()

    async def dns(vard: str, port: int) -> list[str]:
        return ["93.184.216.34"]

    monkeypatch.setattr(natvakt, "upplos", dns)
    monkeypatch.setattr(natvakt, "inre_transport", lambda: httpx.MockTransport(m))
    return m


# -- Händelser och ändringsflöde ---------------------------------------------


async def test_varje_skrivning_blir_en_handelse_i_flodet(buddy, annan):
    async with buddy.klient() as k:
        bolag = (await k.post(f"{V1}/companies", json={"name": "Bygg AB", "org_number": ORGNR_A})).json()
        await k.patch(f"{V1}/companies/{bolag['id']}", json={"phone": "08-123 456 78", "address": {"city": "Umeå"}})
        await k.delete(f"{V1}/companies/{bolag['id']}")
        await k.post(f"{V1}/companies/{bolag['id']}/restore")
        flode = (await k.get(f"{V1}/changes")).json()
        assert [(h["object"], h["type"]) for h in flode["data"]] == [
            ("company", "created"), ("company", "updated"), ("company", "deleted"), ("company", "restored")]
        andrad = flode["data"][1]
        assert sorted(andrad["fields"]) == ["address.city", "phone"] and andrad["id"] == bolag["id"]
        assert andrad["source"] == "api" and andrad["actor"].startswith("nyckel:")
        # Loggen bär fältens namn, aldrig värdena.
        assert "Umeå" not in json.dumps(flode) and "+468" not in json.dumps(flode)
        # Samma markör igen ger bara det som hänt sedan dess.
        assert (await k.get(f"{V1}/changes", params={"cursor": flode["next_cursor"]})).json() == {
            "data": [], "next_cursor": flode["next_cursor"]}
        await k.post(f"{V1}/people", json={"email": "anna@bygg.se"})
        nytt = (await k.get(f"{V1}/changes", params={"cursor": flode["next_cursor"]})).json()
        assert [(h["object"], h["type"]) for h in nytt["data"]] == [("person", "created")]
        assert len((await k.get(f"{V1}/changes", params={"object": "person"})).json()["data"]) == 1
        # Postens egen historik, nyast först.
        historik = (await k.get(f"{V1}/companies/{bolag['id']}/history")).json()["data"]
        assert [h["type"] for h in historik] == ["restored", "deleted", "updated", "created"]
    # Den andra kunden ser ingenting av det.
    async with annan.klient() as k:
        assert (await k.get(f"{V1}/changes")).json()["data"] == []
        assert (await k.get(f"{V1}/companies/{bolag['id']}/history")).status_code == 404


async def test_synken_loggar_per_post_och_en_tomd_post_lamnar_bara_sitt_id(buddy):
    async with buddy.klient() as k:
        await k.post(f"{V1}/connections", json={"name": "egen", "system": "generisk"})
        ut = (await k.post(f"{V1}/sync/companies", json={"connection": "egen", "items": [
            {"id": "1", "name": "Ett AB", "org_number": ORGNR_A}, {"id": "2", "name": "Två AB"}]})).json()
        await k.post(f"{V1}/sync/companies", json={"connection": "egen", "items": [
            {"id": "1", "name": "Ett AB", "org_number": ORGNR_A, "city": "Luleå"}, {"id": "2", "name": "Två AB"}]})
        flode = (await k.get(f"{V1}/changes")).json()["data"]
        assert [(h["type"], h["source"], h["actor"]) for h in flode] == [
            ("created", "synk", "anslutning:egen"), ("created", "synk", "anslutning:egen"),
            ("updated", "synk", "anslutning:egen")]
        assert flode[2]["fields"] == ["address.city"]
        await k.delete(f"{V1}/companies/{ut['items'][1]['id']}", params={"permanent": "true"})
        sist = (await k.get(f"{V1}/changes")).json()["data"][-1]
        assert (sist["type"], sist["id"], sist["fields"]) == ("purged", ut["items"][1]["id"], [])


# -- Sortering, papperskorg och krockens id ----------------------------------


async def test_senast_andrad_forst_med_sidindelning(buddy):
    async with buddy.klient() as k:
        for namn in ("Alfa AB", "Beta AB", "Gamma AB"):
            await k.post(f"{V1}/companies", json={"name": namn})
        forsta = (await k.get(f"{V1}/companies", params={"sort": "-updated", "limit": 2})).json()
        assert [b["name"] for b in forsta["data"]] == ["Gamma AB", "Beta AB"]
        andra = (await k.get(f"{V1}/companies", params={"sort": "-updated", "limit": 2,
                                                        "cursor": forsta["next_cursor"]})).json()
        assert [b["name"] for b in andra["data"]] == ["Alfa AB"] and andra["next_cursor"] is None
        assert [b["name"] for b in (await k.get(f"{V1}/companies", params={"sort": "updated"})).json()["data"]] == [
            "Alfa AB", "Beta AB", "Gamma AB"]
        assert (await k.get(f"{V1}/companies", params={"sort": "created"})).status_code == 422


async def test_papperskorgen_visar_det_som_gar_att_aterstalla(buddy, annan, storage):
    async with buddy.klient() as k:
        kvar = (await k.post(f"{V1}/companies", json={"name": "Kvar AB"})).json()
        forst = (await k.post(f"{V1}/companies", json={"name": "Raderad Först AB"})).json()
        sist = (await k.post(f"{V1}/companies", json={"name": "Raderad Sist AB"})).json()
        tomd = (await k.post(f"{V1}/companies", json={"name": "Tömd AB"})).json()
        for post in (forst, sist):
            await k.delete(f"{V1}/companies/{post['id']}")
        await k.delete(f"{V1}/companies/{tomd['id']}", params={"permanent": "true"})
        korg = (await k.get(f"{V1}/companies", params={"only_deleted": "true"})).json()["data"]
        assert [b["name"] for b in korg] == ["Raderad Sist AB", "Raderad Först AB"]
        raderad = lagring._tid(korg[0]["deleted_at"])
        assert lagring._tid(korg[0]["purge_at"]) == raderad + timedelta(days=30)
        # En levande post har ingen tömningsdag.
        assert (await k.get(f"{V1}/companies/{kvar['id']}")).json()["purge_at"] is None
        await k.post(f"{V1}/companies/{sist['id']}/restore")
        assert len((await k.get(f"{V1}/companies", params={"only_deleted": "true"})).json()["data"]) == 1
    async with annan.klient() as k:
        assert (await k.get(f"{V1}/companies", params={"only_deleted": "true"})).json()["data"] == []


async def test_en_krock_sager_vilken_post_som_redan_har_nyckeln(buddy):
    async with buddy.klient() as k:
        ett = (await k.post(f"{V1}/companies", json={"name": "Ett AB", "org_number": ORGNR_A})).json()
        tva = (await k.post(f"{V1}/companies", json={"name": "Två AB", "org_number": ORGNR_B})).json()
        svar = await k.patch(f"{V1}/companies/{tva['id']}", json={"org_number": ORGNR_A})
        assert svar.status_code == 409 and svar.json()["detail"]["conflicting_id"] == ett["id"]
        anna = (await k.post(f"{V1}/people", json={"email": "anna@ett.se"})).json()
        bo = (await k.post(f"{V1}/people", json={"email": "bo@ett.se"})).json()
        svar = await k.patch(f"{V1}/people/{bo['id']}", json={"email": "ANNA@ett.se"})
        assert svar.status_code == 409 and svar.json()["detail"]["conflicting_id"] == anna["id"]
        # Återställning där adressen hunnit tas av en annan.
        await k.delete(f"{V1}/people/{anna['id']}")
        ny = (await k.post(f"{V1}/people", json={"email": "anna@ett.se"})).json()
        svar = await k.post(f"{V1}/people/{anna['id']}/restore")
        assert svar.status_code == 409 and svar.json()["detail"]["conflicting_id"] == ny["id"]


async def test_synkens_felrader_bar_bolagets_namn_och_krockens_id(buddy):
    async with buddy.klient() as k:
        await k.post(f"{V1}/connections", json={"name": "egen", "system": "generisk"})
        ut = (await k.post(f"{V1}/sync/companies", json={"connection": "egen", "items": [
            {"id": "1", "name": "Ett AB", "org_number": ORGNR_A},
            {"id": "2", "name": "Två AB", "org_number": ORGNR_B},
            {"id": "3", "name": "Fel Telefon AB", "phone": "123"},
            {"id": "4", "name": "Fel Nummer AB", "org_number": "556036-0794"},
        ]})).json()
        ett_id = ut["items"][0]["id"]
        fel = {f["externt_id"]: f for f in ut["run"]["errors"]}
        assert fel["3"]["namn"] == "Fel Telefon AB" and fel["3"]["faltfel"][0]["kod"] == "telefon_saknar_landskod"
        # Det felaktiga organisationsnumret sparas aldrig: det kan vara ett personnummer.
        assert "varde" not in fel["4"]["faltfel"][0] and "0794" not in json.dumps(ut["run"]["errors"])
        # Källans post 2 byter till ett nummer som redan tillhör post 1.
        ut = (await k.post(f"{V1}/sync/companies", json={"connection": "egen", "items": [
            {"id": "2", "name": "Två AB", "org_number": ORGNR_A}]})).json()
        krock = ut["items"][0]
        assert krock["status"] == "conflict" and krock["reason"] == "orgnr_tillhor_annat_bolag"
        assert krock["conflicting_id"] == ett_id
        assert ut["run"]["errors"][0]["krockar_med"] == ett_id and ut["run"]["errors"][0]["namn"] == "Två AB"


# -- Webhooks ----------------------------------------------------------------


async def _webhook(k, **falt) -> dict:
    svar = await k.post(f"{V1}/webhooks", json={"url": "https://kund.example.se/snajp", **falt})
    assert svar.status_code == 201, svar.text
    return svar.json()


async def test_webhooken_far_handelsen_signerad(buddy, annan, storage, mottagare):
    async with buddy.klient() as k:
        hake = await _webhook(k, events=["company.created", "company.deleted"])
        assert hake["secret"].startswith("whsec_")
        # Hemligheten visas en gång och lagras inte i klartext.
        assert "secret" not in (await k.get(f"{V1}/webhooks/{hake['id']}")).json()
        assert hake["secret"] not in json.dumps(list(lagring._minne(storage, "crm_webhooks").values()))
        bolag = (await k.post(f"{V1}/companies", json={"name": "Bygg AB", "org_number": ORGNR_A})).json()
        await k.patch(f"{V1}/companies/{bolag['id']}", json={"phone": "08-123 456 78"})   # inte prenumererad
        assert await webhooks.kor_varv(storage) == 1
        (anrop,) = mottagare.anrop
        kropp = json.loads(anrop.content)
        assert kropp["type"] == "company.created" and kropp["data"]["record"]["org_number"] == ORGNR_A
        assert anrop.headers["X-Snajp-Event"] == "company.created" and anrop.headers["X-Snajp-Delivery"] == kropp["id"]
        tid, v1 = (del_.split("=")[1] for del_ in anrop.headers["X-Snajp-Signature"].split(","))
        vantat = hmac.new(hake["secret"].encode(), f"{tid}.".encode() + anrop.content, hashlib.sha256).hexdigest()
        assert v1 == vantat and abs(int(tid) - datetime.now(timezone.utc).timestamp()) < 60
        logg = (await k.get(f"{V1}/webhooks/{hake['id']}/deliveries")).json()["data"]
        assert [(rad["event"], rad["status"], rad["attempts"], rad["status_code"]) for rad in logg] == [
            ("company.created", "delivered", 1, 200)]
        assert (await k.get(f"{V1}/webhooks/{hake['id']}")).json()["last_success_at"]
    # Den andra kundens skrivningar går inte till Buddys webhook, och den ser den inte.
    async with annan.klient() as k:
        await k.post(f"{V1}/companies", json={"name": "Annat AB"})
        assert (await k.get(f"{V1}/webhooks")).json()["data"] == []
        assert (await k.get(f"{V1}/webhooks/{hake['id']}")).status_code == 404
    assert await webhooks.kor_varv(storage, alla=True) == 0 and len(mottagare.anrop) == 1


async def test_misslyckad_leverans_forsoks_igen_och_gar_att_skicka_om(buddy, storage, mottagare):
    async with buddy.klient() as k:
        hake = await _webhook(k)
        mottagare.status = 500
        await k.post(f"{V1}/companies", json={"name": "Bygg AB"})
        await webhooks.kor_varv(storage)
        (rad,) = (await k.get(f"{V1}/webhooks/{hake['id']}/deliveries")).json()["data"]
        assert (rad["status"], rad["attempts"], rad["status_code"], rad["error"]) == ("pending", 1, 500, "HTTP 500")
        # Nästa försök ligger en minut bort: ett nytt varv skickar ingenting.
        assert await webhooks.kor_varv(storage) == 0 and len(mottagare.anrop) == 1
        # Efter det sista försöket står den som misslyckad.
        leverans = lagring._minne(storage, "crm_webhook_leveranser")[rad["id"]]
        leverans.update(forsok=len(webhooks.VANTETIDER), nasta_forsok_at=lagring.nu())
        await webhooks.kor_varv(storage)
        (rad,) = (await k.get(f"{V1}/webhooks/{hake['id']}/deliveries")).json()["data"]
        assert rad["status"] == "failed" and rad["next_attempt_at"] is None
        assert (await k.get(f"{V1}/webhooks/{hake['id']}")).json()["consecutive_failures"] == 2
        # Mottagaren är uppe igen: leveransen skickas om för hand.
        mottagare.status = 204
        assert (await k.post(f"{V1}/webhooks/{hake['id']}/deliveries/{rad['id']}/retry")).status_code == 202
        await webhooks.kor_varv(storage)
        (rad,) = (await k.get(f"{V1}/webhooks/{hake['id']}/deliveries")).json()["data"]
        assert rad["status"] == "delivered"
        assert (await k.get(f"{V1}/webhooks/{hake['id']}")).json()["consecutive_failures"] == 0


async def test_webhook_som_bara_misslyckas_stangs_av_och_sager_det(buddy, storage, mottagare):
    async with buddy.klient() as k:
        hake = await _webhook(k)
        lagring._minne(storage, "crm_webhooks")[hake["id"]]["fel_i_rad"] = webhooks.MAX_FEL_I_RAD - 1
        mottagare.status = 503
        await k.post(f"{V1}/companies", json={"name": "Bygg AB"})
        await webhooks.kor_varv(storage)
        av = (await k.get(f"{V1}/webhooks/{hake['id']}")).json()
        assert av["active"] is False and av["disabled_reason"] == "for_manga_fel"
        # En avstängd webhook får inga nya leveranser.
        await k.post(f"{V1}/companies", json={"name": "Nästa AB"})
        assert len((await k.get(f"{V1}/webhooks/{hake['id']}/deliveries")).json()["data"]) == 1
        # Slås den på igen börjar räkningen om.
        pa = (await k.patch(f"{V1}/webhooks/{hake['id']}", json={"active": True})).json()
        assert pa["active"] is True and pa["consecutive_failures"] == 0 and pa["disabled_reason"] is None


async def test_ping_och_synkens_slut_gar_ocksa_ut(buddy, storage, mottagare):
    async with buddy.klient() as k:
        hake = await _webhook(k, events=["sync.completed"])
        assert (await k.post(f"{V1}/webhooks/{hake['id']}/test")).status_code == 202
        await k.post(f"{V1}/connections", json={"name": "egen", "system": "generisk"})
        await k.post(f"{V1}/sync/companies", json={"connection": "egen", "items": [{"id": "1", "name": "Ett AB"}]})
        await webhooks.kor_varv(storage)
        typer = [json.loads(a.content)["type"] for a in mottagare.anrop]
        assert typer == ["ping", "sync.completed"]
        slut = json.loads(mottagare.anrop[1].content)["data"]
        assert slut["connection"] == "egen" and slut["counts"]["skapade"] == 1 and slut["status"] == "completed"


async def test_bara_publika_https_adresser_och_kanda_handelser(buddy):
    async with buddy.klient() as k:
        for url in ("http://kund.example.se/x", "https://localhost/x", "https://10.0.0.5/x",
                    "https://169.254.169.254/latest", "https://anv:losen@kund.example.se/x", "https://intern/x"):
            svar = await k.post(f"{V1}/webhooks", json={"url": url})
            assert svar.status_code == 422 and svar.json()["detail"]["code"] == "invalid_url", url
        svar = await k.post(f"{V1}/webhooks", json={"url": "https://kund.example.se/x", "events": ["company.exploded"]})
        assert svar.status_code == 422 and svar.json()["detail"]["code"] == "invalid_events"
        for _ in range(webhooks.MAX_PER_KUND):
            await _webhook(k)
        svar = await k.post(f"{V1}/webhooks", json={"url": "https://kund.example.se/x"})
        assert svar.status_code == 422 and svar.json()["detail"]["code"] == "too_many_webhooks"
    # Webhooks kräver omfånget crm:admin.
    las = await buddy.ny_nyckel(["crm:las", "crm:skriv", "crm:synk"])
    async with buddy.klient(las) as k:
        assert (await k.get(f"{V1}/webhooks")).status_code == 403
        assert (await k.get(f"{V1}/webhooks/events")).status_code == 200
        assert (await k.get(f"{V1}/changes")).status_code == 200


async def test_adressen_provas_igen_nar_leveransen_gar(buddy, storage, monkeypatch, mottagare):
    """Ett namn som var publikt när webhooken skapades och sedan pekas om inåt."""
    async with buddy.klient() as k:
        hake = await _webhook(k)

        async def inat(vard: str, port: int) -> list[str]:
            return ["10.0.0.7"]

        monkeypatch.setattr(natvakt, "upplos", inat)
        await k.post(f"{V1}/companies", json={"name": "Bygg AB"})
        await webhooks.kor_varv(storage)
        (rad,) = (await k.get(f"{V1}/webhooks/{hake['id']}/deliveries")).json()["data"]
        assert rad["status"] == "pending" and "NatvaktError" in rad["error"] and mottagare.anrop == []
