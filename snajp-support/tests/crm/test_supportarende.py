"""En synkkörning med fel blir ett plattformsärende (Antons svar 2026-11-26).

Rapporten (migration 163) blir av sig själv ett ärende i plattformsärendena
(migration 156), och numret står på körningen. Ärendets text bär koder och
tal, aldrig ett värde. Samma anslutning som faller igen ger samma ärende.
"""

from __future__ import annotations

import asyncio
import json
import uuid

import pytest

from app.config import get_settings
from app.crm import supportrapport

from .conftest import ORGNR_A

V1 = "/api/crm/v1"
pytestmark = pytest.mark.anyio

ADRESS = "anna.berg@bolaget.se"
TELEFON = "070-123 45 67"

_FEL = [
    {"id": "1", "name": "Rent AB", "org_number": ORGNR_A},
    {"id": "2", "name": "Fel Telefon AB", "phone": "12 34 56 7", "email": "inte en adress"},
    {"id": "3"},                                                # saknar namn
]


@pytest.fixture
def mejl(monkeypatch):
    """Mejlen som skulle ha gått till Snajp, i ordning."""
    skickade: list[dict] = []

    async def _skicka(**kw):
        skickade.append(kw)
        return True

    monkeypatch.setattr(supportrapport, "skicka_felrapport", _skicka)
    return skickade


async def _vanta() -> None:
    """Mejlen går efter svaret, i egna uppgifter."""
    if supportrapport._pagaende:
        await asyncio.gather(*list(supportrapport._pagaende))


def _arbetsyta(storage, kund) -> str:
    ws = str(uuid.uuid4())
    storage.__dict__.setdefault("_crm_arbetsytor", {})[kund.id] = ws
    return ws


async def _synka(kund, items, namn: str = "egen") -> dict:
    async with kund.klient() as k:
        await k.post(f"{V1}/connections", json={"name": namn, "system": "generisk"})
        svar = await k.post(f"{V1}/sync/companies", json={"connection": namn, "items": items})
        assert svar.status_code == 200, svar.text
        return svar.json()["run"]


async def _arenden(storage) -> list[dict]:
    return await storage.list_plattformsarenden(rapportor_user_id=supportrapport.SYSTEMRAPPORTOR)


async def test_ett_arende_skapas_med_ratt_falt_och_korningen_bar_numret(app, buddy, storage, mejl):
    ws = _arbetsyta(storage, buddy)
    korning = await _synka(buddy, _FEL)
    (arende,) = await _arenden(storage)
    assert korning["support"]["ticket"] == arende["nummer"]
    assert (arende["rapportor_user_id"], arende["rapportor_namn"]) == (
        str(uuid.uuid5(uuid.NAMESPACE_URL, "https://snajp.se/crm/synk")), "Snajp CRM, synken")
    assert (arende["kund_workspace_id"], arende["kund_tenant_slug"], arende["vy"], arende["roll"],
            arende["besok_av_admin"], arende["sida"]) == (ws, "buddy", "crm", "system", False, "/crm/synk")
    assert arende["gjorde"] == "Synk från egen (delta)" and arende["vantade"] == "Att alla poster kom in."
    assert arende["status"] == "mottagen"
    rader = arende["hande"].splitlines()
    assert "Totalt 3, skapade 2, uppdaterade 0, hoppade 1." in rader
    assert rader[rader.index("Felkoder, störst först:") + 1:-1] == [
        "- epost_ogiltig: 1", "- saknar_namn: 1", "- telefon_saknar_riktnummer: 1"]
    assert rader[-1] == f"Hela rapporten: GET /api/admin/crm/supportrapporter/{buddy.id}/{korning['id']}"
    # Numret står kvar när körningen läses igen, och ett nytt ärende mejlas till Snajp.
    async with buddy.klient() as k:
        assert (await k.get(f"{V1}/sync/runs/{korning['id']}")).json()["support"]["ticket"] == arende["nummer"]
    await _vanta()
    assert mejl == []  # hjälpens kund finns inte i testet: mejlet hoppas över, inget fälls
    await storage.create_tenant(slug=get_settings().hjalp_tenant_slug, name="Snajp Hjälp")
    await _synka(buddy, _FEL, namn="andra")
    await _vanta()
    assert [m["nummer"] for m in mejl] == [a["nummer"] for a in await _arenden(storage) if a["gjorde"].startswith(
        "Synk från andra")]


