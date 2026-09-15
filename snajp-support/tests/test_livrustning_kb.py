"""Livrustnings kunskapsbas: modulen ska gå att importera, och artikeln om
ångerrätt ska gå att hitta för en kund som skriver "ångra".

En tidigare version av den här rättningen hade riktiga radbrytningar inne i en
strängliteral. Då gick hela app.main inte att importera och 28 testmoduler föll
redan vid collection. Det här testet fångar just den klassen av fel billigt.
"""

from app.tenants import kb_for_tenant, name_for_tenant


def _angerratt():
    artiklar = kb_for_tenant("livrustning")
    traffar = [a for a in artiklar if "ångerrätt" in a["title"].lower()]
    assert len(traffar) == 1, "exakt en ångerrätt-artikel väntas"
    return traffar[0]


def test_modulen_laddas_med_ratt_namn():
    assert name_for_tenant("livrustning") == "Livrustning AB"
    assert len(kb_for_tenant("livrustning")) > 10


def test_angerratt_bar_synonymerna_kunder_skriver():
    text = (_angerratt()["title"] + " " + _angerratt()["content"]).lower()
    for ord_ in ("ångra", "returnera", "skicka tillbaka", "retur"):
        assert ord_ in text, f"saknar {ord_!r}, fulltextsökningen hittar då inte artikeln"


def test_angerratt_sakuppgifterna_ar_oforandrade():
    innehall = _angerratt()["content"]
    for fakta in ("45 dagar", "originalförpackning", "returfrakten", "inom 30 dagar"):
        assert fakta in innehall


def test_kursfragor_lamnas_over_till_manniska():
    innehall = _angerratt()["content"].lower()
    assert "bokad utbildning" in innehall and "människa" in innehall


def test_inga_radbrytningar_i_fel_lage():
    # chr(10) i stället för en escapesekvens: samma klass av fel som testet
    # vaktar mot uppstod när den här filen skrevs via ett skal som åt backslashar.
    radbrytning = chr(10)
    innehall = _angerratt()["content"]
    assert radbrytning * 2 in innehall
    assert not innehall.endswith(radbrytning)
