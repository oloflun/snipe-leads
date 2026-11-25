#!/usr/bin/env python3
"""Skriver docs/crm/openapi.json ur koden.

    python scripts/crm_openapi.py            # skriv filen
    python scripts/crm_openapi.py --kontroll # fäll om filen inte stämmer med koden

Specifikationen för Snajp CRM:s publika API byggs ur routrarna i
snajp-support/app/api/crm_v1.py. Filen i docs/ är den kunden får och den som
går att läsa utan nyckel. Den ska alltid stämma med koden: testet
snajp-support/tests/crm/test_openapi_fil.py fäller annars, så att ett ändrat
fält inte kan nå drift med en gammal specifikation bredvid.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROT = Path(__file__).resolve().parents[1]
FIL = ROT / "docs" / "crm" / "openapi.json"

sys.path.insert(0, str(ROT / "snajp-support"))


def bygg() -> bytes:
    from app.api import crm_v1

    return (json.dumps(crm_v1.specifikation(), ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def main() -> int:
    ny = bygg()
    if "--kontroll" in sys.argv:
        if not FIL.exists() or FIL.read_bytes() != ny:
            print(f"{FIL.relative_to(ROT)} stämmer inte med koden. Kör: python scripts/crm_openapi.py")
            return 1
        print("Specifikationen stämmer med koden.")
        return 0
    FIL.parent.mkdir(parents=True, exist_ok=True)
    # write_bytes: Path.write_text ger CRLF på Windows, och repot är LF.
    FIL.write_bytes(ny)
    print(f"Skrev {FIL.relative_to(ROT)} ({len(ny)} byte).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
