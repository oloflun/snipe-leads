"""INV-AUTH-002 — en inloggad yta utan session går till inloggningen, aldrig till en felsida.

Kunddemon 2026-11-24: efter utloggning tog bakåtknappen tillbaka till
/admin/arbetsyta, och sidan svarade "Sidan finns inte". Proxyns matcher tog med
/admin, men `protectedRoutePrefixes` i lib/routes.ts gjorde det inte, så proxyn
släppte besökaren vidare till layoutens notFound(). Kommentaren i proxy.ts
påstod samtidigt att proxyn var ett lager för /admin. Den gjorde ingenting där.

Felklassen är att matchern och prefixlistan glider isär, och att en layout
svarar 404 där den borde ha frågat om sessionen först. Båda vaktas statiskt,
eftersom det som blir fel är det som INTE står där.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PROXY = ROOT / "proxy.ts"
ROUTES = ROOT / "lib" / "routes.ts"
ADMIN_LAYOUT = ROOT / "app" / "admin" / "layout.tsx"
AUTH_ACTIONS = ROOT / "lib" / "actions" / "auth.ts"

#: Matcherposter som är publika med flit: inloggningssidan och inbäddningen.
PUBLIKA = {"/login", "/embed"}


def _kod(path: Path) -> str:
    assert path.exists(), f"{path.relative_to(ROOT)} saknas"
    return path.read_text(encoding="utf-8")


def _matcherprefix() -> list[str]:
    kod = _kod(PROXY)
    assert "export const config" in kod, "matchern måste exporteras som `config`, annars läser Next den inte"
    block = kod[kod.index("export const config") :]
    block = block[block.index("matcher") : block.index("]")]
    poster = re.findall(r'"(/[^"]*)"', block)
    assert poster, "hittade inga matcherposter i proxy.ts"
    return [p.split("/:path*")[0] for p in poster]


def _skyddade_prefix() -> list[str]:
    kod = _kod(ROUTES)
    rad = re.search(r"protectedRoutePrefixes\s*=\s*\[([^\]]*)\]", kod)
    assert rad, "protectedRoutePrefixes saknas i lib/routes.ts"
    return re.findall(r'"(/[^"]*)"', rad.group(1))


def test_varje_inloggad_matcherpost_ar_skyddad():
    skyddade = set(_skyddade_prefix())
    saknas = [p for p in _matcherprefix() if p not in PUBLIKA and p not in skyddade]
    assert not saknas, (
        f"proxyn kör på {saknas} men skickar aldrig en besökare utan session till "
        "/login där — lägg prefixet i protectedRoutePrefixes (lib/routes.ts)."
    )


def test_admin_ar_skyddad():
    assert "/admin" in _skyddade_prefix()


def test_proxyn_behaller_sokstrangen_i_next():
    """?vy=korningar ska följa med tillbaka efter inloggningen."""
    kod = _kod(PROXY)
    satt = re.findall(r'searchParams\.set\("next",\s*([^)]*)\)', kod)
    assert len(satt) == 2, f"förväntade två ställen som sätter next, hittade {len(satt)}"
    for uttryck in satt:
        assert "request.nextUrl.search" in uttryck, f"next tappar söksträngen: {uttryck}"


def test_adminlayouten_fragar_om_sessionen_forst():
    """Ingen session → /login. Avgörs med auth(), inte med admin-uppslaget.

    getPlatformAdmin() och getWorkspaceContext() svarar null både för den som
    saknar session och för den som inte är admin; då blandas fallen ihop igen.
    """
    kod = _kod(ADMIN_LAYOUT)
    kropp = kod[kod.index("export default async function AdminLayout") :]
    sessionsfraga = kropp.find("await auth()")
    till_login = kropp.find('redirect("/login')
    behorighet = min(
        i for i in (kropp.find("getPlatformAdmin"), kropp.find("notFound(")) if i != -1
    )
    assert sessionsfraga != -1, "admin-layouten frågar inte auth() om sessionen"
    assert till_login != -1, "admin-layouten skickar aldrig en besökare utan session till /login"
    assert sessionsfraga < till_login < behorighet, (
        "sessionsgrenen måste stå före behörighetsgrenen, annars får en utgången "
        "session layoutens svar för icke-admin."
    )


def test_adminlayouten_svarar_inte_404_for_inloggad_kund():
    """Antons krav 2026-11-24: en felsida får inte dyka upp vid bakåt efter kontobyte."""
    kod = _kod(ADMIN_LAYOUT)
    kropp = kod[kod.index("export default async function AdminLayout") :]
    assert "notFound(" not in kropp
    assert 'redirect("/dashboard")' in kropp


def test_inloggningen_skickar_icke_admin_bort_fran_admin():
    """login?next=/admin/... får aldrig landa en kund på adminytan."""
    kod = _kod(AUTH_ACTIONS)
    kropp = kod[kod.index("async function startsidaFor") :]
    kropp = kropp[: kropp.index("\n}\n")]
    assert re.search(r'\^\\/admin|startsWith\("/admin', kropp), (
        "startsidaFor känner inte igen ett next under /admin — en kund som loggar "
        "in via /login?next=/admin/arbetsyta landar då utanför sin arbetsyta."
    )
    assert '"/dashboard"' in kropp
    assert '"/settings/tvafaktor"' in kropp
