"""Knappen i leads-formuläret måste träffa en route som finns.

`LeadsRunForm` anropar backenden genom catch-all-proxyn:

    fetch(`/api/snajp-support${path}`)  ->  FastAPI  /api${path}

Sökvägarna är strängar i båda ändar. Ingen typ, ingen import, ingenting som
faller vid bygget — och de tre som räknas är: lägg till bolag, starta
körningen, polla jobbet. Exempelbolag är borta ur formuläret (bara /demo).

Döps en route om i backenden svarar knappen 404 med ett meddelande som handlar
om något annat, och felet syns först när någon klickar. Det här testet läser
BÅDA sidorna och jämför dem, i stället för att lita på att den som byter namn
råkar söka i rätt fil.

Ligger i repo-rotens svit och inte i backendens, eftersom det är just
korsningen mellan de två delsystemen som mäts.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "snajp-support"))

from app.main import app  # noqa: E402

FORMULAR = ROOT / "components" / "leads" / "LeadsRunForm.tsx"
PROXY_PREFIX = "/api/snajp-support"

#: `anropa("/leads/...")` — proxyns egen prefix läggs på inne i funktionen.
_ANROP_RE = re.compile(r"""anropa(?:<[^>]*>)?\(\s*["'`](/[^"'`]+)["'`]""")


def _registrerade_vagar() -> set[str]:
    """Backendens egna vägar, lästa ur OpenAPI-schemat.

    Inte ur `app.routes`: den här FastAPI-versionen lägger en inkluderad router
    som ETT objekt utan `path` i listan, så en naiv genomgång ser bara de
    routes som deklarerats direkt på appen — alltså /health och /docs. Ett test
    byggt på den listan hade fällt varenda korrekt sökväg.

    Schemat är dessutom samma dokument tjänsten publicerar i drift, så det går
    att ställa exakt samma fråga mot en deploy.
    """
    return set(app.openapi()["paths"])


def _ui_vagar() -> set[str]:
    return set(_ANROP_RE.findall(FORMULAR.read_text(encoding="utf-8")))


def test_formularet_anropar_minst_de_tre_stegen():
    # Faller listan tom hade testet nedan blivit grönt utan att mäta något —
    # det vanligaste sättet för ett statiskt test att sluta betyda något.
    vagar = _ui_vagar()

    assert "/leads/prospects" in vagar
    assert "/leads/runs/batch" in vagar
    assert "/leads/jobb/" in "".join(vagar) or any(v.startswith("/leads/jobb/") for v in vagar)
    assert "/leads/prospects/exempel" not in vagar


#: Next-routes som proxar till en annan FastAPI-väg än sin egen sökväg.
#: `/leads/jobb/{id}` → `/api/jobs/{id}` med sessionstenant (inte den anonyma
#: `/jobs/{id}`-routen, som slår upp under demonyckeln).
_NEXT_PROXIES = ("/leads/jobb/",)


def test_varje_anrop_traffar_en_route_som_finns():
    registrerade = _registrerade_vagar()

    saknade = sorted(
        v
        for v in _ui_vagar()
        if not any(v.startswith(p) for p in _NEXT_PROXIES)
        and f"/api{v}" not in registrerade
    )

    assert not saknade, (
        f"LeadsRunForm anropar {saknade}, som inte finns i backenden. "
        "Proxyn lägger på /api — se app/api/snajp-support/[...path]/route.ts."
    )


def test_proxyprefixet_i_formularet_ar_det_proxyn_lyssnar_pa():
    # Prefixet står som en literal i fetch-anropet. Byts katalogen under
    # app/api/ utan att strängen följer med går varje anrop till en 404 som
    # ser ut som ett backendfel.
    assert PROXY_PREFIX in FORMULAR.read_text(encoding="utf-8")
    assert (ROOT / "app" / "api" / "snajp-support" / "[...path]" / "route.ts").exists()


# -- Översikten ------------------------------------------------------------
#
# Startsidan räknar sina siffror ur sju endpoints. Samma sorts strängar i båda
# ändar som ovan, med en skillnad som gör dem värre: en 404 här ger inte ett
# felmeddelande utan ett em-streck i en ruta. Vyn är byggd för att TÅLA en död
# endpoint (se modulens docstring i Oversikt.tsx), så en omdöpt route ser ut
# som att kunden inte har någon data.

OVERSIKT = ROOT / "components" / "dashboard" / "Oversikt.tsx"
REGLER = ROOT / "components" / "settings" / "SupportRegler.tsx"

#: `hamta<...>("/leads/queue")` och `api<...>("/rules", …)`. Typargumentet är
#: lazy eftersom det kan innehålla egna `>` — `Record<string, number>` fällde
#: ett `[^>]*`-mönster tyst genom att matcha noll sökvägar.
_OVERSIKT_RE = re.compile(r"""\b(?:hamta|api)(?:<.*?>)?\(\s*["'`](/[^"'`?]+)""")


def _vagar_i(fil: Path) -> set[str]:
    return set(_OVERSIKT_RE.findall(fil.read_text(encoding="utf-8")))


def test_oversikten_anropar_de_vagar_talen_bygger_pa():
    # Samma spärr som ovan: en tom lista hade gjort nästa test grönt utan att
    # mäta något.
    vagar = _vagar_i(OVERSIKT)

    for vag in (
        "/leads/prospects",
        "/leads/runs",
        "/leads/queue",
        "/leads/config",
        "/inbox",
        "/kb",
    ):
        assert vag in vagar, f"Översikten hämtar inte längre {vag} — vilket tal försvann?"


def test_varje_vag_i_oversikten_och_reglerna_finns_i_backenden():
    registrerade = _registrerade_vagar()
    vagar = _vagar_i(OVERSIKT) | _vagar_i(REGLER)

    saknade = sorted(v for v in vagar if f"/api{v}" not in registrerade)

    assert not saknade, (
        f"Översikten anropar {saknade}, som inte finns i backenden. "
        "Proxyn lägger på /api — se app/api/snajp-support/[...path]/route.ts."
    )


def test_reglerna_bor_i_installningarna_och_inte_i_inkorgen():
    """Panelen flyttade från components/snajp/Dashboard.tsx till
    /settings/regler. Blir den kvar på båda ställena driver de isär, och kunden
    ändrar en regel på ett ställe där den inte gäller."""
    inkorg = (ROOT / "components" / "snajp" / "Dashboard.tsx").read_text(encoding="utf-8")

    assert "/settings/regler" in inkorg, "Inkorgen ska länka till reglerna, inte gömma dem."
    assert "rulesOpen" not in inkorg, "Den gamla regelpanelen ligger kvar i inkorgen."
    assert "/rules" in _vagar_i(REGLER)
