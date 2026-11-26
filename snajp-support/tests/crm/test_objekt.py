"""Affärer och affärens steg (migration 164): stegen, tavlan, flytten,
avslutad_at, händelserna och kundisoleringen.

Uppgifter, anteckningar, aktiviteter, bilagor och kaskaden vid tömning står i
test_objekt_ovriga.py.
"""

from __future__ import annotations

import pytest

from app.crm import lagring, objekt

V1 = "/api/crm/v1"
pytestmark = pytest.mark.anyio


async def _steg(k) -> dict[str, dict]:
    """Kundens steg per namn."""
    return {s["name"]: s for s in (await k.get(f"{V1}/deal-stages")).json()["data"]}


async def _affar(k, namn: str, **falt) -> dict:
    svar = await k.post(f"{V1}/deals", json={"name": namn, **falt})
    assert svar.status_code == 201, svar.text
    return svar.json()


async def _ordning(k, steg_id: str) -> list[str]:
    tavla = (await k.get(f"{V1}/deals/board")).json()["stages"]
    return [a["name"] for a in next(s for s in tavla if s["id"] == steg_id)["deals"]]


# -- Stegen ------------------------------------------------------------------


async def test_standardstegen_skapas_en_gang_per_kund(buddy, annan, storage, monkeypatch):
    async with buddy.klient() as k:
        forsta = (await k.get(f"{V1}/deal-stages")).json()["data"]
        andra = (await k.get(f"{V1}/deal-stages")).json()["data"]
    assert [(s["name"], s["probability"], s["type"]) for s in forsta] == [
        ("Ny", 10, "open"), ("Kvalificerad", 25, "open"), ("Möte bokat", 40, "open"),
        ("Offert skickad", 60, "open"), ("Förhandling", 80, "open"), ("Vunnen", 100, "won"),
        ("Förlorad", 0, "lost")]
    assert [s["id"] for s in andra] == [s["id"] for s in forsta]
    # En andra läsning som hann se en tom tabell innan den första skrev: namnet
    # är unikt, så den får en krock per steg i stället för en ny uppsättning.
    riktig = lagring._valj
    sett = {"tomt": False}

    async def sag_tomt(storage_, tenant_id, tabell, **kw):
        if tabell == "crm_affarssteg" and not sett["tomt"]:
            sett["tomt"] = True
            return []
        return await riktig(storage_, tenant_id, tabell, **kw)

    monkeypatch.setattr(lagring, "_valj", sag_tomt)
    efter = await objekt.lista_steg(storage, buddy.id)
    monkeypatch.setattr(lagring, "_valj", riktig)
    assert sett["tomt"] and [s["id"] for s in efter] == [s["id"] for s in forsta]
    assert len([r for r in lagring._minne(storage, "crm_affarssteg").values() if r["tenant_id"] == buddy.id]) == 7
    # Den andra kunden får sin egen uppsättning.
    async with annan.klient() as k:
        egna = (await k.get(f"{V1}/deal-stages")).json()["data"]
    assert len(egna) == 7 and not {s["id"] for s in egna} & {s["id"] for s in forsta}


async def test_en_lasning_mitt_i_den_forsta_far_hela_uppsattningen(buddy, storage):
    """Den första läsningen skriver stegen ett i taget. En läsning som ser en
    del av dem fyller på resten i stället för att svara utan vunnet och förlorat."""
    for position, (namn, sannolikhet, typ) in enumerate(objekt.STANDARDSTEG[:2]):
        await lagring._in(storage, buddy.id, "crm_affarssteg",
                          {"namn": namn, "position": position, "sannolikhet": sannolikhet, "typ": typ})
    async with buddy.klient() as k:
        steg = (await k.get(f"{V1}/deal-stages")).json()["data"]
        assert [s["name"] for s in steg] == [namn for namn, *_ in objekt.STANDARDSTEG]
        tavla = (await k.get(f"{V1}/deals/board")).json()["stages"]
        assert {s["type"] for s in tavla} == {"open", "won", "lost"}


