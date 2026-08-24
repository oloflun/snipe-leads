"""Bokföringen är en PRODUKT, och grinden är entitlement på varje yta.

## Vad som ändrades, och varför testet ser annorlunda ut

Fram till 2026-08-23 var bokföringen admin-endast: ingen kund hade köpt den,
den hade inget pris och ingen marknadssida. Den här filen vaktade det beslutet
på fem ställen.

Nu säljs den. Grinden är `products` precis som för leads och support, och det
som måste hänga ihop är samma sak som förut fast med ett annat villkor: menyn,
`WorkspaceSection` och proxyn ska säga SAMMA sak. En meny som visar fliken mot
en proxy som svarar 404 är en produkt som ser trasig ut för den som betalat
för den.

## Mekanismtesterna står kvar, och de vaktar inte längre bokföringen

`adminOnly` har noll användare i dag. Flaggan och dess fail-closed-filter finns
kvar för nästa admin-endast yta, och testerna nedan vaktar MEKANISMEN — att
defaulten är `false` och att varje anropsplats tar ställning. De hade annars
tystnat helt, och en tyst grind är en grind ingen märker att den försvinner.

Testet läser filerna som text. Det räcker för frågan som ställs och kan köras i
samma svit som resten — se test_preview_routernas_natbarhet.py.
"""

from __future__ import annotations

import re
from pathlib import Path

ROT = Path(__file__).resolve().parents[1]
ROUTES = (ROT / "lib" / "routes.ts").read_text(encoding="utf-8")
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
ROUTES_KOD = _utan_kommentarer(ROUTES)
SECTION_KOD = _utan_kommentarer(SECTION)


# -- 1. Bokföringen är en produkt -----------------------------------------


def test_bokforing_ar_en_productkey():
    assert re.search(r'ProductKey\s*=\s*"leads"\s*\|\s*"support"\s*\|\s*"bookkeeping"', ROUTES_KOD), (
        "bookkeeping saknas i ProductKey. Utan den är entitlement-grinden nedan "
        "inte ens typmässigt möjlig."
    )
    assert re.search(r'productKeys\s*=\s*\[[^\]]*"bookkeeping"', ROUTES_KOD), (
        "bookkeeping saknas i productKeys. Typen och listan MÅSTE följas åt — "
        "listan är det som itereras vid rendering."
    )


def test_routen_grindas_pa_entitlement_inte_admin():
    rad = next((r for r in ROUTES_KOD.splitlines() if "/dashboard/bokforing" in r), None)
    assert rad is not None, "Bokföringsrouten saknas i appRoutes."
    assert 'product: "bookkeeping"' in rad, f"Routen har fel produkt: {rad.strip()}"
    assert "adminOnly" not in rad, (
        "Routen är fortfarande admin-märkt. Då ser en kund som KÖPT bokföringen "
        "inte fliken."
    )


def test_migrationen_slapper_in_vardet():
    """Kolumnen måste tillåta värdet, annars går produkten inte att dela ut.

    Både check-villkoret och `set_workspace_products` räknar upp listan, och de
    måste ändras tillsammans — se 047 om varför uppräkningen finns på två
    ställen med flit.
    """
    sql = (ROT / "supabase" / "migrations" / "047_bookkeeping_entitlement.sql").read_text(
        encoding="utf-8"
    )
    villkor = re.findall(r"array\[[^\]]*\]::text\[\]", sql)
    assert villkor, "047 rör ingen produktlista."
    assert all("bookkeeping" in v for v in villkor), (
        "En av uppräkningarna i 047 saknar bookkeeping. Kolumnen skulle då "
        "tillåta värdet medan RPC:n vägrar skriva det, eller tvärtom."
    )


# -- 2. Mekanismen för admin-endast ytor står kvar, tom -------------------


