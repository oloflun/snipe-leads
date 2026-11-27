"""Uppgifter, anteckningar, aktiviteter och bilagor (migration 164), kaskaden
vid tömning och omfånget. Affärerna och stegen står i test_objekt.py.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

import pytest

from app.crm import lagring, objekt, webhooks

V1 = "/api/crm/v1"
pytestmark = pytest.mark.anyio

PDF = b"%PDF-1.4\n%provfil\n"


@pytest.fixture(autouse=True)
def _rent():
    webhooks.nollstall()
    yield
    webhooks.nollstall()


async def _bolag(k, namn: str = "Bygg AB") -> dict:
    return (await k.post(f"{V1}/companies", json={"name": namn})).json()


async def _ladda_upp(k, namn: str = "offert.pdf", data: bytes = PDF, typ: str = "application/pdf", **kopplingar):
    return await k.post(f"{V1}/attachments", files={"file": (namn, data, typ)}, data=kopplingar)


# -- Uppgifter ---------------------------------------------------------------


async def test_uppgift_star_fri_och_klar_at_foljer_status(buddy):
    async with buddy.klient() as k:
        fri = await k.post(f"{V1}/tasks", json={"title": "Ring tillbaka", "description": "Rad ett\nRad två"})
        assert fri.status_code == 201, fri.text
        uppgift = fri.json()
        assert (uppgift["status"], uppgift["completed_at"], uppgift["company_id"]) == ("todo", None, None)
        assert uppgift["description"] == "Rad ett\nRad två"
        klar = (await k.patch(f"{V1}/tasks/{uppgift['id']}", json={"status": "done"})).json()
        assert klar["status"] == "done" and klar["completed_at"]
        igen = (await k.patch(f"{V1}/tasks/{uppgift['id']}", json={"status": "in_progress"})).json()
        assert igen["completed_at"] is None
        assert (await k.post(f"{V1}/tasks", json={"description": "utan titel"})).status_code == 422
        svar = await k.post(f"{V1}/tasks", json={"title": "x", "due_at": "i morgon"})
        assert svar.status_code == 422 and svar.json()["detail"]["fields"] == [
            {"field": "due_at", "code": "tidpunkt_ogiltig"}]
        assert (await k.delete(f"{V1}/tasks/{uppgift['id']}")).status_code == 204
        assert [u["id"] for u in (await k.get(f"{V1}/tasks", params={"only_deleted": "true"})).json()["data"]] == [
            uppgift["id"]]
        assert (await k.post(f"{V1}/tasks/{uppgift['id']}/restore")).json()["deleted_at"] is None


async def test_uppgifter_sorteras_pa_forfallodag_och_filtreras(buddy):
    async with buddy.klient() as k:
        bolag = await _bolag(k)
        affar = (await k.post(f"{V1}/deals", json={"name": "Takbyte"})).json()
        await k.post(f"{V1}/tasks", json={"title": "Utan dag"})
        await k.post(f"{V1}/tasks", json={"title": "Sen", "due_at": "2026-12-20T09:00:00+01:00", "owner": "Sebbe"})
        await k.post(f"{V1}/tasks", json={"title": "Tidig", "due_at": "2026-12-01T08:00:00Z",
                                          "company_id": bolag["id"], "deal_id": affar["id"]})
        await k.post(f"{V1}/tasks", json={"title": "Klar", "due_at": "2026-11-30T08:00:00Z", "status": "done"})
        sida = (await k.get(f"{V1}/tasks", params={"sort": "due", "limit": 3})).json()
        assert [u["title"] for u in sida["data"]] == ["Klar", "Tidig", "Sen"]
        resten = (await k.get(f"{V1}/tasks", params={"sort": "due", "limit": 3, "cursor": sida["next_cursor"]})).json()
        assert [u["title"] for u in resten["data"]] == ["Utan dag"] and resten["next_cursor"] is None
        # Tiden lagras i UTC, så att ordningen är tidens och inte strängens.
        assert sida["data"][2]["due_at"] == "2026-12-20T08:00:00+00:00"

        async def titlar(**p) -> list[str]:
            return sorted(u["title"] for u in (await k.get(f"{V1}/tasks", params=p)).json()["data"])

        assert await titlar(status="done") == ["Klar"]
        assert await titlar(status="todo") == ["Sen", "Tidig", "Utan dag"]
        assert await titlar(owner="Sebbe") == ["Sen"]
        assert await titlar(due_before="2026-12-10T00:00:00Z") == ["Klar", "Tidig"]
        assert await titlar(company_id=bolag["id"]) == ["Tidig"]
        assert await titlar(deal_id=affar["id"]) == ["Tidig"]
        assert await titlar(q="tidi") == ["Tidig"]
        assert (await k.get(f"{V1}/tasks", params={"due_before": "snart"})).status_code == 422
        assert (await k.get(f"{V1}/tasks", params={"sort": "name"})).status_code == 422


# -- Anteckningar och aktiviteter --------------------------------------------


async def test_anteckning_kraver_koppling_och_har_ett_tak(buddy):
    async with buddy.klient() as k:
        bolag = await _bolag(k)
        person = (await k.post(f"{V1}/people", json={"email": "vd@bygg.se"})).json()
        svar = await k.post(f"{V1}/notes", json={"body": "Ingen koppling"})
        assert svar.status_code == 422 and svar.json()["detail"]["code"] == "target_required"
        svar = await k.post(f"{V1}/notes", json={"body": "x" * (objekt.MAX_ANTECKNING + 1), "person_id": person["id"]})
        assert svar.status_code == 422 and svar.json()["detail"]["fields"] == [{"field": "body", "code": "for_lang"}]
        anteckning = (await k.post(f"{V1}/notes", json={"title": "Möte", "body": "Vill ha offert\nfre",
                                                         "person_id": person["id"], "pinned": True})).json()
        assert anteckning["body"] == "Vill ha offert\nfre" and anteckning["pinned"] is True
        svar = await k.patch(f"{V1}/notes/{anteckning['id']}", json={"person_id": None})
        assert svar.status_code == 422 and svar.json()["detail"]["code"] == "target_required"
        flyttad = (await k.patch(f"{V1}/notes/{anteckning['id']}",
                                 json={"person_id": None, "company_id": bolag["id"]})).json()
        assert (flyttad["person_id"], flyttad["company_id"]) == (None, bolag["id"])
        # En koppling till en raderad post gäller inte.
        await k.delete(f"{V1}/people/{person['id']}")
        svar = await k.post(f"{V1}/notes", json={"body": "x", "person_id": person["id"]})
        assert svar.status_code == 422 and svar.json()["detail"]["code"] == "person_not_found"
        assert (await k.delete(f"{V1}/notes/{anteckning['id']}")).status_code == 204
        assert (await k.get(f"{V1}/notes")).json()["data"] == []
        assert len((await k.get(f"{V1}/notes", params={"include_deleted": "true"})).json()["data"]) == 1
        await k.post(f"{V1}/notes/{anteckning['id']}/restore")
        assert [n["id"] for n in (await k.get(f"{V1}/notes", params={"company_id": bolag["id"]})).json()["data"]] == [
            anteckning["id"]]


async def test_aktiviteter_loggas_sorteras_och_filtreras(buddy):
    async with buddy.klient() as k:
        bolag = await _bolag(k)
        affar = (await k.post(f"{V1}/deals", json={"name": "Takbyte", "company_id": bolag["id"]})).json()
        samtal = (await k.post(f"{V1}/activities", json={
            "type": "call", "subject": "Första samtalet", "duration_minutes": 12, "outcome": "Vill ha offert",
            "deal_id": affar["id"]})).json()
        assert samtal["type"] == "call" and samtal["occurred_at"] and samtal["duration_minutes"] == 12
        mote = (await k.post(f"{V1}/activities", json={"type": "meeting", "subject": "Platsbesök",
                                                       "occurred_at": "2026-11-20T10:00:00+01:00",
                                                       "company_id": bolag["id"]})).json()
        assert mote["occurred_at"] == "2026-11-20T09:00:00+00:00"
        svar = await k.post(f"{V1}/activities", json={"subject": "Ensam"})
        assert svar.status_code == 422 and svar.json()["detail"]["code"] == "target_required"
        assert (await k.post(f"{V1}/activities", json={"type": "fax", "subject": "x",
                                                       "deal_id": affar["id"]})).status_code == 422
        sida = (await k.get(f"{V1}/activities", params={"sort": "-updated", "limit": 1})).json()
        assert [a["subject"] for a in sida["data"]] == ["Platsbesök"]
        nasta = (await k.get(f"{V1}/activities", params={"sort": "-updated", "limit": 1,
                                                         "cursor": sida["next_cursor"]})).json()
        assert [a["subject"] for a in nasta["data"]] == ["Första samtalet"] and nasta["next_cursor"] is None
        assert [a["id"] for a in (await k.get(f"{V1}/activities", params={"deal_id": affar["id"]})).json()["data"]] == [
            samtal["id"]]
        andrad = (await k.patch(f"{V1}/activities/{samtal['id']}", json={"type": "email", "occurred_at": None})).json()
        assert andrad["type"] == "email" and andrad["occurred_at"] == samtal["occurred_at"]
        await k.delete(f"{V1}/activities/{samtal['id']}")
        assert len((await k.get(f"{V1}/activities", params={"only_deleted": "true"})).json()["data"]) == 1
        assert (await k.post(f"{V1}/activities/{samtal['id']}/restore")).json()["deleted_at"] is None
        person = (await k.post(f"{V1}/people", json={"email": "vd@bygg.se"})).json()
        med_person = (await k.post(f"{V1}/activities", json={"subject": "Lunch", "person_id": person["id"]})).json()
        assert [a["id"] for a in (await k.get(f"{V1}/activities", params={"company_id": bolag["id"]})).json()[
            "data"]] == [mote["id"]]
        assert [a["id"] for a in (await k.get(f"{V1}/activities", params={"person_id": person["id"]})).json()[
            "data"]] == [med_person["id"]]


async def test_anteckningar_sorteras_sidindelas_och_filtreras(buddy):
    async with buddy.klient() as k:
        bolag = await _bolag(k)
        person = (await k.post(f"{V1}/people", json={"email": "vd@bygg.se"})).json()
        affar = (await k.post(f"{V1}/deals", json={"name": "Takbyte"})).json()
        forsta = (await k.post(f"{V1}/notes", json={"body": "Om bolaget", "company_id": bolag["id"]})).json()
        andra = (await k.post(f"{V1}/notes", json={"body": "Om personen", "person_id": person["id"]})).json()
        tredje = (await k.post(f"{V1}/notes", json={"title": "Offert", "body": "Om affären",
                                                     "deal_id": affar["id"]})).json()
        sida = (await k.get(f"{V1}/notes", params={"sort": "-updated", "limit": 2})).json()
        assert [n["id"] for n in sida["data"]] == [tredje["id"], andra["id"]]
        resten = (await k.get(f"{V1}/notes", params={"sort": "-updated", "limit": 2,
                                                      "cursor": sida["next_cursor"]})).json()
        assert [n["id"] for n in resten["data"]] == [forsta["id"]] and resten["next_cursor"] is None
        stigande = (await k.get(f"{V1}/notes", params={"sort": "updated"})).json()["data"]
        assert [n["id"] for n in stigande] == [forsta["id"], andra["id"], tredje["id"]]

        async def ids(**p) -> list[str]:
            return [n["id"] for n in (await k.get(f"{V1}/notes", params=p)).json()["data"]]

        assert await ids(person_id=person["id"]) == [andra["id"]]
        assert await ids(deal_id=affar["id"]) == [tredje["id"]]
        assert await ids(q="offert") == [tredje["id"]]
        assert await ids(q="personen") == [andra["id"]]
        assert (await k.get(f"{V1}/notes", params={"cursor": "skrap"})).json()["detail"]["message"] == (
            "cursor could not be read.")


# -- Bilagor -----------------------------------------------------------------


async def test_bilagan_laddas_upp_listas_utan_innehall_och_laddas_ned(buddy):
    async with buddy.klient() as k:
        bolag = await _bolag(k)
        svar = await _ladda_upp(k, company_id=bolag["id"])
        assert svar.status_code == 201, svar.text
        bilaga = svar.json()
        assert (bilaga["filename"], bilaga["content_type"], bilaga["size"]) == ("offert.pdf", "application/pdf", len(PDF))
        assert bilaga["uploaded_by"].startswith("nyckel:") and bilaga["company_id"] == bolag["id"]
        lista = (await k.get(f"{V1}/attachments", params={"company_id": bolag["id"]})).json()
        assert [b["id"] for b in lista["data"]] == [bilaga["id"]]
        assert "provfil" not in json.dumps(lista) and "innehall" not in json.dumps(lista)
        assert "content" not in lista["data"][0] and "provfil" not in json.dumps(bilaga)
        ned = await k.get(f"{V1}/attachments/{bilaga['id']}/content")
        assert ned.status_code == 200 and ned.content == PDF
        assert ned.headers["content-type"] == "application/pdf"
        assert ned.headers["content-disposition"].startswith('attachment; filename="offert.pdf"')
        assert ned.headers["x-content-type-options"] == "nosniff"
        assert ned.headers["cache-control"] == "private, no-store"
        # Filnamnet rensas från sökvägar och styrtecken.
        for skickat, sparat in [("..\\..\\x.pdf", "x.pdf"), ("a/b.pdf", "b.pdf"), ("‮ond.pdf", "ond.pdf")]:
            assert (await _ladda_upp(k, skickat, company_id=bolag["id"])).json()["filename"] == sparat, skickat
        # Styrtecken kodar klienten själv om i rubriken; rensningen tål dem ändå.
        assert objekt.rensa_filnamn("ond\x00\x1b\r\n.pdf") == "ond.pdf"
        assert objekt.rensa_filnamn("../..") == "fil" and objekt.rensa_filnamn(".htaccess.txt") == "htaccess.txt"
        await k.delete(f"{V1}/attachments/{bilaga['id']}")
        assert (await k.get(f"{V1}/attachments/{bilaga['id']}/content")).status_code == 404
        assert (await k.get(f"{V1}/attachments/{bilaga['id']}", params={"include_deleted": "true"})).json()["deleted_at"]
        await k.post(f"{V1}/attachments/{bilaga['id']}/restore")
        assert (await k.get(f"{V1}/attachments/{bilaga['id']}/content")).content == PDF


async def test_bilagans_storlek_typ_och_kvot(buddy, annan, monkeypatch):
    monkeypatch.setattr(objekt, "MAX_BILAGA", 1000)
    monkeypatch.setattr(objekt, "MAX_BILAGOR_PER_KUND", 1500)
    async with annan.klient() as k:
        annans = (await k.post(f"{V1}/notes", json={"body": "x", "company_id": (await _bolag(k))["id"]})).json()
    async with buddy.klient() as k:
        bolag = await _bolag(k)
        svar = await _ladda_upp(k, data=b"x" * 1001, company_id=bolag["id"])
        assert svar.status_code == 413 and svar.json()["detail"]["code"] == "file_too_large"
        # En kropp som säger sig vara för stor avvisas innan den läses.
        stor = await k.post(f"{V1}/attachments", content=b"x" * 70_000,
                            headers={"Content-Type": "multipart/form-data; boundary=x"})
        assert stor.status_code == 413 and stor.json()["detail"]["code"] == "file_too_large"
        for namn, typ in [("program.exe", "application/octet-stream"), ("sida.html", "text/html"),
                          ("sida.pdf", "text/html"), ("utan_andelse", "application/pdf")]:
            svar = await _ladda_upp(k, namn, typ=typ, company_id=bolag["id"])
            assert svar.status_code == 422 and svar.json()["detail"]["code"] == "file_type_not_allowed", namn
        # Utan angiven typ avgör ändelsen; Excel på Windows kallar csv för ms-excel.
        okand = (await _ladda_upp(k, "bild.png", b"\x89PNG", "application/octet-stream", company_id=bolag["id"])).json()
        assert okand["content_type"] == "image/png"
        assert (await _ladda_upp(k, "lista.csv", b"a;b", "application/vnd.ms-excel",
                                 company_id=bolag["id"])).json()["content_type"] == "text/csv"
        svar = await _ladda_upp(k, data=b"x" * 900, company_id=bolag["id"])
        assert svar.status_code == 201
        svar = await _ladda_upp(k, data=b"x" * 900, company_id=bolag["id"])
        assert svar.status_code == 409 and svar.json()["detail"]["code"] == "storage_quota_exceeded"
        svar = await _ladda_upp(k, data=b"x")
        assert svar.status_code == 422 and svar.json()["detail"]["code"] == "target_required"
        svar = await _ladda_upp(k, data=b"x", note_id=annans["id"])
        assert svar.status_code == 422 and svar.json()["detail"]["code"] == "note_not_found"
        svar = await k.post(f"{V1}/attachments", data={"company_id": bolag["id"]})
        assert svar.status_code == 422 and svar.json()["detail"]["code"] == "invalid_body"
        # Ett felformat id får API:ts fältnamn, inte CRM:ets kolumner.
        svar = await _ladda_upp(k, data=b"x", company_id="inte-ett-uuid", note_id="x")
        assert svar.status_code == 422 and svar.json()["detail"]["fields"] == [
            {"field": "company_id", "code": "id_ogiltigt"}, {"field": "note_id", "code": "id_ogiltigt"}]
        # Raderade filer räknas tills de töms; permanent radering frigör platsen direkt.
        stor = next(b for b in (await k.get(f"{V1}/attachments")).json()["data"] if b["size"] == 900)
        await k.delete(f"{V1}/attachments/{stor['id']}")
        svar = await _ladda_upp(k, data=b"x" * 900, company_id=bolag["id"])
        assert svar.status_code == 409 and "permanent=true" in svar.json()["detail"]["message"]
        await k.delete(f"{V1}/attachments/{stor['id']}", params={"permanent": "true"})
        assert (await _ladda_upp(k, data=b"x" * 900, company_id=bolag["id"])).status_code == 201


async def test_en_kropp_utan_content_length_raknas_medan_den_lases(buddy, monkeypatch):
    monkeypatch.setattr(objekt, "MAX_BILAGA", 1000)
    lasta = {"bitar": 0}

    async def strom():
        # Långt mer än gränsen (1000 + 64 KiB), i bitar utan Content-Length.
        for _ in range(200):
            lasta["bitar"] += 1
            yield b"x" * 4096

    async with buddy.klient() as k:
        svar = await k.post(f"{V1}/attachments", content=strom(),
                            headers={"Content-Type": "multipart/form-data; boundary=x"})
    assert svar.status_code == 413 and svar.json()["detail"]["code"] == "file_too_large"
    assert "content-length" not in {n.lower() for n in svar.request.headers}
    # Läsningen avbröts när gränsen passerades, inte efter hela kroppen.
    assert lasta["bitar"] < 200


async def test_samma_uppladdning_med_samma_nyckel_ger_samma_svar(buddy):
    """Multipartens gräns slumpas om för varje anrop; nyckeln ska ändå känna igen omförsöket."""
    async with buddy.klient() as k:
        bolag = await _bolag(k)
        forsta = await k.post(f"{V1}/attachments", files={"file": ("offert.pdf", PDF, "application/pdf")},
                              data={"company_id": bolag["id"]}, headers={"Idempotency-Key": "k1"})
        assert forsta.status_code == 201, forsta.text
        igen = await k.post(f"{V1}/attachments", files={"file": ("offert.pdf", PDF, "application/pdf")},
                            data={"company_id": bolag["id"]}, headers={"Idempotency-Key": "k1"})
        assert igen.status_code == 201 and igen.headers.get("idempotent-replayed") == "true"
        assert igen.json()["id"] == forsta.json()["id"]
        assert len((await k.get(f"{V1}/attachments")).json()["data"]) == 1
        annan_fil = await k.post(f"{V1}/attachments", files={"file": ("offert.pdf", PDF + b"!", "application/pdf")},
                                 data={"company_id": bolag["id"]}, headers={"Idempotency-Key": "k1"})
        assert annan_fil.status_code == 422 and annan_fil.json()["detail"]["code"] == "idempotency_key_reused"


async def test_bilagor_sorteras_sidindelas_och_filtreras(buddy):
    async with buddy.klient() as k:
        bolag = await _bolag(k)
        person = (await k.post(f"{V1}/people", json={"email": "vd@bygg.se"})).json()
        affar = (await k.post(f"{V1}/deals", json={"name": "Takbyte"})).json()
        anteckning = (await k.post(f"{V1}/notes", json={"body": "x", "company_id": bolag["id"]})).json()
        pa_bolaget = (await _ladda_upp(k, "bolag.pdf", company_id=bolag["id"])).json()
        pa_personen = (await _ladda_upp(k, "cv.pdf", person_id=person["id"])).json()
        pa_affaren = (await _ladda_upp(k, "offert.pdf", deal_id=affar["id"])).json()
        pa_anteckningen = (await _ladda_upp(k, "bild.png", b"\x89PNG", "image/png", note_id=anteckning["id"])).json()
        sida = (await k.get(f"{V1}/attachments", params={"sort": "-updated", "limit": 3})).json()
        assert [b["id"] for b in sida["data"]] == [pa_anteckningen["id"], pa_affaren["id"], pa_personen["id"]]
        resten = (await k.get(f"{V1}/attachments", params={"sort": "-updated", "limit": 3,
                                                            "cursor": sida["next_cursor"]})).json()
        assert [b["id"] for b in resten["data"]] == [pa_bolaget["id"]] and resten["next_cursor"] is None

        async def ids(**p) -> list[str]:
            return [b["id"] for b in (await k.get(f"{V1}/attachments", params=p)).json()["data"]]

        assert await ids(person_id=person["id"]) == [pa_personen["id"]]
        assert await ids(deal_id=affar["id"]) == [pa_affaren["id"]]
        assert await ids(note_id=anteckning["id"]) == [pa_anteckningen["id"]]
        assert await ids(q="cv") == [pa_personen["id"]]
        await k.delete(f"{V1}/attachments/{pa_personen['id']}")
        assert await ids(only_deleted="true") == [pa_personen["id"]]
        assert pa_personen["id"] not in await ids()


# -- Isolering, omfång och händelser -----------------------------------------


async def test_en_kund_ser_och_kopplar_aldrig_till_en_annans_poster(buddy, annan):
    async with buddy.klient() as k:
        bolag = await _bolag(k)
        person = (await k.post(f"{V1}/people", json={"email": "vd@bygg.se"})).json()
        affar = (await k.post(f"{V1}/deals", json={"name": "Takbyte"})).json()
        uppgift = (await k.post(f"{V1}/tasks", json={"title": "Ring", "company_id": bolag["id"]})).json()
        anteckning = (await k.post(f"{V1}/notes", json={"body": "Hemligt", "company_id": bolag["id"]})).json()
        aktivitet = (await k.post(f"{V1}/activities", json={"subject": "Samtal", "person_id": person["id"]})).json()
        bilaga = (await _ladda_upp(k, deal_id=affar["id"])).json()
    async with annan.klient() as k:
        for vag, post in [("tasks", uppgift), ("notes", anteckning), ("activities", aktivitet),
                          ("attachments", bilaga)]:
            assert (await k.get(f"{V1}/{vag}")).json()["data"] == [], vag
            assert (await k.get(f"{V1}/{vag}", params={"include_deleted": "true"})).json()["data"] == [], vag
            assert (await k.get(f"{V1}/{vag}/{post['id']}")).status_code == 404, vag
            assert (await k.delete(f"{V1}/{vag}/{post['id']}")).status_code == 404, vag
            assert (await k.post(f"{V1}/{vag}/{post['id']}/restore")).status_code == 404, vag
            if vag != "attachments":
                assert (await k.patch(f"{V1}/{vag}/{post['id']}", json={})).status_code == 404, vag
        assert (await k.get(f"{V1}/attachments/{bilaga['id']}/content")).status_code == 404
        egen = await _bolag(k, "Eget AB")
        for kropp, kod in [({"company_id": bolag["id"]}, "company_not_found"),
                           ({"person_id": person["id"]}, "person_not_found"),
                           ({"deal_id": affar["id"]}, "deal_not_found")]:
            for vag, grund in [("tasks", {"title": "x"}), ("notes", {"body": "x"}), ("activities", {"subject": "x"})]:
                svar = await k.post(f"{V1}/{vag}", json={**grund, **kropp})
                assert svar.status_code == 422 and svar.json()["detail"]["code"] == kod, (vag, kod)
            svar = await _ladda_upp(k, **kropp)
            assert svar.status_code == 422 and svar.json()["detail"]["code"] == kod
        # En egen uppgift kan inte flyttas över till den första kundens bolag.
        egen_uppgift = (await k.post(f"{V1}/tasks", json={"title": "Egen", "company_id": egen["id"]})).json()
        svar = await k.patch(f"{V1}/tasks/{egen_uppgift['id']}", json={"company_id": bolag["id"]})
        assert svar.status_code == 422 and svar.json()["detail"]["code"] == "company_not_found"


async def test_en_lasnyckel_laser_men_skriver_inte(buddy):
    async with buddy.klient() as k:
        bolag = await _bolag(k)
    las = await buddy.ny_nyckel(["crm:las"])
    async with buddy.klient(las) as k:
        for vag in ("deal-stages", "deals", "deals/board", "tasks", "notes", "activities", "attachments"):
            assert (await k.get(f"{V1}/{vag}")).status_code == 200, vag
        for vag, kropp in [("deal-stages", {"name": "X"}), ("deals", {"name": "X"}), ("tasks", {"title": "X"}),
                           ("notes", {"body": "x", "company_id": bolag["id"]}),
                           ("activities", {"subject": "x", "company_id": bolag["id"]})]:
            svar = await k.post(f"{V1}/{vag}", json=kropp)
            assert svar.status_code == 403 and svar.json()["detail"]["code"] == "scope_missing", vag
        svar = await _ladda_upp(k, company_id=bolag["id"])
        assert svar.status_code == 403 and svar.json()["detail"]["code"] == "scope_missing"


async def test_skrivningar_kraver_avtalet(utan_avtal):
    async with utan_avtal.klient() as k:
        assert (await k.get(f"{V1}/tasks")).status_code == 200
        svar = await k.post(f"{V1}/tasks", json={"title": "x"})
        assert svar.status_code == 403 and svar.json()["detail"]["code"] == "agreement_missing"
        svar = await _ladda_upp(k, company_id="00000000-0000-0000-0000-000000000000")
        assert svar.status_code == 403 and svar.json()["detail"]["code"] == "agreement_missing"


async def test_varje_objekts_skrivning_syns_i_flodet_och_webhooken_bar_ingen_fil(buddy, storage):
    async with buddy.klient() as k:
        hake = await k.post(f"{V1}/webhooks", json={"url": "https://kund.example.se/snajp",
                                                    "events": ["attachment.created"]})
        assert hake.status_code == 201, hake.text
        bolag = await _bolag(k)
        uppgift = (await k.post(f"{V1}/tasks", json={"title": "Ring"})).json()
        await k.patch(f"{V1}/tasks/{uppgift['id']}", json={"status": "done", "due_at": "2026-12-01T08:00:00Z"})
        anteckning = (await k.post(f"{V1}/notes", json={"body": "x", "company_id": bolag["id"]})).json()
        aktivitet = (await k.post(f"{V1}/activities", json={"subject": "x", "company_id": bolag["id"]})).json()
        bilaga = (await _ladda_upp(k, company_id=bolag["id"])).json()
        await k.delete(f"{V1}/notes/{anteckning['id']}")
        await k.post(f"{V1}/notes/{anteckning['id']}/restore")
        await k.delete(f"{V1}/activities/{aktivitet['id']}", params={"permanent": "true"})
        flode = (await k.get(f"{V1}/changes")).json()["data"]
        assert [(h["object"], h["type"]) for h in flode] == [
            ("company", "created"), ("task", "created"), ("task", "updated"), ("note", "created"),
            ("activity", "created"), ("attachment", "created"), ("note", "deleted"), ("note", "restored"),
            ("activity", "purged")]
        assert sorted(flode[2]["fields"]) == ["completed_at", "due_at", "status"]
        assert [h["id"] for h in (await k.get(f"{V1}/changes", params={"object": "attachment"})).json()["data"]] == [
            bilaga["id"]]
        assert (await k.get(f"{V1}/webhooks/events")).json()["events"].count("attachment.created") == 1
    (leverans,) = lagring._minne(storage, "crm_webhook_leveranser").values()
    assert leverans["handelsetyp"] == "attachment.created"
    assert leverans["kropp"]["data"]["record"]["filename"] == "offert.pdf"
    assert "provfil" not in json.dumps(leverans["kropp"])


# -- Kaskaden vid tömning ----------------------------------------------------


async def test_tomt_bolag_och_tomd_person_tar_med_sig_det_som_pekar_pa_dem(buddy, storage):
    """GDPR artikel 17: fritext och filer om posten töms, affärer och uppgifter
    är kundens egna och tappar bara kopplingen."""
    async with buddy.klient() as k:
        bolag = await _bolag(k)
        annat = await _bolag(k, "Annat AB")
        person = (await k.post(f"{V1}/people", json={"email": "vd@bygg.se"})).json()
        affar = (await k.post(f"{V1}/deals", json={"name": "Takbyte", "company_id": bolag["id"]})).json()
        uppgift = (await k.post(f"{V1}/tasks", json={"title": "Ring", "company_id": bolag["id"]})).json()
        anteckning = (await k.post(f"{V1}/notes", json={"body": "Vd:n heter Anna", "company_id": bolag["id"]})).json()
        aktivitet = (await k.post(f"{V1}/activities", json={"subject": "Samtal", "company_id": bolag["id"]})).json()
        bilaga = (await _ladda_upp(k, company_id=bolag["id"])).json()
        # En fil på anteckningen följer anteckningen, också när den själv pekar på ett annat bolag.
        pa_anteckningen = (await _ladda_upp(k, "bild.png", b"\x89PNG", "image/png", note_id=anteckning["id"],
                                            company_id=annat["id"])).json()
        om_personen = (await k.post(f"{V1}/notes", json={"body": "Privat", "person_id": person["id"]})).json()
        orord = (await k.post(f"{V1}/notes", json={"body": "Står kvar", "company_id": annat["id"]})).json()

        assert (await k.delete(f"{V1}/companies/{bolag['id']}", params={"permanent": "true"})).status_code == 204
        for vag, post in [("notes", anteckning), ("activities", aktivitet), ("attachments", bilaga),
                          ("attachments", pa_anteckningen)]:
            tomd = (await k.get(f"{V1}/{vag}/{post['id']}", params={"include_deleted": "true"})).json()
            assert tomd["deleted_at"] and tomd["source"] == lagring.GRAVSTEN and tomd["company_id"] is None, vag
            assert (await k.post(f"{V1}/{vag}/{post['id']}/restore")).status_code == 410, vag
        minne = lagring._minne(storage, "crm_anteckningar")
        assert minne[anteckning["id"]]["text"] == "" and lagring._minne(storage, "crm_bilagor")[bilaga["id"]][
            "innehall"] == b""
        assert (await k.get(f"{V1}/deals/{affar['id']}")).json()["company_id"] is None
        assert (await k.get(f"{V1}/tasks/{uppgift['id']}")).json()["company_id"] is None
        assert (await k.get(f"{V1}/notes/{orord['id']}")).json()["body"] == "Står kvar"
        flode = (await k.get(f"{V1}/changes")).json()["data"]
        tomda = {(h["object"], h["id"]) for h in flode if h["type"] == "purged"}
        assert {("company", bolag["id"]), ("note", anteckning["id"]), ("activity", aktivitet["id"]),
                ("attachment", bilaga["id"]), ("attachment", pa_anteckningen["id"])} <= tomda
        tappade = [(h["object"], h["fields"]) for h in flode if h["type"] == "updated"]
        assert ("deal", ["company_id"]) in tappade and ("task", ["company_id"]) in tappade

        await k.delete(f"{V1}/people/{person['id']}", params={"permanent": "true"})
        assert (await k.get(f"{V1}/notes/{om_personen['id']}", params={"include_deleted": "true"})).json()["body"] == ""


async def test_en_tomd_affar_tar_med_sig_sitt_arbete_och_uppgiften_tappar_kopplingen(buddy, annan, storage):
    """Granskningens fynd: en affär som töms lämnade anteckningar, aktiviteter
    och bilagor kvar, pekande på en gravsten."""
    async with buddy.klient() as k:
        bolag = await _bolag(k)
        affar = (await k.post(f"{V1}/deals", json={"name": "Takbyte", "company_id": bolag["id"]})).json()
        anteckning = (await k.post(f"{V1}/notes", json={"body": "Offert till Anna", "deal_id": affar["id"]})).json()
        aktivitet = (await k.post(f"{V1}/activities", json={"subject": "Samtal", "deal_id": affar["id"]})).json()
        bilaga = (await _ladda_upp(k, deal_id=affar["id"])).json()
        uppgift = (await k.post(f"{V1}/tasks", json={"title": "Skicka offert", "deal_id": affar["id"]})).json()
        pa_bolaget = (await k.post(f"{V1}/notes", json={"body": "Står kvar", "company_id": bolag["id"]})).json()
    async with annan.klient() as k:
        hans_affar = (await k.post(f"{V1}/deals", json={"name": "Hans affär"})).json()
        hans = (await k.post(f"{V1}/notes", json={"body": "Hans anteckning", "deal_id": hans_affar["id"]})).json()
    async with buddy.klient() as k:
        assert (await k.delete(f"{V1}/deals/{affar['id']}", params={"permanent": "true"})).status_code == 204
        for vag, post in [("notes", anteckning), ("activities", aktivitet), ("attachments", bilaga)]:
            tomd = (await k.get(f"{V1}/{vag}/{post['id']}", params={"include_deleted": "true"})).json()
            assert tomd["deleted_at"] and tomd["source"] == lagring.GRAVSTEN and tomd["deal_id"] is None, vag
        assert lagring._minne(storage, "crm_anteckningar")[anteckning["id"]]["text"] == ""
        assert lagring._minne(storage, "crm_bilagor")[bilaga["id"]]["innehall"] == b""
        kvar = (await k.get(f"{V1}/tasks/{uppgift['id']}")).json()
        assert kvar["deleted_at"] is None and kvar["title"] == "Skicka offert" and kvar["deal_id"] is None
        assert (await k.get(f"{V1}/notes/{pa_bolaget['id']}")).json()["body"] == "Står kvar"
        flode = (await k.get(f"{V1}/changes")).json()["data"]
        tomda = {(h["object"], h["id"]) for h in flode if h["type"] == "purged"}
        assert {("deal", affar["id"]), ("note", anteckning["id"]), ("activity", aktivitet["id"]),
                ("attachment", bilaga["id"])} <= tomda
        assert ("task", ["deal_id"]) in [(h["object"], h["fields"]) for h in flode if h["type"] == "updated"]
    async with annan.klient() as k:
        assert (await k.get(f"{V1}/notes/{hans['id']}")).json()["body"] == "Hans anteckning"


async def test_papperskorgen_toms_efter_trettio_dagar(buddy, storage):
    async with buddy.klient() as k:
        bolag = await _bolag(k)
        anteckning = (await k.post(f"{V1}/notes", json={"body": "Gammal", "company_id": bolag["id"]})).json()
        await k.delete(f"{V1}/notes/{anteckning['id']}")
        rad = lagring._minne(storage, "crm_anteckningar")[anteckning["id"]]
        rad["raderad_at"] = (datetime.now(timezone.utc) - timedelta(days=31)).isoformat()
        assert await lagring.tom_papperskorg(storage, buddy.id, "anteckning") == 1
        assert rad["text"] == "" and rad["kalla"] == lagring.GRAVSTEN
        assert (await k.get(f"{V1}/notes", params={"only_deleted": "true"})).json()["data"] == []


async def test_papperskorgen_toms_aven_nar_en_annan_sorts_post_raderas(buddy, storage):
    """Löftet om 30 dagar hänger inte på att ännu en post av samma sort raderas."""
    async with buddy.klient() as k:
        bolag = await _bolag(k)
        anteckning = (await k.post(f"{V1}/notes", json={"body": "Gammal", "company_id": bolag["id"]})).json()
        bilaga = (await _ladda_upp(k, company_id=bolag["id"])).json()
        uppgift = (await k.post(f"{V1}/tasks", json={"title": "Ring"})).json()
        await k.delete(f"{V1}/notes/{anteckning['id']}")
        await k.delete(f"{V1}/attachments/{bilaga['id']}")
        gammal = (datetime.now(timezone.utc) - timedelta(days=31)).isoformat()
        lagring._minne(storage, "crm_anteckningar")[anteckning["id"]]["raderad_at"] = gammal
        lagring._minne(storage, "crm_bilagor")[bilaga["id"]]["raderad_at"] = gammal
        await k.delete(f"{V1}/tasks/{uppgift['id']}")
        assert lagring._minne(storage, "crm_anteckningar")[anteckning["id"]]["text"] == ""
        assert lagring._minne(storage, "crm_bilagor")[bilaga["id"]]["innehall"] == b""
        assert await lagring.bilagornas_storlek(storage, buddy.id) == 0


async def test_gdpr_skriptet_raderar_det_som_toms_med_personen():
    """scripts/gdpr_radera.py raderar personen direkt i databasen och går inte
    genom gor_gravsten. Det som töms med personen i appen ska därför raderas
    av skriptet före personen, annars står det kvar med person_id = null."""
    import importlib.util
    import sys
    from pathlib import Path

    skript = Path(__file__).resolve().parents[3] / "scripts"
    sys.path.insert(0, str(skript))
    try:
        spec = importlib.util.spec_from_file_location("gdpr_radera_crm", skript / "gdpr_radera.py")
        gdpr = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(gdpr)
    finally:
        sys.path.remove(str(skript))
    ordning = [tabell for tabell, *_ in gdpr.TABELLER]
    for beroende in lagring._TOMS_MED:
        tabell = lagring._OBJEKTTABELL[beroende]
        assert tabell in ordning, tabell
        assert ordning.index(tabell) < ordning.index("crm_personer"), tabell
        villkor = next(v for t, v, _ in gdpr.TABELLER if t == tabell)
        assert "person_id in" in villkor, tabell