async def test_steg_byter_namn_ordnas_om_laggs_till_och_tas_bort(buddy):
    async with buddy.klient() as k:
        ny = await k.post(f"{V1}/deal-stages", json={"name": "Demo", "probability": 50, "color": "blue"})
        assert ny.status_code == 201 and ny.json()["position"] == 7 and ny.json()["type"] == "open"
        krock = await k.post(f"{V1}/deal-stages", json={"name": "demo"})
        assert krock.status_code == 409 and krock.json()["detail"]["code"] == "conflict"
        utan_namn = await k.post(f"{V1}/deal-stages", json={"probability": 5})
        assert utan_namn.status_code == 422 and utan_namn.json()["detail"]["fields"][0]["field"] == "name"
        andrad = await k.patch(f"{V1}/deal-stages/{ny.json()['id']}", json={"name": "Demo bokad"})
        assert andrad.json()["name"] == "Demo bokad"
        ids = [s["id"] for s in (await k.get(f"{V1}/deal-stages")).json()["data"]]
        omvand = (await k.post(f"{V1}/deal-stages/reorder", json={"ids": ids[::-1]})).json()["data"]
        assert [s["id"] for s in omvand] == ids[::-1] and [s["position"] for s in omvand] == list(range(8))
        saknas = await k.post(f"{V1}/deal-stages/reorder", json={"ids": ids[:-1]})
        assert saknas.status_code == 422 and saknas.json()["detail"]["code"] == "invalid_fields"
        assert (await k.delete(f"{V1}/deal-stages/{ny.json()['id']}")).status_code == 204
        assert len((await k.get(f"{V1}/deal-stages")).json()["data"]) == 7
        assert (await k.delete(f"{V1}/deal-stages/{ny.json()['id']}")).status_code == 404


async def test_steg_med_affarer_och_det_sista_av_sin_typ_star_kvar(buddy):
    async with buddy.klient() as k:
        steg = await _steg(k)
        affar = await _affar(k, "Takbyte")
        svar = await k.delete(f"{V1}/deal-stages/{steg['Ny']['id']}")
        assert svar.status_code == 409 and svar.json()["detail"]["code"] == "stage_in_use"
        # En raderad affär går att återställa, och steget behövs då fortfarande.
        await k.delete(f"{V1}/deals/{affar['id']}")
        assert (await k.delete(f"{V1}/deal-stages/{steg['Ny']['id']}")).json()["detail"]["code"] == "stage_in_use"
        for namn in ("Vunnen", "Förlorad"):
            svar = await k.delete(f"{V1}/deal-stages/{steg[namn]['id']}")
            assert svar.status_code == 409 and svar.json()["detail"]["code"] == "stage_required", namn
        svar = await k.patch(f"{V1}/deal-stages/{steg['Vunnen']['id']}", json={"type": "open"})
        assert svar.status_code == 409 and svar.json()["detail"]["code"] == "stage_required"
        # Ett tomt öppet steg går bra att ta bort: fyra öppna finns kvar.
        assert (await k.delete(f"{V1}/deal-stages/{steg['Kvalificerad']['id']}")).status_code == 204
        # Ett andra vunnet steg gör det första borttagbart.
        extra = (await k.post(f"{V1}/deal-stages", json={"name": "Vunnen via partner", "type": "won"})).json()
        assert (await k.delete(f"{V1}/deal-stages/{steg['Vunnen']['id']}")).status_code == 204
        assert (await k.delete(f"{V1}/deal-stages/{extra['id']}")).json()["detail"]["code"] == "stage_required"


# -- Affärerna ---------------------------------------------------------------


