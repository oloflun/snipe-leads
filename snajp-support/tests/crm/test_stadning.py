"""Städjobbet: papperskorgen töms efter 30 dagar utan att kunden skriver något.

Förut tömdes korgen bara vid nästa skrivning hos kunden. Här visas att jobbet
tömmer det utgångna, låter det yngre stå, håller sig till en kund i taget och
att ett fel hos en kund inte stoppar nästa.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone

import pytest

from app.crm import lagring, stadning

pytestmark = pytest.mark.anyio


def _sedan(dagar: int) -> str:
    return (datetime.now(timezone.utc) - timedelta(days=dagar)).isoformat()


async def _raderad(storage, tenant_id: str, objekt: str, falt: dict, dagar: int) -> str:
    post = await lagring.skapa_post(storage, tenant_id, objekt, falt)
    await lagring.uppdatera_post(storage, tenant_id, objekt, post["id"], {"raderad_at": _sedan(dagar)})
    return post["id"]


async def test_raderad_for_31_dagar_sedan_toms_och_29_star_kvar(storage, buddy, annan):
    gammal = await _raderad(storage, buddy.id, "bolag", {"namn": "Gammal AB"}, 31)
    ung = await _raderad(storage, buddy.id, "bolag", {"namn": "Ung AB"}, 29)
    anteckning = await _raderad(storage, buddy.id, "anteckning", {"text": "Ring Anna", "bolag_id": ung}, 31)
    hos_annan = await _raderad(storage, annan.id, "person", {"fornamn": "Eva", "epost": "eva@annan.se"}, 40)

    totalt = await stadning.kor_varv(storage)

    assert totalt == {"bolag": 1, "anteckning": 1, "person": 1}
    tomd = await lagring.hamta_post(storage, buddy.id, "bolag", gammal, med_raderade=True)
    assert tomd["kalla"] == lagring.GRAVSTEN and tomd["namn"] == ""
    kvar = await lagring.hamta_post(storage, buddy.id, "bolag", ung, med_raderade=True)
    assert kvar["namn"] == "Ung AB" and kvar["kalla"] != lagring.GRAVSTEN
    assert (await lagring.hamta_post(storage, buddy.id, "anteckning", anteckning, med_raderade=True))["text"] == ""
    person = await lagring.hamta_post(storage, annan.id, "person", hos_annan, med_raderade=True)
    assert person["epost"] is None and person["kalla"] == lagring.GRAVSTEN
    # Ett andra varv har inget att göra.
    assert await stadning.kor_varv(storage) == {}
    assert await stadning.kunder_att_tomma(storage) == []


async def test_bara_kunder_med_nagot_att_tomma_besoks(storage, buddy, annan):
    await _raderad(storage, buddy.id, "uppgift", {"titel": "Gammal"}, 45)
    await _raderad(storage, annan.id, "uppgift", {"titel": "Ny"}, 2)
    assert await stadning.kunder_att_tomma(storage) == [buddy.id]
    assert await stadning.har_utgangna(storage, annan.id) is False


async def test_ett_fel_hos_den_forsta_kunden_stoppar_inte_den_andra(storage, buddy, annan, monkeypatch, caplog):
    await _raderad(storage, buddy.id, "bolag", {"namn": "Hemligt Namn AB"}, 31)
    andra = await _raderad(storage, annan.id, "bolag", {"namn": "Annan AB"}, 31)
    riktig = lagring.tom_papperskorg

    async def faller_for_buddy(storage_, tenant_id, objekt, **kw):
        if tenant_id == buddy.id:
            raise RuntimeError("databasen svarar inte")
        return await riktig(storage_, tenant_id, objekt, **kw)

    monkeypatch.setattr(lagring, "tom_papperskorg", faller_for_buddy)
    with caplog.at_level(logging.INFO, logger="snajp-support.crm.stadning"):
        totalt = await stadning.kor_varv(storage)
    assert totalt == {"bolag": 1}
    assert (await lagring.hamta_post(storage, annan.id, "bolag", andra, med_raderade=True))["kalla"] == lagring.GRAVSTEN
    # Loggen säger antal per objekt, aldrig innehåll.
    assert "bolag 1" in caplog.text and "Hemligt Namn" not in caplog.text and "Annan AB" not in caplog.text


async def test_begransad_adress_toms_inte_och_olasbar_lista_tommer_inga_personer(storage, buddy, monkeypatch):
    begransad = await _raderad(storage, buddy.id, "person", {"fornamn": "B", "epost": "b@x.se"}, 31)
    vanlig = await _raderad(storage, buddy.id, "person", {"fornamn": "V", "epost": "v@x.se"}, 31)
    uppgift = await _raderad(storage, buddy.id, "uppgift", {"titel": "Gammal"}, 31)
    storage.behandlingsbegransningar.append({"email": "B@x.se", "havd_at": None})

    async def kan_inte_lasas(tenant_id):
        raise RuntimeError("nere")

    monkeypatch.setattr(storage, "list_begransade", kan_inte_lasas)
    assert await stadning.tom_for_kund(storage, buddy.id) == {"uppgift": 1}
    assert (await lagring.hamta_post(storage, buddy.id, "person", vanlig, med_raderade=True))["epost"] == "v@x.se"
    monkeypatch.undo()

    assert await stadning.tom_for_kund(storage, buddy.id) == {"person": 1}
    assert (await lagring.hamta_post(storage, buddy.id, "person", begransad, med_raderade=True))["epost"] == "b@x.se"
    assert (await lagring.hamta_post(storage, buddy.id, "uppgift", uppgift, med_raderade=True))["titel"] == ""


async def test_fler_an_tvahundra_toms_i_samma_varv(storage, buddy):
    for i in range(205):
        await _raderad(storage, buddy.id, "aktivitet", {"rubrik": f"Samtal {i}", "tid": _sedan(40)}, 31)
    assert await stadning.tom_for_kund(storage, buddy.id) == {"aktivitet": 205}


async def test_jobbet_kor_ett_varv_och_overlever_ett_fel(storage, monkeypatch):
    varv = []

    async def kor(storage_):
        varv.append(1)
        if len(varv) == 1:
            raise RuntimeError("första varvet faller")
        return {}

    monkeypatch.setattr(stadning, "kor_varv", kor)

    class Tillstand:
        pass

    tillstand = Tillstand()
    tillstand.storage = storage
    uppgift = asyncio.create_task(stadning.run_stadjobb(tillstand, intervall=0.01, fordrojning=0))
    for _ in range(100):
        if len(varv) >= 2:
            break
        await asyncio.sleep(0.01)
    uppgift.cancel()
    with pytest.raises(asyncio.CancelledError):
        await uppgift
    assert len(varv) >= 2


def test_flaggan_ar_pa_som_standard_och_gar_att_stanga_av(monkeypatch):
    from app.config import Settings

    monkeypatch.delenv("CRM_STADJOBB", raising=False)
    assert Settings(_env_file=None).crm_stadjobb is True
    monkeypatch.setenv("CRM_STADJOBB", "0")
    assert Settings(_env_file=None).crm_stadjobb is False
