"""INV-AUTH-001 — sessions-token bär BARA identitet. Föränderligt tillstånd
läses färskt.

Bakgrunden är mätt i drift, inte befarad. Onboardingstatusen låg som ett
anspråk i sessions-JWT:n och proxyn dirigerade på den. Följden var en loop:
onboardingen skrev `business_contexts` korrekt, skickade till /dashboard, och
proxyn skickade tillbaka till /onboarding. Raden fanns i databasen hela tiden.

Första försöket till fix var att utfärda cookien på nytt med
`unstable_update`. Det höll inte — och det är den viktigare lärdomen, för
felet var inte ett glömt anrop utan formen: en token är en ÖGONBLICKSBILD,
signerad och cachad hos klienten. Identitet hör hemma där för att den inte
ändras under sessionen. Föränderligt tillstånd gör det inte — det blir
inaktuellt utan att något felar, och felet visar sig som en dirigering ingen
kan förklara från koden hen läser.

Den här invarianten spärrar därför inte "kom ihåg att uppdatera", utan
"lägg inte dit det". Ett test som kräver ett uppdateringsanrop hade
cementerat den lösning som bevisligen inte fungerade.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
AUTH = ROOT / "lib" / "auth.ts"
PROXY = ROOT / "proxy.ts"
GATE = ROOT / "lib" / "auth" / "onboarding-gate.ts"

#: Tillstånd som ändras UNDER en session och därför aldrig får bo i token.
#: Lägg till här när ett nytt sådant fält dyker upp — listan är billigare att
#: underhålla än loopen den förhindrar.
MUTABLE_STATE = ("onboarded", "workspaceId", "role", "addons", "products", "entitlement")


@pytest.fixture(scope="module")
def auth_source() -> str:
    assert AUTH.exists(), f"{AUTH} saknas — invarianten mäter ingenting."
    return AUTH.read_text(encoding="utf-8")


def _callback_body(source: str, name: str) -> str:
    """Kroppen av en namngiven Auth.js-callback, grovt men tillräckligt."""
    match = re.search(rf"async {name}\(.*?\n(.*?)\n    }},?\n", source, re.DOTALL)
    assert match, f"Hittade ingen {name}-callback i lib/auth.ts — se över invarianten."
    return match.group(1)


@pytest.mark.parametrize("field", MUTABLE_STATE)
def test_token_bar_inte_forandeligt_tillstand(auth_source: str, field: str):
    body = _callback_body(auth_source, "jwt")
    assert f"token.{field}" not in body, (
        f"jwt-callbacken skriver token.{field}. Det är föränderligt tillstånd i "
        f"en ögonblicksbild: det blir inaktuellt utan att något felar. Läs det "
        f"färskt där det används i stället (lib/auth/onboarding-gate.ts är "
        f"mönstret)."
    )


def test_proxyn_avgor_bara_om_sessionen_finns():
    """Proxyn läser den RÅA token:en och kör aldrig jwt-callbacken. Varje
    routingbeslut den fattar på något annat än 'finns en session' vilar
    därför på ett värde som kan vara godtyckligt gammalt."""
    proxy = PROXY.read_text(encoding="utf-8")
    for field in MUTABLE_STATE:
        assert f"token?.{field}" not in proxy and f"token.{field}" not in proxy, (
            f"proxy.ts dirigerar på token.{field}. Det värdet uppdateras inte av "
            f"getToken(), så beslutet fattas på en gammal cookie."
        )


def test_onboardinggrinden_finns_och_laser_databasen():
    """Kontrollen får inte bara försvinna ur proxyn — den måste finnas kvar
    någonstans, annars når en icke-onboardad användare dashboarden."""
    assert GATE.exists(), (
        "lib/auth/onboarding-gate.ts saknas. Kontrollen togs bort ur proxyn; "
        "utan en ersättare är /dashboard öppen för en halvfärdig arbetsyta."
    )
    gate = GATE.read_text(encoding="utf-8")
    assert "hasCompletedOnboarding" in gate, (
        "Grinden läser inte databasen — då är den tillbaka på ett cachat värde."
    )
    assert 'redirect("/onboarding")' in gate


@pytest.mark.parametrize(
    "layout",
    ["app/dashboard/layout.tsx", "app/settings/layout.tsx"],
)
def test_grinden_ar_anropad_fran_varje_skyddad_yta(layout: str):
    path = ROOT / layout
    assert path.exists(), f"{layout} saknas — se över invarianten."
    assert "requireOnboarded" in path.read_text(encoding="utf-8"), (
        f"{layout} anropar inte requireOnboarded(). En grind som finns men inte "
        f"anropas är samma sak som ingen grind — precis som signOut(), som fanns "
        f"med noll konsumenter tills någon letade."
    )
