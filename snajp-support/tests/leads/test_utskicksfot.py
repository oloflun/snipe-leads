"""Sidfoten som koden bygger måste passera de spärrar koden själv dömer med.

Testets hela poäng är kopplingen: `utskicksfot.bygg_fot` SKRIVER texten,
`send_guard` DÖMER den, och de två filerna delar inte en rad kod. Går
formuleringarna isär — någon "förbättrar" en mening, eller lägger till ett
krav i `_ART14_KRAV` — blockeras varje utskick i produktion utan att något
annat test märker det. Här märks det.
"""

from datetime import datetime, timezone

import pytest

from app.leads.send_guard import (
    SKICKA,
    Avsandare,
    TenantHistorik,
    Utskick,
    check_send_guard,
)
from app.leads.utskicksfot import avregistreringslank, bygg_fot, har_fot, med_fot, ny_token

AVSANDARE = Avsandare(
    foretagsnamn="Livrustning Sverige AB",
    orgnr="556824-9022",
    postadress="Storgatan 1, 411 38 Göteborg",
)

FOT = bygg_fot(
    foretagsnamn=AVSANDARE.foretagsnamn,
    orgnr=AVSANDARE.orgnr,
    postadress=AVSANDARE.postadress,
    lank=avregistreringslank("https://snajp.se", "a" * 32),
    kontakt_epost="dataskydd@livrustning.se",
)


def _historik(**overrides) -> TenantHistorik:
    bas = dict(
        skickade_totalt=50,
        skickade_idag=0,
        tenant_alder_dagar=400,
        senaste_kontakt_med_foretaget=None,
        suppressions=frozenset(),
        tidigare_kontaktade=frozenset(),
        egna_kunder=frozenset(),
    )
    bas.update(overrides)
    return TenantHistorik(**bas)


def _dom(brodtext: str, *, personlig: bool):
    # Tisdag 10:00 svensk tid — inom regel 5:s fönster, så domen handlar om
    # innehållet och inte om klockan.
    nu = datetime(2026, 8, 25, 8, 0, tzinfo=timezone.utc)
    return check_send_guard(
        avsandare=AVSANDARE,
        utskick=Utskick(
            mottagare="anna.svensson@exempel.se" if personlig else "info@exempel.se",
            amne="En fråga",
            brodtext=brodtext,
            foretagsnyckel="exempel.se",
            personlig_adress=personlig,
        ),
        historik=_historik(),
        nu=nu,
    )


@pytest.mark.parametrize("personlig", [True, False])
def test_mejl_med_foten_slapps_igenom(personlig):
    beslut = _dom("Hej,\n\nEtt kort och relevant erbjudande.\n\n" + FOT, personlig=personlig)
    assert beslut.atgard == SKICKA, beslut.skal


def test_mejl_utan_foten_blockeras():
    beslut = _dom("Hej,\n\nEtt kort och relevant erbjudande.", personlig=False)
    assert beslut.atgard != SKICKA
    assert beslut.regel in ("1_avsandaridentifikation", "2_avregistrering")


def test_foten_ar_idempotent():
    en_gang = med_fot("Hej.", fot=FOT)
    assert med_fot(en_gang, fot=FOT) == en_gang
    assert har_fot(en_gang)
    assert not har_fot("Hej.")


def test_token_ar_ogenomskinlig_och_unik():
    assert ny_token() != ny_token()
    assert len(ny_token()) == 32


def test_lanken_bar_ordet_guarden_letar_efter():
    """Regel 2 letar efter avregistrera/unsubscribe/optout i en http-länk. En
    kortare sökväg (/u/<token>) hade blockerat varje utskick."""
    assert "avregistrera" in avregistreringslank("https://snajp.se", "x" * 32)
