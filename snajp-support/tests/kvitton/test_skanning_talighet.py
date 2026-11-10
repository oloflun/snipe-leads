"""Ett mejl som faller stoppar inte skanningen (Fas 0-fyndet H3, 2026-11-09).

Före: skanningen läste mejlen i en slinga utan felhantering. Ett mejl som
föll (en trasig bilaga, ett oväntat modellsvar) kastade ut ur hela
skanningen. Mejlet märktes aldrig som läst, så nästa skanning föll på samma
mejl, och alla mejl efter det i inkorgen lästes aldrig.
"""

from __future__ import annotations

import asyncio

import pytest

from app.kvitton import skanning
from app.kvitton.mejl import FEJKMEJL, MejlkontofelError, MockMejlkonto
from app.kvitton.skanning import skanna_inkorg
from app.storage.memory import MemoryStorage


@pytest.fixture(autouse=True)
def _deterministisk(monkeypatch):
    monkeypatch.setenv("KVITTO_TOLKNING", "deterministisk")
    from app import config

    config.get_settings.cache_clear()
    yield
    config.get_settings.cache_clear()


def _skanna(storage: MemoryStorage):
    return asyncio.run(skanna_inkorg(storage, "t1", MockMejlkonto()))


def _fall_pa(monkeypatch, mejl_id: str, fel: Exception) -> None:
    """Låter hanteringen av ETT mejl kasta; övriga går den riktiga vägen."""
    riktig = skanning.hantera

    async def _hantera(storage, tenant_id, inkommande, **k):
        if inkommande.meddelande_id == mejl_id:
            raise fel
        return await riktig(storage, tenant_id, inkommande, **k)

    monkeypatch.setattr(skanning, "hantera", _hantera)


def _forsta_kvittomejl() -> str:
    referens = _skanna(MemoryStorage())
    return next(h["mejl_id"] for h in referens.handelser if h["utfall"] in ("kvitto", "kvitto_granska"))


def test_ett_mejl_som_faller_stoppar_inte_resten(monkeypatch):
    referens = _skanna(MemoryStorage())
    trasigt = _forsta_kvittomejl()
    _fall_pa(monkeypatch, trasigt, RuntimeError("trasig bilaga"))

    resultat = _skanna(MemoryStorage())

    assert resultat.genomlasta == len(FEJKMEJL) == referens.genomlasta
    utfall = {h["mejl_id"]: h["utfall"] for h in resultat.handelser}
    assert utfall[trasigt] == "fel"
    ovriga = {k: v for k, v in utfall.items() if k != trasigt}
    assert ovriga == {h["mejl_id"]: h["utfall"] for h in referens.handelser if h["mejl_id"] != trasigt}
    assert resultat.misslyckade == 1
    assert resultat.nya_kvitton < referens.nya_kvitton


def test_felhandelsen_bar_avsandare_och_amne_men_inget_internt(monkeypatch):
    trasigt = _forsta_kvittomejl()
    _fall_pa(monkeypatch, trasigt, RuntimeError("psycopg: relation bk_underlag saknas"))

    resultat = _skanna(MemoryStorage())

    handelse = next(h for h in resultat.handelser if h["mejl_id"] == trasigt)
    assert handelse["avsandare"] and "amne" in handelse
    assert "psycopg" not in str(handelse)


def test_ett_fallet_mejl_provas_igen_vid_nasta_skanning(monkeypatch):
    storage = MemoryStorage()
    trasigt = _forsta_kvittomejl()
    _fall_pa(monkeypatch, trasigt, RuntimeError("tillfälligt"))
    _skanna(storage)

    monkeypatch.undo()
    monkeypatch.setenv("KVITTO_TOLKNING", "deterministisk")
    andra = _skanna(storage)

    utfall = {h["mejl_id"]: h["utfall"] for h in andra.handelser}
    assert utfall[trasigt] in ("kvitto", "kvitto_granska")
    assert andra.nya_kvitton == 1


def test_fel_som_galler_hela_skanningen_avbryter_den(monkeypatch):
    """Ett kontofel eller en slut kvot går inte över av att läsa nästa mejl."""
    trasigt = _forsta_kvittomejl()
    _fall_pa(monkeypatch, trasigt, MejlkontofelError("Inloggningen till brevlådan har gått ut."))

    with pytest.raises(MejlkontofelError):
        _skanna(MemoryStorage())
