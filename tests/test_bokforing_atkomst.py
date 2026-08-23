"""Bokföringen är admin-endast, och det ska gälla på BÅDA ställena.

Att dölja en menypost är en artighet. Grinden är serverbeslutet — och de två
måste hänga ihop, annars uppstår exakt den motsägelse som gjorde
preview-routerna onåbara: två filer som var för sig ser rätt ut och tillsammans
säger emot varandra.

Tre ytor kontrolleras här:

  1. `lib/routes.ts` — routen är märkt `adminOnly`, och filtret är fail-closed
     (default `false`, så en anropare som glömmer flaggan visar FÄRRE poster).
  2. `components/AppShell.tsx` — båda anropen skickar faktiskt in admin-status.
  3. `WorkspaceSection` och proxyn — serverns 404 för den som inte är admin.

Testet läser filerna som text. Det räcker för frågan som ställs och kan köras i
samma svit som resten — se test_preview_routernas_natbarhet.py.
"""

from __future__ import annotations

import re
from pathlib import Path

ROT = Path(__file__).resolve().parents[1]
ROUTES = (ROT / "lib" / "routes.ts").read_text(encoding="utf-8")
APPSHELL = (ROT / "components" / "AppShell.tsx").read_text(encoding="utf-8")
SECTION = (ROT / "components" / "dashboard" / "WorkspaceSection.tsx").read_text(encoding="utf-8")
_PROXY_FIL = ROT / "app" / "api" / "snajp-support" / "bookkeeping" / "[...path]" / "route.ts"

_BLOCK_COMMENT = re.compile(r"/\*.*?\*/", re.DOTALL)
_LINE_COMMENT = re.compile(r"//[^\n]*")


def _utan_kommentarer(kalla: str) -> str:
    """Kommentarerna bort före sökningen.

    Inte en detalj: den FÖRSTA versionen av det här testet fällde på sin egen
    förklaring. Proxyns docstring nämner `request.text()` för att beskriva vad
    catch-allen gör FEL, och testet läste det som att proxyn gjorde det.
    Samma fälla som INV-SEC-010 dokumenterar — testet anklagade filen för det
    den varnar för.
    """

    def _behall_nyrader(match: re.Match[str]) -> str:
        return "\n" * match.group(0).count("\n")

    return _LINE_COMMENT.sub("", _BLOCK_COMMENT.sub(_behall_nyrader, kalla))


PROXY = _utan_kommentarer(_PROXY_FIL.read_text(encoding="utf-8"))


# -- 1. Routen och filtret -------------------------------------------------


def test_routen_ar_markt_admin_only():
    rad = next((r for r in ROUTES.splitlines() if "/dashboard/bokforing" in r), None)
    assert rad is not None, "Bokföringsrouten saknas i appRoutes."
    assert "adminOnly: true" in rad, f"Routen är inte admin-märkt: {rad.strip()}"


def test_filtret_ar_fail_closed():
    """`isAdmin = false` som default.

    Motsatt default hade gjort varje ny anropsplats till en potentiell läcka:
    den som glömmer flaggan hade visat MER, inte mindre. Samma val som
    entitlements gör sedan Fas 3 (se lib/data/dashboard.ts).
    """
    assert re.search(r"isAdmin\s*=\s*false", ROUTES), (
        "routesForProducts måste defaulta isAdmin till false. Utan det visar "
        "en anropare som glömmer flaggan bokföringsfliken för alla."
    )


def test_filtret_faktiskt_grindar_pa_flaggan():
    assert re.search(r"!route\.adminOnly\s*\|\|\s*isAdmin", ROUTES), (
        "adminOnly-flaggan läses inte i routesForProducts — då är den dekoration."
    )


# -- 2. Skalet skickar in admin-status ------------------------------------