def test_filtret_ar_fail_closed():
    """`isAdmin = false` som default.

    Motsatt default hade gjort varje ny anropsplats till en potentiell läcka:
    den som glömmer flaggan hade visat MER, inte mindre. Ingen route använder
    `adminOnly` i dag — testet vaktar mekanismen inför nästa som gör det.
    """
    assert re.search(r"isAdmin\s*=\s*false", ROUTES_KOD), (
        "routesForProducts måste defaulta isAdmin till false."
    )


def test_filtret_faktiskt_grindar_pa_flaggan():
    assert re.search(r"!route\.adminOnly\s*\|\|\s*isAdmin", ROUTES_KOD), (
        "adminOnly-flaggan läses inte i routesForProducts — då är den dekoration."
    )


def test_varje_anropsplats_i_repot_skickar_admin():
    """VARJE `routesForProducts`-anrop, inte ett känt antal i en känd fil.

    Den första versionen letade i AppShell och hävdade att anropen var exakt
    två. Det fanns tre — den tredje i `components/admin/AdminShell.tsx`, och
    eftersom filtret är fail-closed försvann fliken tyst just där.

    Testet räknar därför inte anrop längre. En ny anropsplats fälls
    automatiskt.
    """
    anropsplatser: list[tuple[str, str]] = []
    for fil in sorted((ROT / "components").rglob("*.tsx")) + sorted((ROT / "app").rglob("*.tsx")):
        kalla = _utan_kommentarer(fil.read_text(encoding="utf-8"))
        for block in re.findall(r"routesForProducts\((.*?)\)", kalla, re.DOTALL):
            anropsplatser.append((str(fil.relative_to(ROT)), block))

    assert anropsplatser, "Hittade inga anrop — testet mäter ingenting."

    utan_admin = [(fil, block.strip()) for fil, block in anropsplatser if "isAdmin" not in block]
    assert not utan_admin, (
        "Dessa anrop tar inte ställning till adminOnly-routerna. Filtret är "
        "fail-closed, så de FÖRSVINNER tyst i just den menyn:\n"
        + "\n".join(f"  {fil}: routesForProducts({block})" for fil, block in utan_admin)
    )


# -- 3. Grinden på servern ------------------------------------------------


def test_bokforing_gar_via_entitlement_kartan():
    """Motsatsen till vad det här testet krävde före 2026-08-23.

    `sectionProduct` är den karta `WorkspaceSection` grindar på. Står
    bokföringen inte där finns ingen entitlement-kontroll för den alls.
    """
    karta = SECTION_KOD.split("const sectionProduct")[1].split("}")[0]
    assert re.search(r'bokforing:\s*"bookkeeping"', karta), (
        "bokforing saknas i sectionProduct — då grindas vyn inte på entitlement."
    )


def test_ingen_admin_gren_kvar_for_bokforing():
    """Den gamla adminkontrollen får inte ligga kvar bredvid den nya.

    Två grindar för samma yta är en grind för mycket: den som köpt produkten
    hade mötts av 404 från den kvarglömda.
    """
    assert 'section === "bokforing"' not in SECTION_KOD, (
        "Det finns en särskild bokforing-gren kvar i WorkspaceSection. "
        "Entitlement-kontrollen nedanför täcker den redan."
    )


def test_proxyn_grindar_pa_entitlement_fore_tenant_uppslaget():
    """Entitlement FÖRST.

    En tenant-uppslagning före grinden lämnar en mätbar tidsskillnad som
    avslöjar om kontot finns, och gör dessutom ett databasanrop åt någon som
    inte får vara där.
    """
    assert "resolveDashboardState" in PROXY, "Proxyn läser inte arbetsytans produkter."
    assert 'products.includes("bookkeeping")' in PROXY, (
        "Proxyn grindar inte på bookkeeping-entitlement."
    )
    assert PROXY.index("resolveDashboardState(") < PROXY.index("requireSnajpTenant("), (
        "requireSnajpTenant körs före entitlement-kontrollen i proxyn."
    )
    assert "getPlatformAdmin" not in PROXY, (
        "Proxyn grindar fortfarande på plattformsadmin. En kund som köpt "
        "bokföringen når då inte sitt eget API."
    )


