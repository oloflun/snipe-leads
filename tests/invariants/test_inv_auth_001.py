"""INV-AUTH-001 — sessionsanspråk som styr routing måste utfärdas om när de
ändras.

Bakgrunden är mätt i drift, inte befarad. Onboardingen skrev `business_contexts`
korrekt, omdirigerade till /dashboard, och proxyn skickade tillbaka till
/onboarding — i oändlighet. Raden fanns i databasen hela tiden.

Orsaken är formen, inte en glömd rad: proxyn läser den RÅA sessions-token:en
med `getToken()` och kör aldrig `jwt`-callbacken. Ett anspråk som uppdateras i
minnet syns därför aldrig där. Cookien måste skrivas om, och det gör bara
`unstable_update`.

Det här är exakt den sortens fel som ingen typkontroll och inget enhetstest
hittar: båda halvorna är korrekt kod, felet sitter i att de inte talar med
varandra. Därför en statisk invariant över anropsstället.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
AUTH = ROOT / "lib" / "auth.ts"
ONBOARDING = ROOT / "lib" / "actions" / "onboarding.ts"
PROXY = ROOT / "proxy.ts"

#: Anspråk i token som proxyn fattar routingbeslut på. Läggs ett till här utan
#: att det utfärdas om vid ändring uppstår samma loop igen.
ROUTING_CLAIMS = ("onboarded",)


@pytest.fixture(scope="module")
def sources() -> dict[str, str]:
    for path in (AUTH, ONBOARDING, PROXY):
        assert path.exists(), f"{path} saknas — invarianten mäter ingenting."
    return {p.name: p.read_text(encoding="utf-8") for p in (AUTH, ONBOARDING, PROXY)}


def test_proxyn_laser_ratt_anspraak(sources: dict[str, str]):
    """Om proxyn slutar läsa anspråket mäter resten av filen fel sak."""
    proxy = sources["proxy.ts"]
    assert "getToken" in proxy, "proxy.ts läser inte längre token — se över hela invarianten."
    for claim in ROUTING_CLAIMS:
        assert claim in proxy, f"proxy.ts läser inte anspråket {claim!r} längre."


def test_auth_exporterar_en_vag_att_utfarda_om(sources: dict[str, str]):
    auth = sources["auth.ts"]
    assert "unstable_update" in auth, (
        "lib/auth.ts exporterar ingen väg att utfärda sessionen på nytt. Utan "
        "den kan ett routinganspråk aldrig bli färskt i proxyn."
    )
    assert re.search(r"unstable_update\s*:\s*(\w+)", auth), (
        "unstable_update måste exporteras under ett namn som går att anropa."
    )


def test_onboardingen_utfardar_sessionen_pa_nytt(sources: dict[str, str]):
    """Den enda platsen som ändrar `onboarded` från false till true."""
    auth = sources["auth.ts"]
    alias = re.search(r"unstable_update\s*:\s*(\w+)", auth).group(1)

    onboarding = sources["onboarding.ts"]
    assert alias in onboarding, (
        f"lib/actions/onboarding.ts anropar aldrig {alias}(). Då står "
        f"`onboarded: false` kvar i cookien och /dashboard studsar tillbaka "
        f"till /onboarding trots att raden skrevs."
    )

    # Ordningen spelar roll: en omutfärdning EFTER redirect() körs aldrig,
    # eftersom redirect kastar.
    assert onboarding.index(f"{alias}(") < onboarding.index('redirect("/dashboard")'), (
        f"{alias}() måste anropas FÖRE redirect(). redirect() kastar, så allt "
        f"efter den är död kod som ser levande ut."
    )
