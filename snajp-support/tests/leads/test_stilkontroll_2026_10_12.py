"""Antons genomgång 2026-10-12 av två utkastkedjor (Fiskebäck, Härlanda):
ingången får inte vara en mall, inte rabbla registerfakta och inte anta
något om mottagaren; erbjudandet överlever omskrivningen; två mejl i samma
körning byggs inte likadant. Referensutkastet (andra Personalisera) passerar."""

from app.agent.leads_research_v2 import _stilfynd, _vald_produkt
from app.leads import stilkontroll as stil

REFERENS = (
    "Hej Christian,\n\n"
    "När man driver ett företag som ert, med både privatpersoner och företag som kunder, "
    "kan det vara en utmaning att hinna hitta nya affärsmöjligheter.\n\n"
    "Vår agent Iris hittar kvalificerade kunder åt er. Ni får fem företag i er region som passar er, "
    "med kontaktperson och ett färdigt första mejl till var och en, helt utan kostnad.\n\n"
    "Svara \"ja\" på mejlet så skickar vi de fem inom två arbetsdagar."
)
VILLKOR = (
    "Fem kvalificerade leads i er region, med kontaktperson och ett färdigt första mejl till var och en, "
    "helt utan kostnad. Handling: svara \"ja\" på mejlet, så skickar vi de 5 inom 2 arbetsdagar."
)
PRODUKT = "Iris, leadsagenten"


def _koder(text: str) -> set[str]:
    return {a.kod for a in stil.kontrollera(text).anmarkningar}


def test_referensutkastet_passerar():
    assert _koder(REFERENS) == set()
    assert stil.erbjudande_fynd(REFERENS, villkor=VILLKOR, produkt=PRODUKT) == []


def test_mallingangen_falls():
    text = REFERENS.replace(
        "När man driver ett företag som ert, med både privatpersoner och företag som kunder, kan det vara",
        "För företag som ert, som säljer till andra företag, är det ofta",
    )
    assert "mall_ingang" in _koder(text)


def test_registerfakta_och_antaganden_i_ingangen_falls():
    text = REFERENS.replace(
        "När man driver ett företag som ert, med både privatpersoner och företag som kunder, kan det vara en utmaning",
        "Med 20-25 anställda och fem platschefer vet jag att det är en utmaning",
    )
    assert {"registerfakta_i_ingangen", "antagande_om_dem"} <= _koder(text)
    # En tid eller ett telefonnummer i ingången är inga registerfakta.
    assert "registerfakta_i_ingangen" not in _koder("Boka 15–20 minuter nästa vecka, ring 070-123 45 67.")


def test_tappat_erbjudande_falls():
    utan = REFERENS.replace(
        "Vår agent Iris hittar kvalificerade kunder åt er. Ni får fem företag i er region som passar er, "
        "med kontaktperson och ett färdigt första mejl till var och en, helt utan kostnad.",
        "Vi hjälper byggföretag att hitta nya affärsmöjligheter.",
    ).replace("så skickar vi de fem inom två arbetsdagar", "så visar vi ett par exempel")
    koder = {a.kod for a in stil.erbjudande_fynd(utan, villkor=VILLKOR, produkt=PRODUKT)}
    assert koder == {"erbjudande_siffror", "erbjudande_produkt"}


def test_samma_konstruktion_i_korningen_falls():
    annat = REFERENS.replace("både privatpersoner och företag som kunder", "nära relationer till beställare")
    assert [a.kod for a in stil.mot_andra(annat, [REFERENS])] == ["samma_konstruktion", "samma_uppmaning"]
    olikt = REFERENS.replace(
        "När man driver ett företag som ert, med både privatpersoner och företag som kunder, kan det vara",
        "Att hinna hitta nästa företagskund vid sidan av villorna är ofta",
    ).replace("så skickar vi de fem inom två arbetsdagar", "så kommer de fem inom två arbetsdagar")
    assert stil.mot_andra(olikt, [REFERENS]) == []


def test_stilfynden_till_omskrivningen():
    draft = {
        "subject": "x",
        "body": REFERENS.replace("Ni får fem företag", "Ni får företag").replace("skickar vi de fem", "skickar vi dem"),
    }
    fynd = _stilfynd(draft, villkor=VILLKOR, produkt=PRODUKT, andra=[])
    assert fynd and fynd[0].startswith("Stil: villkorens siffror saknas")
    assert _stilfynd({"body": ""}, villkor=VILLKOR, produkt=PRODUKT, andra=[]) == []


def test_produktens_kortform_raknas():
    produkter = [{"namn": "Iris, leadsagenten", "nytta": "x"}, {"namn": "Supportagenten", "nytta": "y"}]
    assert _vald_produkt({"produkt": "Iris"}, produkter)["namn"] == "Iris, leadsagenten"
    assert _vald_produkt({"produkt": "Iris leadsagent"}, produkter) is None


def test_ingangsformen_roterar_per_prospekt():
    from app.agent.leads_research_v2 import _INGANGSFORMER, _ingangsform

    former = {_ingangsform(f"prospekt-{i}") for i in range(40)}
    assert former == set(_INGANGSFORMER), "fem former ska alla förekomma över en körning"
    assert _ingangsform("samma") == _ingangsform("samma")
