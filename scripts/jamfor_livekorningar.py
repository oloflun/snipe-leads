"""Jämför två livekörningar (docs/live-tests/*.json) — support eller leads.

    python scripts/jamfor_livekorningar.py support FORE.json EFTER.json
    python scripts/jamfor_livekorningar.py leads FORE.json EFTER.json

Skriver en kompakt tabell per scenario/prospekt: eskalering, kategori,
KB-träffar, steg, tokens, latens — och utkastens ämnesrader för leads.
Mätningen är körningens; tolkningen är läsarens.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


def _ladda(sokvag: str) -> dict:
    return json.loads(Path(sokvag).read_text(encoding="utf-8"))


def _stegtokens(r: dict) -> tuple[int, int]:
    logg = r.get("step_log") or []
    return (
        sum(s.get("tokens_in", 0) for s in logg),
        sum(s.get("tokens_out", 0) for s in logg),
    )


def jamfor_support(fore: dict, efter: dict) -> None:
    a, b = fore["results"], efter["results"]
    rubrik = f"{'scenario':<28} {'esk':>9} {'kategori':>20} {'kb':>5} {'steg':>6} {'tok ut':>10} {'ms':>10}"
    print(rubrik)
    print("-" * len(rubrik))
    for nyckel in sorted(set(a) | set(b)):
        for etikett, sida in (("FÖRE", a.get(nyckel)), ("EFTER", b.get(nyckel))):
            if not sida or not sida.get("_ok"):
                print(f"{nyckel:<28} {etikett}: körningen saknas/föll")
                continue
            _, ut = _stegtokens(sida)
            print(
                f"{(etikett + ' ' + nyckel)[:28]:<28} "
                f"{str(sida.get('escalated')):>9} "
                f"{str(sida.get('category'))[:20]:>20} "
                f"{len(sida.get('kb_sources') or []):>5} "
                f"{len(sida.get('step_log') or []):>6} "
                f"{ut:>10} "
                f"{sida.get('_wall_ms', 0):>10}"
            )
        print()


def jamfor_leads(fore: dict, efter: dict) -> None:
    a, b = fore.get("snajp", {}), efter.get("snajp", {})
    for nyckel in sorted(set(a) | set(b)):
        print(f"===== {nyckel}")
        for etikett, sida in (("FÖRE", a.get(nyckel)), ("EFTER", b.get(nyckel))):
            if not sida:
                print(f"  {etikett}: saknas")
                continue
            utk = sida.get("draft") or {}
            grund = (sida.get("draft") or {}).get("grounding") or utk.get("grounding") or {}
            print(
                f"  {etikett}: research {sida.get('research_ms', '?')} ms · "
                f"draft {sida.get('draft_ms', '?')} ms · "
                f"queued {utk.get('queued')} · grounding fired {grund.get('fired')}"
            )
            print(f"    ÄMNE: {utk.get('subject')}")
        print()


def main() -> None:
    if len(sys.argv) != 4 or sys.argv[1] not in ("support", "leads"):
        print(__doc__)
        raise SystemExit(2)
    lage, fore, efter = sys.argv[1], _ladda(sys.argv[2]), _ladda(sys.argv[3])
    (jamfor_support if lage == "support" else jamfor_leads)(fore, efter)


if __name__ == "__main__":
    main()