async def test_affar_skapas_andras_raderas_och_aterstalls(buddy):
    async with buddy.klient() as k:
        steg = await _steg(k)
        bolag = (await k.post(f"{V1}/companies", json={"name": "Bygg AB"})).json()
        person = (await k.post(f"{V1}/people", json={"email": "vd@bygg.se", "company_id": bolag["id"]})).json()
        affar = await _affar(k, "Takbyte", company_id=bolag["id"], person_id=person["id"], amount=125000,
                             expected_close_date="31/12/2026", custom={"offertnr": "O-7"})
        assert affar["stage_id"] == steg["Ny"]["id"] and affar["currency"] == "SEK" and affar["closed_at"] is None
        assert affar["expected_close_date"] == "2026-12-31" and affar["custom"] == {"offertnr": "O-7"}
        assert affar["source"] == "api" and affar["probability"] is None
        andrad = (await k.patch(f"{V1}/deals/{affar['id']}", json={"amount": 150000, "probability": 70,
                                                                    "currency": "eur"})).json()
        assert (andrad["amount"], andrad["probability"], andrad["currency"]) == (150000, 70, "EUR")
        svar = await k.patch(f"{V1}/deals/{affar['id']}", json={"currency": "kronor"})
        assert svar.status_code == 422 and svar.json()["detail"]["fields"] == [
            {"field": "currency", "code": "valuta_ogiltig"}]
        svar = await k.patch(f"{V1}/deals/{affar['id']}", json={"name": None})
        assert svar.status_code == 422 and svar.json()["detail"]["fields"][0] == {"field": "name", "code": "saknas"}
        assert (await k.post(f"{V1}/deals", json={"amount": 5})).status_code == 422
        assert (await k.delete(f"{V1}/deals/{affar['id']}")).status_code == 204
        assert (await k.get(f"{V1}/deals/{affar['id']}")).status_code == 404
        korg = (await k.get(f"{V1}/deals", params={"only_deleted": "true"})).json()["data"]
        assert [a["id"] for a in korg] == [affar["id"]] and korg[0]["purge_at"]
        assert (await k.post(f"{V1}/deals/{affar['id']}/restore")).json()["deleted_at"] is None
        assert (await k.delete(f"{V1}/deals/{affar['id']}", params={"permanent": "true"})).status_code == 204
        tomd = (await k.get(f"{V1}/deals/{affar['id']}", params={"include_deleted": "true"})).json()
        assert tomd["name"] == "" and tomd["amount"] is None and tomd["company_id"] is None
        assert (await k.post(f"{V1}/deals/{affar['id']}/restore")).status_code == 410
        assert (await k.get(f"{V1}/deals/inte-ett-uuid")).status_code == 404


async def test_affarer_sorteras_sidindelas_och_filtreras(buddy):
    async with buddy.klient() as k:
        steg = await _steg(k)
        bolag = (await k.post(f"{V1}/companies", json={"name": "Bygg AB"})).json()
        await _affar(k, "Cembalo", company_id=bolag["id"])
        await _affar(k, "Akvarium", stage_id=steg["Möte bokat"]["id"])
        person = (await k.post(f"{V1}/people", json={"email": "vd@bygg.se"})).json()
        await _affar(k, "Balkong", company_id=bolag["id"], owner="Sebbe", person_id=person["id"])
        sida = (await k.get(f"{V1}/deals", params={"sort": "name", "limit": 2})).json()
        assert [a["name"] for a in sida["data"]] == ["Akvarium", "Balkong"]
        sista = (await k.get(f"{V1}/deals", params={"sort": "name", "limit": 2, "cursor": sida["next_cursor"]})).json()
        assert [a["name"] for a in sista["data"]] == ["Cembalo"] and sista["next_cursor"] is None
        senast = (await k.get(f"{V1}/deals", params={"sort": "-updated"})).json()["data"]
        assert [a["name"] for a in senast] == ["Balkong", "Akvarium", "Cembalo"]
        per_bolag = (await k.get(f"{V1}/deals", params={"company_id": bolag["id"], "sort": "name"})).json()["data"]
        assert [a["name"] for a in per_bolag] == ["Balkong", "Cembalo"]
        per_steg = (await k.get(f"{V1}/deals", params={"stage_id": steg["Möte bokat"]["id"]})).json()["data"]
        assert [a["name"] for a in per_steg] == ["Akvarium"]
        per_person = (await k.get(f"{V1}/deals", params={"person_id": person["id"]})).json()["data"]
        assert [a["name"] for a in per_person] == ["Balkong"]
        assert [a["name"] for a in (await k.get(f"{V1}/deals", params={"q": "sebb"})).json()["data"]] == ["Balkong"]
        assert (await k.get(f"{V1}/deals", params={"sort": "due"})).status_code == 422


# -- Tavlan ------------------------------------------------------------------