async def test_ingen_personuppgift_star_i_arendet(buddy, storage, mejl):
    _arbetsyta(storage, buddy)
    await _synka(buddy, [{"id": "9", "name": "Anna Bergs Bygg AB", "email": f"{ADRESS} x", "phone": TELEFON[:5]},
                         {"id": "8", "name": "Kalle AB", "email": ADRESS, "phone": "12 34"}])
    (arende,) = await _arenden(storage)
    text = json.dumps(arende, ensure_ascii=False)
    for bit in (ADRESS, "anna.berg", TELEFON[:5], "12 34", "Anna Bergs", "Kalle", '"9"', "aaaa"):
        assert bit not in text, bit
    # Rapporten bär formen av värdet, ärendet inte ens den.
    assert "epost_ogiltig" in arende["hande"]


async def test_samma_anslutning_tva_ganger_ger_ett_arende_och_en_intern_handelse(buddy, storage, mejl):
    _arbetsyta(storage, buddy)
    await storage.create_tenant(slug=get_settings().hjalp_tenant_slug, name="Snajp Hjälp")
    forsta = await _synka(buddy, _FEL)
    andra = await _synka(buddy, _FEL)
    (arende,) = await _arenden(storage)
    assert forsta["support"]["ticket"] == andra["support"]["ticket"] == arende["nummer"]
    assert arende["status"] == "mottagen"
    (handelse,) = [h for h in arende["handelser"] if h["typ"] != "skapad"]
    assert handelse["synlig_for_kund"] is False and handelse["aktor"] == "system"
    assert handelse["meddelande"] == f"Samma anslutning föll igen i körning {andra['id']}: 2 poster"
    await _vanta()
    assert len(mejl) == 1  # bara det nya ärendet mejlas
    # En annan anslutning hos samma kund är ett annat ärende.
    await _synka(buddy, _FEL, namn="hubspot-test")
    assert len(await _arenden(storage)) == 2


async def test_ett_stangt_arende_ger_ett_nytt(buddy, storage, mejl):
    _arbetsyta(storage, buddy)
    forsta = await _synka(buddy, _FEL)
    (arende,) = await _arenden(storage)
    await storage.andra_plattformsarende(arende["id"], status="stangd",
                                         handelse={"typ": "status", "aktor": "plattformsadmin"})
    andra = await _synka(buddy, _FEL)
    assert andra["support"]["ticket"] != forsta["support"]["ticket"]
    assert len(await _arenden(storage)) == 2


async def test_ett_gammalt_oppet_arende_hittas_bakom_manga_nyare(buddy, storage, mejl):
    """Granskningens fynd: återanvändningen letade bland de 500 nyaste
    ärendena från synken, över alla kunder och stängda inräknade. Ett äldre
    öppet ärende syns nu ändå, och den första händelsen är synkens, intern."""
    _arbetsyta(storage, buddy)
    forsta = await _synka(buddy, _FEL)
    (arende,) = await _arenden(storage)
    assert [(h["typ"], h["aktor"], h["synlig_for_kund"]) for h in arende["handelser"]] == [
        ("skapad", "system", False)]
    for i in range(510):
        nytt = await storage.skapa_plattformsarende({
            "rapportor_user_id": supportrapport.SYSTEMRAPPORTOR, "kund_workspace_id": str(uuid.uuid4()),
            "kund_tenant_slug": f"kund-{i}", "vy": "crm", "roll": "system", "sida": "/crm/synk",
            "gjorde": "Synk från egen (delta)", "hande": "x"}, aktor="system", synlig_for_kund=False)
        if i % 2:
            await storage.andra_plattformsarende(nytt["id"], status="stangd",
                                                 handelse={"typ": "status", "aktor": "plattformsadmin"})
    andra = await _synka(buddy, _FEL)
    assert andra["support"]["ticket"] == forsta["support"]["ticket"]
    assert len(await storage.list_plattformsarenden(rapportor_user_id=supportrapport.SYSTEMRAPPORTOR,
                                                    limit=1000)) == 511


async def test_ett_arende_som_stangs_under_skrivningen_ger_ett_nytt(buddy, storage, monkeypatch, mejl):
    """Granskningens fynd: svaret från andra_plattformsarende ignorerades, och
    körningen fick numret på ett ärende som just stängts utan händelsen."""
    _arbetsyta(storage, buddy)
    forsta = await _synka(buddy, _FEL)
    (arende,) = await _arenden(storage)
    riktig = storage.andra_plattformsarende

    async def _stangs_forst(arende_id, **kw):
        # En admin hinner stänga ärendet: den villkorade skrivningen säger nej.
        await riktig(arende_id, status="stangd", handelse={"typ": "status", "aktor": "plattformsadmin"})
        return await riktig(arende_id, **kw)

    monkeypatch.setattr(storage, "andra_plattformsarende", _stangs_forst)
    andra = await _synka(buddy, _FEL)
    assert andra["support"]["ticket"] not in (None, forsta["support"]["ticket"])
    stangt = await storage.hamta_plattformsarende(arende["id"])
    assert stangt["status"] == "stangd" and not [h for h in stangt["handelser"] if h["typ"] == "synk"]


