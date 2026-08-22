"""INV-SEC-011 — vybytet till demokontot kräver plattformsadmin.

Vyväxeln Admin / Demo låter en plattformsadmin rendera hela appen som en
inloggning mot demokontot. Mekanismen är en cookie, och en cookie är något
KLIENTEN skickar — vilket är precis det `requireSnajpTenant` finns för att inte
göra. Tenanten härleds ur sessionen med flit (INV-SEC-002), efter att
catch-all-proxyn en gång föll tillbaka på demonyckeln och varje inloggad kunds
inkorg, kunskapsbas och röstdokument pekade på Nordlys Handel.

Skillnaden mellan den buggen och den här funktionen är EN kontroll:
`getPlatformAdmin()`. Tas den bort blir raden `snajp.vy=demo` i devtools ett
tenant-byte för vem som helst, och ingenting annat i sviten märker det —
demovyn fungerar ju, den fungerar bara för fler än den ska.

Formen är statisk av samma skäl som INV-SEC-010: kontrollen kan inte försvinna
genom att någon skriver ett fel, bara genom att någon tar bort en rad eller
lägger till en ny väg förbi den. Det är den sortens hål ett beteendetest inte
ser, eftersom det som blir fel är vad som INTE står där.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
VY = ROOT / "lib" / "vy.ts"
ACTION = ROOT / "lib" / "actions" / "vy.ts"
TENANT = ROOT / "lib" / "snajp" / "tenant.ts"

#: Namnet på cookien. Står här och inte importeras: testet ska fälla om någon
#: byter namn på båda ställena samtidigt utan att tänka på grinden.
COOKIE = "snajp.vy"


def _kod(path: Path) -> str:
    assert path.exists(), f"{path.relative_to(ROOT)} saknas — vyväxeln är borttagen?"
    return path.read_text(encoding="utf-8")


def test_vy_modulen_ar_server_only():
    """Ett adminvillkor i klientbundeln är inget adminvillkor.

    Samma resonemang som docstringen i lib/auth/admin.ts: det syns i devtools
    och går att sätta till true.
    """
    assert 'import "server-only"' in _kod(VY)


def test_aktiv_vy_slar_upp_plattformsadmin():
    kod = _kod(VY)
    assert "getPlatformAdmin" in kod, (
        "aktivVy() läser cookien utan att fråga vem som skickade den — "
        "det är ett tenant-byte via klienten (INV-SEC-002)."
    )
    # Uppslaget måste stå i samma funktion som cookieläsningen, inte bara
    # någonstans i filen. En import utan anrop är den mest trovärdiga formen
    # av borttagen kontroll.
    kropp = kod[kod.index("export async function aktivVy") :]
    assert "getPlatformAdmin(" in kropp


def test_bytvy_kontrollerar_innan_den_skriver():
    """Skrivvägen har en EGEN kontroll, inte bara läsvägens."""
    kod = _kod(ACTION)
    grind = kod.find("getPlatformAdmin(")
    skrivning = kod.find("cookies()")
    assert grind != -1, "bytVy sätter cookien utan att kontrollera vem som ber om det."
    assert grind < skrivning, "kontrollen står efter skrivningen — den skyddar ingenting."


def test_tenanten_laser_aldrig_cookien_sjalv():
    """requireSnajpTenant frågar aktivVy, och går inte förbi den.

    En andra cookieläsning i tenant.ts vore en andra väg in i demogrenen, och
    den vägen skulle ärva noll av grindarna ovan.
    """
    kod = _kod(TENANT)
    assert "aktivVy(" in kod
    assert COOKIE not in kod, (
        "tenant.ts läser cookien direkt — då finns grinden i vy.ts bara för "
        "den väg som redan var säker."
    )
    assert "cookies(" not in kod


def test_demogrenen_nar_exakt_en_tenant():
    """Det här är inte generell impersonation, och ska inte gå att göra till det."""
    kod = _kod(VY)
    slugar = re.findall(r'DEMO_TENANT_SLUG\s*=\s*"([^"]+)"', kod)
    assert slugar == ["nordlys-handel"], (
        f"förväntade en hårdkodad demo-slug, hittade {slugar}"
    )


@pytest.mark.parametrize("path", [VY, ACTION, TENANT])
def test_filerna_finns_kvar(path: Path):
    """Fälls om någon löser en konflikt genom att ta bort en av filerna."""
    assert path.exists()
