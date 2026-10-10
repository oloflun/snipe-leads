"""Skicka nu ur kön (Anton 2026-10-10): går direkt även utanför sändfönstret,
men bara kontorstiden släpps."""

from datetime import datetime, timezone

from app.leads import send_guard as sg

LORDAG_23 = datetime(2026, 10, 10, 21, 0, tzinfo=timezone.utc)


def _utskick(direkt: bool) -> sg.Utskick:
    return sg.Utskick(mottagare="info@exempel.se", amne="Hej", brodtext="Text", foretagsnyckel="exempel.se",
                      personlig_adress=False, direkt=direkt)


def test_regel_5a_slapps_bara_for_skicka_nu():
    historik = sg.TenantHistorik(skickade_totalt=10, skickade_idag=0, tenant_alder_dagar=60,
                                 senaste_kontakt_med_foretaget=None, suppressions=frozenset(),
                                 tidigare_kontaktade=frozenset(), egna_kunder=frozenset())
    vanlig = sg._regel_5_volymtak(avsandare=None, utskick=_utskick(False), historik=historik, nu=LORDAG_23)
    assert vanlig is not None and vanlig.atgard == sg.KOLA_OM
    assert sg._regel_5_volymtak(avsandare=None, utskick=_utskick(True), historik=historik, nu=LORDAG_23) is None
