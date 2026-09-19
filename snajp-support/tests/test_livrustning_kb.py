"""Livrustnings kunskapsbas: modulen ska gå att importera, och innehållet ska
följa den nya sajten (2026-09-19) — inte den gamla Wix-sajten.

En tidigare version av basen hade riktiga radbrytningar inne i en
strängliteral. Då gick hela app.main inte att importera och 28 testmoduler föll
redan vid collection. Det här testet fångar just den klassen av fel billigt.
"""

from app.tenants import kb_for_tenant, name_for_tenant


def _artiklar():
    return kb_for_tenant("livrustning")


def _artikel(titel_del: str) -> dict:
    traffar = [a for a in _artiklar() if titel_del.lower() in a["title"].lower()]
    assert len(traffar) == 1, f"exakt en artikel om {titel_del!r} väntas"
    return traffar[0]


def test_modulen_laddas_med_ratt_namn():
    assert name_for_tenant("livrustning") == "Livrustning AB"
    assert len(_artiklar()) > 10


def test_rubrikerna_ar_unika():
    titlar = [a["title"].casefold() for a in _artiklar()]
    assert len(titlar) == len(set(titlar))


def test_gamla_sajtens_felaktiga_uppgifter_ar_borta():
    """Webbutiken, det gamla telefonnumret och Nacka-adressen kom från Wix-sajten.
    Agenten svarar ur basen — står de kvar upprepar den dem för kundens räkning."""
    allt = " ".join(f"{a['title']} {a['content']}" for a in _artiklar()).lower()
    for fel in ("hjartstartarbutiken", "08-972247", "rudsjövägen", "nacka", "ångerrätt", "frakt"):
        assert fel not in allt, f"{fel!r} står kvar"


def test_hjartstartare_saljs_inte():
    innehall = _artikel("säljer ni hjärtstartare")["content"]
    assert innehall.startswith("Nej")


def test_avbokning_lamnas_till_manniska():
    innehall = _artikel("avboka")["content"].lower()
    assert "kontakt@livrustning.se" in innehall and "personligen" in innehall


def test_kontaktuppgifterna_foljer_nya_sajten():
    innehall = _artikel("kontaktuppgifter")["content"]
    for fakta in ("kontakt@livrustning.se", "070-733 32 54", "Hökaren 49, 907 88 Täfteå", "556824-9022"):
        assert fakta in innehall


def test_inga_radbrytningar_i_innehallet():
    # chr(10) i stället för en escapesekvens: samma klass av fel som testet
    # vaktar mot uppstod när en fil skrevs via ett skal som åt backslashar.
    for artikel in _artiklar():
        assert chr(10) not in artikel["content"], artikel["title"]
