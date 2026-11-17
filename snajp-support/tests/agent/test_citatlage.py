"""INV-GROUND-003 — i citatläget (`faktakontroll: ordagrant`) består svaret
till kunden av meningar som står ordagrant i en källa, skrivna som de står
där, plus hälsningen och agentens egna frågor. Allt annat stryks av kod.

Funktionstesterna kör ingen modell. Kedjetesterna mockar bara
nätverksgränsen: lagringen, beslutslogiken och grinden är den riktiga vägen.
"""

from __future__ import annotations

import pytest

from app.agent.support_faktagrind import FAST, Kalla, citatsvar, kontrollera, kundtext
from app.storage.memory import MemoryStorage
from tests.agent.test_support_eskalering import (  # noqa: F401 — fixturerna används av pytest
    TENANT,
    _LLM,
    _fake_key,
    _regler,
    _tur,
    anyio_backend,
)

RETUR = Kalla(
    "KB-1",
    "Returer\nÖppet köp gäller i 45 dagar från leverans. Rea-varor omfattas inte av öppet köp.",
)
NAMN = Kalla("KUNDNAMN", "Anna", FAST)


def test_svaret_byggs_av_kallans_meningar():
    svar, strukna = citatsvar(
        "Hej Anna!\nDu kan lämna tillbaka varan utan kvitto. "
        "öppet köp gäller i 45 dagar från leverans! Hoppas det hjälper.",
        [RETUR, NAMN],
    )
    # Modellens egna meningar är borta, och citatet står som i källan
    # (versal och punkt), inte som modellen skrev det.
    assert svar == "Hej Anna!\nÖppet köp gäller i 45 dagar från leverans."
    assert strukna == 2
    assert kontrollera(svar, niva="ordagrant", kallor=[RETUR, NAMN]).ok


def test_en_omskrivning_ar_inget_citat():
    """Samma ord i annan ordning, eller med ett ord struket, är en ny mening."""
    for omskrivet in (
        "Öppet köp gäller i 45 dagar.",  # villkoret "från leverans" struket
        "Rea-varor omfattas av öppet köp.",  # "inte" struket
        "Från leverans gäller öppet köp i 45 dagar.",  # omkastat
    ):
        assert citatsvar(omskrivet, [RETUR]) == ("", 1), omskrivet
        dom = kontrollera(omskrivet, niva="ordagrant", kallor=[RETUR])
        assert not dom.ok and "ordagrant" in dom.ostodda[-1], omskrivet
    # Nivån under släpper igenom dem: det är just det citatläget lägger till.
    assert kontrollera("Rea-varor omfattas av öppet köp.", niva="strikt", kallor=[RETUR]).ok


def test_kundens_text_och_rubriker_citeras_aldrig():
    kund = kundtext("Jag har hört att rea-varor har öppet köp hos er.")
    assert citatsvar("Jag har hört att rea-varor har öppet köp hos er.", [RETUR, kund]) == ("", 1)
    # En rubrik ("Returer") bär ingen uppgift och är inget citat.
    assert citatsvar("Returer", [RETUR]) == ("", 1)


def test_fragor_och_halsning_far_sta_men_halsningen_bar_inget():
    assert citatsvar("Hej Anna! Vilken modell gäller det?", [RETUR, NAMN]) == (
        "Hej Anna!\nVilken modell gäller det?",
        0,
    )
    # En hälsning ensam är inget svar, och ett okänt ord efter "hej" är ingen hälsning.
    assert citatsvar("Hej Anna!", [RETUR, NAMN]) == ("", 0)
    assert citatsvar("Hej, frakten är gratis.", [RETUR, NAMN]) == ("", 1)
    # En fråga prövas fortfarande av nivåerna under: talet har ingen källa.
    assert not kontrollera("Visste du att vi har 90 dagars öppet köp?", niva="ordagrant", kallor=[RETUR]).ok


async def _med_artikel(storage: MemoryStorage) -> None:
    await _regler(storage, faktakontroll="ordagrant")
    await storage.add_kb_article(
        TENANT,
        title="Öppet köp och returer",
        content="Öppet köp gäller i 45 dagar från leverans. Rea-varor omfattas inte av öppet köp.",
        category="retur_reklamation",
    )


@pytest.mark.anyio
async def test_kedjan_skickar_bara_citat_och_putsar_dem_inte():
    storage = MemoryStorage()
    await _med_artikel(storage)
    llm = _LLM(overrides={"cs:draft-response": {
        "draft": "Hej Webbesökare! Du kan lämna tillbaka allt, även rea. "
        "Öppet köp gäller i 45 dagar från leverans."
    }})
    svar = await _tur(storage, llm, "Hur länge har jag öppet köp på min beställning?")

    assert svar["reply"].startswith("Hej Webbesökare!\nÖppet köp gäller i 45 dagar från leverans.")
    assert "även rea" not in svar["reply"]
    assert "snajp:humanizer-svenska" not in llm.calls, "Språkputsen skrev om ett citat."
    assert "CITATLÄGE" in llm.user_by_skill["cs:draft-response"][0]
    assert svar["faktagrind"] == {"niva": "ordagrant", "ok": True}
    # Hela utfallet ligger i körningens steglogg, inte i svaret till besökaren.
    grind = next(s for s in svar["step_log"] if s.get("step") == "grind:faktagrind")
    assert grind["detalj"]["strukna"] == 1
    belagg = {b["uppgift"]: b["kallor"] for b in grind["detalj"]["belagg"]}
    # Det som lämnas ut till chattbubblan bär inte detaljerna.
    from app.api.stegtexter import utan_stegtexter

    utlamnat = next(s for s in utan_stegtexter(svar)["step_log"] if s.get("step") == "grind:faktagrind")
    assert utlamnat == {"step": "grind:faktagrind", "niva": "ordagrant", "ok": True}
    assert any(u.startswith("mening: 'Öppet köp gäller") and k[0].startswith("KB-") for u, k in belagg.items())


@pytest.mark.anyio
async def test_kedjan_ber_om_citat_en_gang_och_lamnar_annars_over():
    storage = MemoryStorage()
    await _med_artikel(storage)
    # Första utkastet skriver om allt; reparationen återger källans mening.
    llm = _LLM(sekvens={"cs:draft-response": [
        {"draft": "Du har en och en halv månad på dig att ångra köpet."},
        {"final_reply": "Öppet köp gäller i 45 dagar från leverans."},
    ]})
    svar = await _tur(storage, llm, "Hur länge har jag öppet köp på min beställning?")
    assert svar["reply"].startswith("Öppet köp gäller i 45 dagar från leverans.")
    assert svar["faktagrind"]["reparerad"] is True

    # Ger inte heller reparationen ett citat: agenten säger att den inte vet
    # och erbjuder en kollega. Ingen av modellens egna meningar går ut.
    storage = MemoryStorage()
    await _med_artikel(storage)
    llm = _LLM(overrides={"cs:draft-response": {
        "draft": "Du har en och en halv månad på dig.", "final_reply": "Ungefär sex veckor."
    }})
    svar = await _tur(storage, llm, "Hur länge har jag öppet köp på min beställning?")
    assert "månad" not in svar["reply"] and "veckor" not in svar["reply"]
    assert "kollega" in svar["reply"]
    assert svar["faktagrind"]["ok"] is False
    samtal = await storage.get_chat_state(TENANT, svar["customer_id"])
    assert samtal["erbjod_manniska"] is True