def test_antalet_poster_ar_ett_golv_nar_felloggen_ar_full():
    from app.crm import lagring

    rad = {"objekt": "bolag", "orsak": "saknar_namn"}
    assert supportrapport._antal_poster({"fel": [rad] * 3}) == "3"
    assert supportrapport._antal_poster({"fel": [rad] * lagring.MAX_FEL}) == f"minst {lagring.MAX_FEL}"
    # Med flit överhoppade rader räknas inte, men en full logg är fortfarande ett golv.
    privat = {"objekt": "bolag", "orsak": "privatperson"}
    assert supportrapport._antal_poster({"fel": [privat] * (lagring.MAX_FEL - 2) + [rad] * 2}) == "minst 2"


async def test_utan_fel_eller_med_bara_privatpersoner_blir_det_inget_arende(buddy, storage, mejl):
    _arbetsyta(storage, buddy)
    ren = await _synka(buddy, [_FEL[0]])
    privat = await _synka(buddy, [{"id": "5", "name": "Anna Berg", "is_private_person": True, "email": ADRESS}])
    assert ren["support"] is None and privat["support"] is None
    assert await _arenden(storage) == []


async def test_en_kund_utan_arbetsyta_far_inget_arende_och_rapporten_vantar(app, buddy, storage, mejl):
    korning = await _synka(buddy, _FEL)
    assert korning["support"]["forwarded_at"] and korning["support"]["ticket"] is None
    assert await _arenden(storage) == []
    vantar = await supportrapport.lista(storage, bara_utan_arende=True)
    assert [r["korning_id"] for r in vantar] == [korning["id"]]


async def test_ett_fel_i_arendet_faller_inte_korningen(buddy, storage, monkeypatch, mejl):
    _arbetsyta(storage, buddy)

    async def _trasig(falt, **kw):
        raise RuntimeError("databasen svarar inte")

    monkeypatch.setattr(storage, "skapa_plattformsarende", _trasig)
    korning = await _synka(buddy, _FEL)
    assert korning["status"] == "completed" and korning["counts"]["created"] == 2
    assert korning["support"]["forwarded_at"] and korning["support"]["ticket"] is None


async def test_tva_kunder_far_var_sitt_arende_och_ser_aldrig_varandras_nummer(buddy, annan, storage, mejl):
    _arbetsyta(storage, buddy)
    _arbetsyta(storage, annan)
    hos_buddy = await _synka(buddy, _FEL)
    hos_annan = await _synka(annan, _FEL)
    arenden = {a["kund_tenant_slug"]: a for a in await _arenden(storage)}
    assert set(arenden) == {"buddy", "annan-kund"}
    assert hos_buddy["support"]["ticket"] == arenden["buddy"]["nummer"]
    assert hos_annan["support"]["ticket"] == arenden["annan-kund"]["nummer"]
    assert hos_buddy["support"]["ticket"] != hos_annan["support"]["ticket"]
    async with annan.klient() as k:
        assert (await k.get(f"{V1}/sync/runs/{hos_buddy['id']}")).status_code == 404
        listan = json.dumps((await k.get(f"{V1}/sync/runs")).json())
        assert arenden["buddy"]["nummer"] not in listan and arenden["annan-kund"]["nummer"] in listan


async def test_flaggan_av_ger_inget_arende(buddy, storage, monkeypatch, mejl):
    _arbetsyta(storage, buddy)
    monkeypatch.setattr(get_settings(), "crm_supportarenden", False)
    korning = await _synka(buddy, _FEL)
    assert korning["support"]["forwarded_at"] and korning["support"]["ticket"] is None
    assert await _arenden(storage) == []


def test_flaggan_ar_pa_som_standard(monkeypatch):
    from app.config import Settings

    monkeypatch.delenv("CRM_SUPPORTARENDEN", raising=False)
    assert Settings(_env_file=None).crm_supportarenden is True
    monkeypatch.setenv("CRM_SUPPORTARENDEN", "0")
    assert Settings(_env_file=None).crm_supportarenden is False