async def test_flytt_inom_och_mellan_steg_ger_ratt_ordning_och_summa(buddy):
    async with buddy.klient() as k:
        steg = await _steg(k)
        ny, mote = steg["Ny"]["id"], steg["Möte bokat"]["id"]
        a = await _affar(k, "A", amount=100)
        b = await _affar(k, "B", amount=200)
        c = await _affar(k, "C", amount=400, currency="EUR")
        assert await _ordning(k, ny) == ["A", "B", "C"]
        await k.post(f"{V1}/deals/{c['id']}/move", json={"stage_id": ny, "before_id": a["id"]})
        assert await _ordning(k, ny) == ["C", "A", "B"]
        await k.post(f"{V1}/deals/{a['id']}/move", json={"stage_id": ny, "after_id": b["id"]})
        assert await _ordning(k, ny) == ["C", "B", "A"]
        await k.post(f"{V1}/deals/{b['id']}/move", json={"stage_id": mote})
        await k.post(f"{V1}/deals/{c['id']}/move", json={"stage_id": mote, "before_id": b["id"]})
        assert await _ordning(k, ny) == ["A"] and await _ordning(k, mote) == ["C", "B"]
        tavla = {s["name"]: s for s in (await k.get(f"{V1}/deals/board")).json()["stages"]}
        assert (tavla["Ny"]["count"], tavla["Ny"]["amount_total"]) == (1, 100)
        assert tavla["Möte bokat"]["amount_by_currency"] == {"EUR": 400, "SEK": 200}
        assert tavla["Möte bokat"]["amount_total"] == 600 and tavla["Vunnen"]["count"] == 0
        assert [s["name"] for s in tavla.values()][0] == "Ny" and len(tavla) == 7
        # Grannen ska stå i steget dit affären flyttas, och bara en av before och after.
        svar = await k.post(f"{V1}/deals/{a['id']}/move", json={"stage_id": ny, "before_id": b["id"]})
        assert svar.status_code == 422 and svar.json()["detail"]["fields"][0]["field"] == "before_id"
        svar = await k.post(f"{V1}/deals/{a['id']}/move",
                            json={"stage_id": mote, "before_id": b["id"], "after_id": c["id"]})
        assert svar.status_code == 422
        svar = await k.post(f"{V1}/deals/{a['id']}/move", json={"stage_id": "00000000-0000-0000-0000-000000000000"})
        assert svar.status_code == 422 and svar.json()["detail"]["code"] == "stage_not_found"
        # En raderad affär syns inte på tavlan.
        await k.delete(f"{V1}/deals/{b['id']}")
        assert await _ordning(k, mote) == ["C"]


async def test_luckan_mellan_tva_kort_jamnas_ut(buddy, storage):
    async with buddy.klient() as k:
        ny = (await _steg(k))["Ny"]["id"]
        a, b, c = [await _affar(k, namn) for namn in "ABC"]
        minne = lagring._minne(storage, "crm_affarer")
        minne[a["id"]]["position"], minne[b["id"]]["position"] = 1.0, 1.0 + 1e-9
        flyttad = (await k.post(f"{V1}/deals/{c['id']}/move", json={"stage_id": ny, "before_id": b["id"]})).json()
        assert await _ordning(k, ny) == ["A", "C", "B"]
        assert minne[a["id"]]["position"] < flyttad["position"] < minne[b["id"]]["position"]


async def test_vunnen_och_forlorad_satter_avslutad_at_och_oppet_nollar(buddy):
    async with buddy.klient() as k:
        steg = await _steg(k)
        affar = await _affar(k, "Takbyte")
        vunnen = (await k.post(f"{V1}/deals/{affar['id']}/move", json={"stage_id": steg["Vunnen"]["id"]})).json()
        assert vunnen["closed_at"] and vunnen["stage_id"] == steg["Vunnen"]["id"]
        forlorad = (await k.post(f"{V1}/deals/{affar['id']}/move", json={"stage_id": steg["Förlorad"]["id"]})).json()
        assert forlorad["closed_at"] == vunnen["closed_at"]
        tillbaka = (await k.post(f"{V1}/deals/{affar['id']}/move", json={"stage_id": steg["Förhandling"]["id"]})).json()
        assert tillbaka["closed_at"] is None
        via_patch = (await k.patch(f"{V1}/deals/{affar['id']}", json={"stage_id": steg["Vunnen"]["id"]})).json()
        assert via_patch["closed_at"]
        direkt = await _affar(k, "Förlorad direkt", stage_id=steg["Förlorad"]["id"], lost_reason="Pris")
        assert direkt["closed_at"] and direkt["lost_reason"] == "Pris"


