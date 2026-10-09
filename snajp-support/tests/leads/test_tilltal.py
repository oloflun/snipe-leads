"""Tilltalet i utkasten (Sebbe 2026-10-09: "proffsiga, välformulerade").

Utkast som börjar "Hej," utan namn går till bolaget (Antons regel 14) och
blandade ändå "Skulle du vilja" och "Vi kan visa dig"."""

from app.leads.outreach_playbook import finalize_outreach_body, tilltala_med_ni


def test_hej_utan_namn_ger_ni_genomgaende():
    ut = tilltala_med_ni("Hej,\n\nSkulle du vilja se hur det fungerar? Vi kan visa dig. Hör av dig om din tid räcker.")
    assert "Skulle ni vilja" in ut and "visa er" in ut and "Hör av er" in ut and "er tid" in ut
    assert " du " not in ut and "dig" not in ut


def test_stor_bokstav_behalls():
    assert tilltala_med_ni("Hej,\n\nDu bestämmer.") == "Hej,\n\nNi bestämmer."


def test_namngiven_mottagare_rors_inte():
    text = "Hej Peter,\n\nHör av dig om du vill."
    assert tilltala_med_ni(text) == text


def test_signaturen_efter_halsningen_rors_inte():
    text = "Hej,\n\nHör av dig.\n\nVänliga hälsningar,\nDu-Hansson AB"
    ut = tilltala_med_ni(text)
    assert "Hör av er." in ut and ut.endswith("Du-Hansson AB")


def test_finaliseringen_gor_det_for_varje_utkast():
    assert "Skulle ni" in finalize_outreach_body("Hej,\n\n**Skulle du** vilja?")


def test_avdelning_eller_ort_i_halsningen_blir_hej_och_ni():
    """"Hej Verkstad," och "Hej Luleå," (development 2026-10-09): namnet kom
    från en funktionsadress eller en ortsrad på sajten."""
    assert tilltala_med_ni("Hej Verkstad,\n\nSkulle du vilja?") == "Hej,\n\nSkulle ni vilja?"
    assert tilltala_med_ni("Hej Luleå,\n\nHör av dig.") == "Hej,\n\nHör av er."
    assert tilltala_med_ni("Hej Anna Karin,\n\nDu bestämmer.") == "Hej Anna Karin,\n\nDu bestämmer."


def test_intervall_far_tankstreck_men_telefonnummer_rors_inte():
    ut = finalize_outreach_body("Hej,\n\nEtt samtal på 15-20 minuter. Ring 070-360 05 64.")
    assert "15–20 minuter" in ut and "070-360 05 64" in ut


def test_funktionsadress_med_versalord_blir_ingen_person():
    from app.leads.discovery import person_kontakt_i_text

    sida = "<p>Verkstad Granec</p><p>verkstad@granec.se</p><p>Peter Holm, VD peter.holm@granec.se</p>"
    hit = person_kontakt_i_text(sida, "https://granec.se")
    assert hit and hit["contact_name"] == "Peter Holm"
    assert person_kontakt_i_text("<p>Verkstad Granec</p><p>verkstad@granec.se</p>", "https://granec.se") is None
