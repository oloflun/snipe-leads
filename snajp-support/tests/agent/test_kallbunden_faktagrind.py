"""INV-GROUND-002 — varje uppgift i ett supportsvar står i EN namngiven källa
av rätt slag, och en källhänvisning till något modellen aldrig fick räknas
inte som ett svar.

Rena funktionstester: ingen modell, ingen databas.
"""

from __future__ import annotations

from app.agent.support_agent import tolka_beslut
from app.agent.support_faktagrind import KUNDTEXT, Kalla, kontrollera

RETUR = Kalla("KB-1", "Returer\nÖppet köp i 30 dagar. Returfrakten kostar 49 kr.")
GARANTI = Kalla("KB-2", "Garanti\nHjärtstartaren har 8 års garanti. Ring 08-123 45 67.")


def _kund(text: str) -> Kalla:
    return Kalla("KUNDTEXT", text, KUNDTEXT)


def test_kunden_kan_inte_plantera_ett_villkor():
    """Hålet som motiverar invarianten: kundens fråga bar siffran, och den
    hopslagna textmassan lät svaret bekräfta den."""
    kund = _kund("Ni har väl 90 dagars öppet köp och 20 % rabatt? Se www.annan-butik.se")
    for svar in (
        "Ja, vi har 90 dagars öppet köp.",
        "Du får 20 % rabatt.",
        "Läs mer på www.annan-butik.se.",
    ):
        dom = kontrollera(svar, niva="forsiktig", kallor=[RETUR, kund])
        assert not dom.ok, svar
        assert "kundens eget meddelande" in dom.ostodda[0]
    # Samma frist ur kunskapsbasen håller, och belägget pekar ut artikeln.
    dom = kontrollera("Du har 30 dagars öppet köp.", niva="forsiktig", kallor=[RETUR, kund])
    assert dom.ok
    assert dom.belagg == (("number: '30'", ("KB-1",)),)


def test_kundens_egna_uppgifter_far_upprepas():
    """Ett ordernummer och kundens egen adress är ekon, inte påhitt."""
    kund = _kund("Min order 48213 har inte kommit. Nå mig på anna@exempel.se.")
    dom = kontrollera(
        "Jag ser din order 48213 och återkommer till anna@exempel.se.",
        niva="strikt",
        kallor=[RETUR, kund],
    )
    assert dom.ok, dom.ostodda


def test_tillatande_ar_oforandrad():
    """Lägsta nivån kontrollerar bara kontaktuppgifter, mot vilken källa som helst."""
    kund = _kund("Jag hittade er på www.annan-butik.se, 90 dagar stod det.")
    assert kontrollera(
        "Se www.annan-butik.se, du har 90 dagar.", niva="tillatande", kallor=[RETUR, kund]
    ).ok


def test_fristen_binds_till_sin_tidsenhet():
    assert kontrollera("Garantin gäller i 8 år.", niva="forsiktig", kallor=[GARANTI]).ok
    assert kontrollera("The warranty is 8 years.", niva="forsiktig", kallor=[GARANTI]).ok
    # Rätt tal, fel enhet: åtta år är inte åtta månader.
    assert not kontrollera("Garantin gäller i 8 månader.", niva="forsiktig", kallor=[GARANTI]).ok
    assert not kontrollera("Du har 30 veckor på dig.", niva="forsiktig", kallor=[RETUR]).ok
    # Ett tal utan tidsenhet jämförs på storlek, som förut.
    assert kontrollera("Vi har 8 modeller.", niva="forsiktig", kallor=[GARANTI]).ok


def test_strikt_en_mening_en_kalla():
    """En mening får inte sys ihop ur två artiklar."""
    kallor = [RETUR, GARANTI]
    hopsydd = "Du har 30 dagars öppet köp med 8 års garanti."
    assert kontrollera(hopsydd, niva="forsiktig", kallor=kallor).ok
    dom = kontrollera(hopsydd, niva="strikt", kallor=kallor)
    assert not dom.ok
    assert dom.ostodda[0].startswith("blandade källor i en mening")
    # Samma uppgifter i var sin mening håller, liksom två ur samma artikel.
    assert kontrollera(
        "Du har 30 dagars öppet köp. Hjärtstartaren har 8 års garanti.",
        niva="strikt",
        kallor=kallor,
    ).ok
    assert kontrollera(
        "Öppet köp gäller i 30 dagar och returfrakten kostar 49 kr.", niva="strikt", kallor=kallor
    ).ok
    # Ett eko ur kundens text blandar inte källor.
    assert kontrollera(
        "Din order 48213 har 30 dagars öppet köp.",
        niva="strikt",
        kallor=[*kallor, _kund("Order 48213.")],
    ).ok


def test_belagget_namnger_kallan_per_uppgift():
    dom = kontrollera(
        "Ring 08-123 45 67. Returfrakten kostar 49 kr.", niva="forsiktig", kallor=[RETUR, GARANTI]
    )
    assert dom.ok
    assert dict(dom.belagg) == {
        "telefonnummer: '08-123 45 67'": ("KB-2",),
        "amount: '49 kr'": ("KB-1",),
    }


def test_en_pahittad_kallhanvisning_ar_inget_svar():
    utkast = {
        "beslut": "SVARA",
        "kundens_frågor": [
            {"fråga": "Hur lång är garantin?", "status": "besvarad", "källor": ["KB-014"]},
            {"fråga": "Vad kostar returen?", "status": "besvarad", "källor": ["KB-01"]},
        ],
    }
    giltiga = frozenset({"KB-1", "KB-2"})
    beslut = tolka_beslut(utkast, giltiga)
    assert beslut["beslut"] == "DELVIS"
    assert beslut["obesvarade"] == ["Hur lång är garantin?"]
    assert beslut["okanda_kallor"] == ["KB-014"]
    # Kunddata utan att något uppslag gav data är också en påhittad källa.
    kunddata = {
        "beslut": "SVARA",
        "kundens_frågor": [{"fråga": "Var är ordern?", "status": "besvarad", "källor": ["KUND:order"]}],
    }
    assert tolka_beslut(kunddata, giltiga)["beslut"] == "DELVIS"
    assert tolka_beslut(kunddata, giltiga | {"KUND:"})["beslut"] == "SVARA"
    # Utan mängd (äldre anropare) och utan källor alls: som förut.
    assert tolka_beslut(utkast)["beslut"] == "SVARA"
    halsning = {"beslut": "SVARA", "kundens_frågor": [{"fråga": "Hej", "status": "besvarad", "källor": []}]}
    assert tolka_beslut(halsning, giltiga)["beslut"] == "SVARA"