def test_varje_anropsplats_i_repot_skickar_admin():
    """VARJE `routesForProducts`-anrop, inte ett känt antal i en känd fil.

    Den första versionen av det här testet letade i AppShell och hävdade att
    anropen var exakt två. Det fanns tre. Den tredje låg i
    `components/admin/AdminShell.tsx`, som bygger ADMINYTANS flikrad — och
    eftersom filtret är fail-closed försvann bokföringsfliken där.

    Följden var att fliken inte fanns någonstans för den enda publik den är
    byggd för: en plattformsadmin som öppnar /dashboard skickas till /admin
    (app/dashboard/layout.tsx), och /admin är precis den yta AppShell inte
    ritar (den kortsluter på pathname). Sidan gick att nå på /admin/bokforing
    men ingenting länkade dit.

    Testet räknar därför inte anrop längre — det letar upp dem och kräver att
    var och en tar ställning. En ny anropsplats fälls automatiskt.
    """
    anropsplatser: list[tuple[str, str]] = []
    for fil in sorted((ROT / "components").rglob("*.tsx")) + sorted((ROT / "app").rglob("*.tsx")):
        kalla = _utan_kommentarer(fil.read_text(encoding="utf-8"))
        for block in re.findall(r"routesForProducts\((.*?)\)", kalla, re.DOTALL):
            anropsplatser.append((str(fil.relative_to(ROT)), block))

    assert anropsplatser, "Hittade inga anrop — testet mäter ingenting."

    utan_admin = [
        (fil, block.strip()) for fil, block in anropsplatser if "isAdmin" not in block
    ]
    assert not utan_admin, (
        "Dessa anrop tar inte ställning till adminOnly-routerna. Filtret är "
        "fail-closed, så de FÖRSVINNER tyst i just den menyn:\n"
        + "\n".join(f"  {fil}: routesForProducts({block})" for fil, block in utan_admin)
    )


# -- 3. Grinden på servern ------------------------------------------------


def test_workspacesection_grindar_bokforing_pa_plattformsadmin():
    block = SECTION.split('section === "bokforing"')
    assert len(block) == 2, "WorkspaceSection har ingen bokforing-gren."
    gren = block[1].split("const product")[0]
    assert "isPlatformAdmin" in gren, "Bokföringsgrenen kontrollerar inte plattformsadmin."
    assert "notFound()" in gren, "Bokföringsgrenen svarar inte 404 för den som inte är admin."


def test_bokforing_gar_inte_via_entitlement_kartan():
    """`sectionProduct` kräver en ProductKey, och bokföringen har ingen.

    Står den ändå där betyder det att någon gett den en ProductKey utan att
    röra kartorna i lib/routes.ts — se AppRoute.adminOnly för vad som då också
    måste ändras.
    """
    karta = SECTION.split("const sectionProduct")[1].split("}")[0]
    assert "bokforing" not in karta, (
        "bokforing står i sectionProduct. Den grindas på admin, inte på "
        "entitlement — se AppRoute.adminOnly i lib/routes.ts."
    )


def test_proxyn_grindar_fore_tenant_uppslaget():
    """Adminkontrollen FÖRST.

    En tenant-uppslagning före grinden lämnar en mätbar tidsskillnad som
    avslöjar om kontot finns, och den gör dessutom ett databasanrop åt någon
    som inte får vara där.
    """
    assert "getPlatformAdmin" in PROXY, "Proxyn kontrollerar inte plattformsadmin."
    assert PROXY.index("getPlatformAdmin(") < PROXY.index("requireSnajpTenant("), (
        "requireSnajpTenant körs före adminkontrollen i proxyn."
    )


def test_proxyn_svarar_404_och_inte_403():
    """403 bekräftar att ytan finns. Samma val som app/admin/layout.tsx."""
    gren = PROXY.split("if (!admin)")[1].split("return")[1].split(";")[0]
    assert "404" in gren, f"Proxyn svarar inte 404 för icke-admin: {gren.strip()}"
    assert "403" not in gren


def test_proxyn_ar_binarsaker():
    """Kvittot in är multipart, SIE-filen ut är CP437.

    Går någondera genom en text-rundtur blir den obrukbar: kvittot oläsbart,
    SIE-filen avvisad av kundens bokföringsprogram. Catch-allen gör exakt det,
    vilket är hela skälet till att den här routen finns.
    """
    assert "arrayBuffer()" in PROXY, "Proxyn strömmar inte kroppen som bytes."
    assert "request.text()" not in PROXY, "Proxyn läser kroppen som text."
    assert 'svar.headers.get("content-type")' in PROXY, (
        "Proxyn bevarar inte mottagarens Content-Type — SIE-filens teckenkodning "
        "går då förlorad."
    )


# -- Ingen publik yta ------------------------------------------------------


def test_ingen_marknadssida_och_inget_paket():
    """Bokföringen ska inte synas på hemsidan ännu.

    Beslut 2026-08-23: flik i dashboarden, inget på snajp.se. Testet finns för
    att beslutet ska gå att bryta AVSIKTLIGT och inte av misstag, t.ex. genom
    att någon lägger till ett paket i prissättningen "för fullständighetens
    skull".
    """
    assert not (ROT / "app" / "bokforing").exists(), "En marknadssida för bokföring har lagts till."
    pricing = (ROT / "lib" / "pricing.ts").read_text(encoding="utf-8")
    assert "bokforing" not in pricing.lower(), "Bokföringen har lagts till i prissättningen."