def test_proxyn_kraver_ocksa_en_session():
    """`signedIn` är inte bältesspänne på hängslen.

    `resolveDashboardState()` returnerar ANONYMOUS utan session, och den listan
    är PERMISSIV med flit — den finns för marknadsföringsytorna. Utan
    session-kontrollen passerar en oinloggad förfrågan entitlement-grinden och
    faller först på tenant-uppslaget med 401.

    Uppmätt mot dev 2026-08-24: POST utan session gav 401, inte 404. Ingen data
    läckte, men ytan bekräftades — vilket är precis vad 404:an finns för att
    undvika.
    """
    assert "signedIn" in PROXY, "Proxyn kontrollerar inte att någon är inloggad."
    assert re.search(r"!signedIn\s*\|\|\s*!products\.includes", PROXY), (
        "Session- och entitlement-kontrollen sitter inte i samma grind, alltså "
        "inte före tenant-uppslaget."
    )


def test_proxyn_svarar_404_och_inte_403():
    """403 bekräftar att ytan finns. Samma val som app/admin/layout.tsx."""
    gren = PROXY.split('products.includes("bookkeeping")')[1].split("return")[1].split(";")[0]
    assert "404" in gren, f"Proxyn svarar inte 404 utan entitlement: {gren.strip()}"
    assert "403" not in gren


def test_proxyn_ar_binarsaker():
    """Kvittot in är multipart, SIE-filen ut är CP437.

    Går någondera genom en text-rundtur blir den obrukbar: kvittot oläsbart,
    SIE-filen avvisad av kundens bokföringsprogram.
    """
    assert "arrayBuffer()" in PROXY, "Proxyn strömmar inte kroppen som bytes."
    assert "request.text()" not in PROXY, "Proxyn läser kroppen som text."
    assert 'svar.headers.get("content-type")' in PROXY, (
        "Proxyn bevarar inte mottagarens Content-Type — SIE-filens teckenkodning "
        "går då förlorad."
    )


# -- 4. Den publika ytan finns nu -----------------------------------------


def test_marknadssidan_och_paketet_finns():
    """Inverterat mot den gamla versionen, som krävde att de INTE fanns.

    Beslutet ändrades 2026-08-23: bokföringen säljs. Testet står kvar i
    inverterad form så att beslutet går att bryta AVSIKTLIGT och inte genom att
    någon råkar ta bort sidan.
    """
    assert (ROT / "app" / "bokforing" / "page.tsx").exists(), "Marknadssidan saknas."
    pricing = (ROT / "lib" / "pricing.ts").read_text(encoding="utf-8")
    assert '"bookkeeping"' in pricing, "Bokföringen saknas i prissättningen."


def test_paketet_har_det_beslutade_priset():
    """1 990 kr/mån, beslutat 2026-08-24.

    Testet finns för att priset ska gå att ändra AVSIKTLIGT. En prislapp som
    tyst byts är en prislapp en kund upptäcker på fakturan.

    `prisPerManad` är fortfarande `number | null` i typen, och det ska den vara:
    null är ett giltigt tillstånd för en produkt vars pris inte satts, och
    nästa produkt börjar där. Se PRIS_SAKNAS i lib/pricing.ts.
    """
    pricing = (ROT / "lib" / "pricing.ts").read_text(encoding="utf-8")
    block = pricing.split('id: "bookkeeping"')[1].split("}")[0]
    assert "prisPerManad: 1990" in block, (
        "Bokföringspaketets pris är inte 1990. Ändras det ska både raden här och "
        "beslutsdatumet i pricing.ts uppdateras."
    )


def test_typen_tillater_fortfarande_ett_osatt_pris():
    """Null-vägen får inte tas bort bara för att just det här paketet fick ett
    pris — nästa produkt börjar utan ett, och `PRIS_SAKNAS` är vad den visar."""
    pricing = (ROT / "lib" / "pricing.ts").read_text(encoding="utf-8")
    assert "prisPerManad: number | null" in pricing
    assert "PRIS_SAKNAS" in pricing
