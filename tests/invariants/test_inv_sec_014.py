"""INV-SEC-014 — klienten märker när identiteten bytts och laddar om.

Kunddemon 2026-11-24: två flikar i samma webbläsare. Den ena hade renderat
/dashboard som kundkontot, med kundens namn och demobanner i skalet. Sedan blev
plattformsadminens session den aktiva i webbläsaren. Varje mjuk navigering i
den gamla fliken hämtade paneldata med adminens cookie, medan skalet stod kvar
på kunden, tills en hård omladdning. Servern svarade rätt för den session som
var aktiv. Felet var att klienten aldrig märkte att identiteten bytts.

Skyddet har fyra delar, och vakten är statisk av samma skäl som INV-SEC-011:
det som blir fel är det som inte står där.

1. Varje svar från proxyAsTenant bär X-Snajp-Identitet, även felsvaren.
2. Layoutens DashboardState bär samma värde, räknat av EN funktion
   (lib/snajp/tenant.ts:snajpIdentitet), så att proxyn och layouten aldrig räknar
   olika.
3. DashboardProvider jämför vid varje navigering, vid fokus och när fliken blir
   synlig, och lyssnar på BroadcastChannel("snajp-identitet").
4. Inloggning, utloggning och vybyte gör ingen redirect() på servern. De
   returnerar en adress som klienten öppnar med window.location.replace, efter
   att ha sagt till de andra flikarna.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
TENANT = ROOT / "lib" / "snajp" / "tenant.ts"
PROXY_AUTH = ROOT / "app" / "api" / "snajp-support" / "_auth.ts"
PROXY_LIB = ROOT / "app" / "api" / "snajp-support" / "_lib.ts"
IDENTITET_ROUTE = ROOT / "app" / "api" / "snajp-support" / "identitet" / "route.ts"
DASHBOARD = ROOT / "lib" / "data" / "dashboard.ts"
PROVIDER = ROOT / "components" / "dashboard" / "DashboardContext.tsx"
AUTH_ACTIONS = ROOT / "lib" / "actions" / "auth.ts"
VY_ACTION = ROOT / "lib" / "actions" / "vy.ts"

HUVUD = "X-Snajp-Identitet"
KANAL = "snajp-identitet"


def _kod(path: Path) -> str:
    assert path.exists(), f"{path.relative_to(ROOT)} saknas"
    return path.read_text(encoding="utf-8")


def _funktion(kod: str, signatur: str) -> str:
    """Kroppen från signaturen till funktionens avslutande toppnivåklammer."""
    start = kod.index(signatur)
    slut = kod.find("\n}\n", start)
    return kod[start : slut if slut != -1 else len(kod)]


def test_en_enda_identitetsfunktion():
    kod = _kod(TENANT)
    assert "export async function snajpIdentitet" in kod
    kropp = _funktion(kod, "export async function snajpIdentitet")
    # Användare, vy och tenantens slug — alla tre ska ingå.
    for del_ in ("user.id", "lage.vy", "slug"):
        assert del_ in kropp, f"identiteten saknar {del_}"
    # Opak: ett hashvärde, aldrig användar-id:t i klartext i ett svarshuvud.
    assert "createHash" in kropp


def test_proxyn_satter_huvudet_pa_varje_svar():
    kod = _kod(PROXY_AUTH)
    kropp = _funktion(kod, "export async function proxyAsTenant")
    assert HUVUD in kod
    assert "snajpIdentitet" in kropp
    # Exakt ett return i den exporterade funktionen, och det kommer efter att
    # huvudet satts: då kan ingen gren (läsrollens 403, tenantfelet, backendens
    # svar) gå förbi det.
    assert kropp.count("return ") == 1, "proxyAsTenant har fler än en utgång — huvudet kan missas"
    assert kropp.index(".headers.set(") < kropp.index("return ")


def test_identitetsrouten_finns_och_cachas_inte():
    kod = _kod(IDENTITET_ROUTE)
    assert "requireSnajpTenant" in kod
    assert "snajpIdentitet" in kod
    # Samma konstant som proxyn, så att namnet inte kan glida isär.
    assert "IDENTITET_HUVUD" in kod and 'from "../_auth"' in kod
    assert "no-store" in kod


def test_proxyns_svar_cachas_inte_och_varierar_pa_cookie():
    kod = _kod(PROXY_LIB)
    assert re.search(r'"Cache-Control",\s*"private, no-store"', kod)
    assert re.search(r'"Vary",\s*"Cookie"', kod)


def test_layoutens_state_bar_identiteten():
    kod = _kod(DASHBOARD)
    assert "identitet" in kod
    assert "snajpIdentitet(" in kod


def test_providern_jamfor_och_lyssnar():
    kod = _kod(PROVIDER)
    assert "/api/snajp-support/identitet" in kod
    assert HUVUD in kod
    assert "window.location.reload()" in kod
    assert f'"{KANAL}"' in kod and "BroadcastChannel" in kod
    for handelse in ('"focus"', '"visibilitychange"'):
        assert handelse in kod, f"providern kontrollerar inte vid {handelse}"
    assert "usePathname" in kod and "useSearchParams" in kod
    # Skydd mot omladdningsloop.
    assert "sessionStorage" in kod


@pytest.mark.parametrize(
    ("fil", "signatur"),
    [
        (AUTH_ACTIONS, "export async function signInWithPassword"),
        (AUTH_ACTIONS, "export async function signOut"),
        (VY_ACTION, "export async function bytVy"),
    ],
)
def test_identitetsbyten_gor_ingen_serverredirect(fil: Path, signatur: str):
    kropp = _funktion(_kod(fil), signatur)
    assert "redirect(" not in kropp, (
        f"{signatur.split()[-1]} gör redirect() — en mjuk navigering som behåller "
        "flikens state och routercache efter identitetsbytet."
    )
    assert "redirectTo" not in kropp
    assert "url" in kropp


def test_vycookien_rensas_vid_in_och_utloggning():
    kod = _kod(AUTH_ACTIONS)
    for signatur in ("export async function signInWithPassword", "export async function signOut"):
        kropp = _funktion(kod, signatur)
        assert "VY_COOKIE" in kropp, f"{signatur.split()[-1]} lämnar snajp.vy kvar till nästa konto"


@pytest.mark.parametrize(
    "fil",
    [
        "components/auth/LoginForm.tsx",
        "components/auth/SignOutButton.tsx",
        "components/admin/AdminShell.tsx",
        "components/VyVaxel.tsx",
        "components/admin/BytKund.tsx",
        "components/admin/OppnaArbetsyta.tsx",
        "components/ImpersonationBanner.tsx",
    ],
)
def test_anroparna_oppnar_adressen_hart(fil: str):
    """Ingen anropare använder längre en server action direkt som formulärets action."""
    kod = _kod(ROOT / fil)
    assert "action={bytVy}" not in kod
    assert "action={signOut}" not in kod
    assert "void signOut()" not in kod
    assert re.search(r"oppnaEfterIdentitetsbyte|bytVyOchOppna|loggaUtOchOppna", kod), (
        f"{fil} öppnar inte adressen efter identitetsbytet"
    )
