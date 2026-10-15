"""Antons genomgång 2026-10-12 av utkastkedjan (Fiskebäck, Härlanda), i två
omgångar: ingången får inte vara en allmän mening med en etikett på ("som ni
gör", "för företag som ert"), inte "man"/"den som", inte rabbla registerfakta
och inte anta något om mottagaren; erbjudandet överlever omskrivningen; två
mejl i samma körning byggs inte likadant. Referensutkastet passerar."""

from app.agent.leads_research_v2 import _stilfynd, _vald_produkt
from app.leads import stilkontroll as stil

INGANG = (
    "Med både privatpersoner och företag som kunder för er brandtätning och mjukfogning "
    "är nästa företagskund ofta det som får vänta."
)
# "Hej," i stället för "Hej Christian,": texten är i ni-form, och en namngiven
# mottagare får "du" sedan 2026-10-15 (ni_till_person).
REFERENS = (
    "Hej,\n\n"
    f"{INGANG}\n\n"
    "Vår agent Iris hittar kvalificerade kunder åt er. Ni får fem företag i er region som passar er, "
    "med kontaktperson och ett färdigt första mejl till var och en, helt utan kostnad.\n\n"
    "Svara \"ja\" på mejlet så skickar vi de fem inom två arbetsdagar."
)
VILLKOR = (
    "Fem kvalificerade leads i er region, med kontaktperson och ett färdigt första mejl till var och en, "
    "helt utan kostnad. Handling: svara \"ja\" på mejlet, så skickar vi de 5 inom 2 arbetsdagar."
)
PRODUKT = "Iris, leadsagenten"


def _med_ingang(ingang: str) -> str:
    return REFERENS.replace(INGANG, ingang)


def _koder(text: str) -> set[str]:
    return {a.kod for a in stil.kontrollera(text).anmarkningar}


def test_referensutkasten_passerar():
    assert _koder(REFERENS) == set()
    assert stil.erbjudande_fynd(REFERENS, villkor=VILLKOR, produkt=PRODUKT) == []
    # Antons tre goda ingångar ur kön 2026-10-12.
    for ingang in (
        "Att hitta nya företagsuppdrag i Göteborg, parallellt med villor och fastighetsprojekt, är ofta en tidstjuv.",
        "Med Consensos fokus på komplexa program och projekt behöver ni hitta rätt företag att samarbeta med.",
    ):
        assert _koder(_med_ingang(ingang)) == set(), ingang
    # Anton 2026-10-15: "Med er/ert/era …" blev det nya mallordet och fälls nu.
    assert "slentrian_ingang" in _koder(
        _med_ingang("Med er roll inom värmepumpar och fastighetsautomation i Luleå blir servicefrågorna många.")
    )


def test_allman_mening_med_etikett_falls():
    for ingang in (
        "För företag som ert, som säljer till andra företag, är det ofta en utmaning att hitta nya kunder.",
        "När man arbetar med markarbeten och grundläggningar, som ni gör, kommer många förfrågningar.",
        "När ett byggföretag, som ert, hjälper både företag och privatpersoner blir tiden knapp.",
        "Att hitta nya kunder är ofta en utmaning för den som, liksom ni, utför rivning i västra Sverige.",
        "Ni vänder er till privatpersoner, som ni gör, och det tar tid.",
    ):
        assert "mall_ingang" in _koder(_med_ingang(ingang)), ingang


def test_allman_ingang_utan_etikett_falls():
    for ingang in (
        "När man driver ett byggföretag med både privatpersoner och företag som kunder får nästa kund vänta.",
        "Den som utför markarbeten åt både företag och privatpersoner hinner sällan leta nästa kund.",
        "Ett byggföretag som arbetar nära sina beställare har sällan tid över.",
    ):
        assert "generell_ingang" in _koder(_med_ingang(ingang)), ingang


def test_registerfakta_och_antaganden_i_ingangen_falls():
    koder = _koder(_med_ingang("Med 20-25 anställda och fem platschefer vet jag att nästa kund får vänta."))
    assert {"registerfakta_i_ingangen", "antagande_om_dem"} <= koder
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
    annat = _med_ingang("Med både privatpersoner och företag som kunder för er VVS blir nästa kund det som får vänta.")
    assert [a.kod for a in stil.mot_andra(annat, [REFERENS])] == ["samma_konstruktion", "samma_uppmaning"]
    # Ingen gemensam fras om fyra ord heller (samma_fras, 2026-10-15).
    olikt = _med_ingang("Att hinna hitta nästa företagskund vid sidan av era villor kräver tid ni sällan har.").replace(
        "så skickar vi de fem inom två arbetsdagar", "så kommer de fem inom två arbetsdagar"
    )
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
