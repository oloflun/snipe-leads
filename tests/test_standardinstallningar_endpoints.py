"""Standardinställningarna måste träffa routes som finns — och skriva det
backenden faktiskt tar emot.

`lib/snajp/standard.ts` anropar backenden DIREKT med kundens tenant-nyckel, inte
genom catch-all-proxyn: den körs i uppstarten och i inloggningsvägen, alltså
innan det finns en request att proxa. Sökvägarna är därmed strängar i ena änden
och FastAPI-dekoratorer i den andra, utan något som faller vid bygget.

Vad ett fel här kostar: onboardingen fyller inte i något, kunden möts av tomma
fält, och `require_business_context` avbryter varje leads-körning med
"Produktbeskrivningen saknas" trots att kunden skrivit in den. Det är precis
det felet modulen finns för att stänga, och det syns bara i drift.

Ligger i repo-rotens svit av samma skäl som test_leads_ui_endpoints.py: det är
korsningen mellan de två delsystemen som mäts.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "snajp-support"))

from app.leads.icp import SMAFORETAG_ANSTALLDA, normalize_icp, validate_icp  # noqa: E402
from app.leads.soul import SOUL_KIND  # noqa: E402
from app.main import app  # noqa: E402

STANDARD = ROOT / "lib" / "snajp" / "standard.ts"
KALLA = STANDARD.read_text(encoding="utf-8")

#: `anrop(apiKey, "/api/leads/...")` — hela sökvägen står i anropet.
_ANROP_RE = re.compile(r"""anrop(?:<[^>]*>)?\(\s*apiKey,\s*["'`]([^"'`]+)["'`]""")


def _registrerade_vagar() -> set[str]:
    """Backendens egna vägar, lästa ur OpenAPI-schemat. Se
    test_leads_ui_endpoints._registrerade_vagar för varför inte app.routes."""
    return set(app.openapi()["paths"])


def _anropade_vagar() -> set[str]:
    """Utan query-strängen — OpenAPI beskriver vägen, inte parametrarna."""
    return {vag.split("?")[0] for vag in _ANROP_RE.findall(KALLA)}


def test_alla_anropade_vagar_finns_i_backenden():
    anropade = _anropade_vagar()
    # Faller listan tom blir påståendet nedan grönt utan att mäta något.
    assert anropade, "Inga anrop lästes ur standard.ts — regexen matchar inte längre."

    saknade = sorted(anropade - _registrerade_vagar())
    assert not saknade, (
        f"{saknade} anropas av lib/snajp/standard.ts men finns inte i backenden. "
        "Onboardingen fyller då inte i något, och kunden möts av tomma fält."
    )


def test_de_tre_falten_skrivs():
    """Produktbeskrivning, röstdokument och ICP — utan alla tre är kunden
    fortfarande hänvisad till att konfigurera för hand."""
    anropade = _anropade_vagar()
    for vag in ("/api/leads/context-docs", "/api/leads/soul", "/api/leads/config"):
        assert vag in anropade, f"{vag} anropas inte längre av standard.ts."


def test_produktdokumentets_kind_ar_det_backenden_laser():
    """`require_business_context` läser kind `product_marketing` och ingenting
    annat. Ett dokument med fel kind sparas utan fel och läses aldrig."""
    assert '"product_marketing"' in KALLA or "product_marketing" in KALLA, (
        "standard.ts skriver inte kind product_marketing — dokumentet hamnar då "
        "utanför det build_context_pack läser."
    )


def test_rostdokumentet_skrivs_som_soul_och_inte_som_kontextdokument():
    """SOUL har en egen endpoint med flit: kind-allowlisten i
    leads_tools._save_context_doc_impl utesluter 'soul' så att onboarding-agenten
    inte kan skriva kundens röstdokument. Skrevs det som ett kontextdokument
    härifrån hade den gränsen kringgåtts."""
    assert f'"{SOUL_KIND}"' not in KALLA, (
        f"standard.ts skickar kind {SOUL_KIND!r} som kontextdokument. "
        "Röstdokumentet ska gå via PUT /api/leads/soul."
    )


def test_storleksspannet_overlever_backendens_validering():
    """Att bara sätta `company_size` räcker INTE, och det syns inte i API:et.

    `_normalize_size` seedar ur `company_size` men skriver sedan över varje
    nyckel som finns i inkommande `size` — och ett `size` läst ur GET-svaret
    bär `anstallda_min: None`. Spannet nollades alltså av det egna svaret.
    Uppmätt, inte antaget; testet är regressionsspärren."""
    bas = normalize_icp({})
    minsta, storsta = SMAFORETAG_ANSTALLDA

    utan_size = dict(bas) | {"company_size": {"min": minsta, "max": storsta}}
    assert validate_icp(utan_size)["company_size"] == {"min": None, "max": None}, (
        "Backenden nollar inte längre company_size när size följer med. Läs om "
        "_normalize_size innan du förenklar storlek() i standard.ts."
    )

    med_size = dict(bas) | {
        "company_size": {"min": minsta, "max": storsta},
        "size": bas["size"] | {"anstallda_min": minsta, "anstallda_max": storsta},
    }
    validerad = validate_icp(med_size)
    assert validerad["company_size"] == {"min": minsta, "max": storsta}
    assert validerad["size"]["anstallda_min"] == minsta
    assert validerad["size"]["anstallda_max"] == storsta

    # Och att standard.ts faktiskt skickar båda.
    assert "anstallda_min" in KALLA and "company_size" in KALLA, (
        "standard.ts sätter inte längre båda storleksfälten. Spannet försvinner "
        "då tyst, och urvalet blir 'alla företag' utan att någon bestämt det."
    )


def test_storleksspannet_speglar_backendens_definition():
    """Talen är EU:s definition av småföretag och bor i backendens icp.py.
    Två kopior som glider isär betyder att formuläret visar ett spann och
    defaulten sätter ett annat."""
    minsta, storsta = SMAFORETAG_ANSTALLDA
    traff = re.search(r"const SMAFORETAG:\s*\[number,\s*number\]\s*=\s*\[(\d+),\s*(\d+)\]", KALLA)
    assert traff, "SMAFORETAG-konstanten hittades inte i standard.ts."
    assert (int(traff.group(1)), int(traff.group(2))) == (minsta, storsta), (
        f"standard.ts sätter {traff.group(1)}–{traff.group(2)} anställda, "
        f"backendens SMAFORETAG_ANSTALLDA säger {minsta}–{storsta}."
    )
