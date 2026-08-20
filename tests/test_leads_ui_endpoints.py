"""Knappen i leads-formuläret måste träffa en route som finns.

`LeadsRunForm` anropar backenden genom catch-all-proxyn:

    fetch(`/api/snajp-support${path}`)  ->  FastAPI  /api${path}

Sökvägarna är strängar i båda ändar. Ingen typ, ingen import, ingenting som
faller vid bygget — och tre av dem är hela vägen in i produkten för en ny kund:
lägg till bolag, fyll på med exempelbolag, starta körningen.

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
    assert "/leads/prospects/exempel" in vagar
    assert "/leads/runs/batch" in vagar


def test_varje_anrop_traffar_en_route_som_finns():
    registrerade = _registrerade_vagar()

    saknade = sorted(v for v in _ui_vagar() if f"/api{v}" not in registrerade)

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
