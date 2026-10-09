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