# -- Händelser och isolering -------------------------------------------------


async def test_affarens_skrivningar_syns_i_flodet_och_historiken(buddy, annan):
    async with buddy.klient() as k:
        steg = await _steg(k)
        affar = await _affar(k, "Takbyte")
        await k.patch(f"{V1}/deals/{affar['id']}", json={"amount": 5000})
        await k.post(f"{V1}/deals/{affar['id']}/move", json={"stage_id": steg["Vunnen"]["id"]})
        await k.delete(f"{V1}/deals/{affar['id']}")
        await k.post(f"{V1}/deals/{affar['id']}/restore")
        flode = (await k.get(f"{V1}/changes", params={"object": "deal"})).json()["data"]
        assert [(h["object"], h["type"]) for h in flode] == [
            ("deal", "created"), ("deal", "updated"), ("deal", "updated"), ("deal", "deleted"), ("deal", "restored")]
        assert flode[1]["fields"] == ["amount"]
        # Ensam i ett tomt steg: platsen blir densamma, så bara steget och avslutet ändrades.
        assert sorted(flode[2]["fields"]) == ["closed_at", "stage_id"]
        assert all(h["id"] == affar["id"] for h in flode)
        historik = (await k.get(f"{V1}/deals/{affar['id']}/history")).json()["data"]
        assert [h["type"] for h in historik] == ["restored", "deleted", "updated", "updated", "created"]
    async with annan.klient() as k:
        assert (await k.get(f"{V1}/deals/{affar['id']}/history")).status_code == 404
        assert (await k.get(f"{V1}/changes")).json()["data"] == []


async def test_en_kund_ser_och_ror_aldrig_en_annans_affarer(buddy, annan):
    async with buddy.klient() as k:
        steg = await _steg(k)
        bolag = (await k.post(f"{V1}/companies", json={"name": "Bygg AB"})).json()
        person = (await k.post(f"{V1}/people", json={"email": "vd@bygg.se"})).json()
        affar = await _affar(k, "Hemlig affär", company_id=bolag["id"])
    async with annan.klient() as k:
        assert (await k.get(f"{V1}/deals")).json()["data"] == []
        assert (await k.get(f"{V1}/deals", params={"only_deleted": "true"})).json()["data"] == []
        assert all(s["count"] == 0 for s in (await k.get(f"{V1}/deals/board")).json()["stages"])
        for metod, vag, kropp in [("get", f"/deals/{affar['id']}", None),
                                  ("patch", f"/deals/{affar['id']}", {"name": "Kapad"}),
                                  ("delete", f"/deals/{affar['id']}", None),
                                  ("post", f"/deals/{affar['id']}/restore", None),
                                  ("patch", f"/deal-stages/{steg['Ny']['id']}", {"name": "Kapat"}),
                                  ("delete", f"/deal-stages/{steg['Ny']['id']}", None)]:
            svar = await k.request(metod.upper(), f"{V1}{vag}", json=kropp)
            assert svar.status_code == 404, vag
        egna = await _steg(k)
        svar = await k.post(f"{V1}/deals/{affar['id']}/move", json={"stage_id": egna["Ny"]["id"]})
        assert svar.status_code == 404
        for falt_, varde, kod in [("company_id", bolag["id"], "company_not_found"),
                                  ("person_id", person["id"], "person_not_found"),
                                  ("stage_id", steg["Ny"]["id"], "stage_not_found")]:
            svar = await k.post(f"{V1}/deals", json={"name": "Egen", falt_: varde})
            assert svar.status_code == 422 and svar.json()["detail"]["code"] == kod, falt_
    async with buddy.klient() as k:
        assert (await k.get(f"{V1}/deals/{affar['id']}")).json()["name"] == "Hemlig affär"
        assert (await k.get(f"{V1}/deal-stages")).json()["data"][0]["name"] == "Ny"
