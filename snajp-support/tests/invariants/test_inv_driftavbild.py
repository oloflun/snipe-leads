"""Driftavbilden (railway/Dockerfile.drift) bär varje skript den importerar.

Avbilden kör synken och migrationerna hos Railway och kopierar bara utvalda
filer ur scripts/, med en allowlist i Dockerfile.drift.dockerignore. När
railway_synk.py fick en ny lokal modul (begransning_spegel, Codex runda 15,
2026-11-20) saknades den i avbilden, och synken hade dött vid start med
ModuleNotFoundError. CI-jobbet som bygger avbilden fångade det; det här testet
fångar det före bygget: varje modul i scripts/ som ett kopierat skript
importerar ska kopieras och släppas igenom av allowlisten.
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SKRIPT = ROOT / "scripts"
DOCKERFILE = ROOT / "railway" / "Dockerfile.drift"
IGNORE = ROOT / "railway" / "Dockerfile.drift.dockerignore"


def _kopierade() -> set[str]:
    rader = [r for r in DOCKERFILE.read_text(encoding="utf-8").splitlines()
             if r.startswith("COPY ") and "./scripts/" in r]
    return {Path(f).name for r in rader for f in r.split()[1:-1] if f.startswith("scripts/")}


def _lokala_importer(fil: Path) -> set[str]:
    kalla = fil.read_text(encoding="utf-8")
    namn = set(re.findall(r"^\s*import\s+(\w+)", kalla, re.MULTILINE))
    namn |= set(re.findall(r"^\s*from\s+(\w+)\s+import\b", kalla, re.MULTILINE))
    return {f"{n}.py" for n in namn if (SKRIPT / f"{n}.py").is_file()}


def test_varje_lokal_import_finns_i_avbilden():
    kopierade = _kopierade()
    assert "railway_synk.py" in kopierade
    slapps = set(re.findall(r"^!scripts/(\S+)$", IGNORE.read_text(encoding="utf-8"), re.MULTILINE))
    att_gora = list(kopierade)
    sedda: set[str] = set()
    while att_gora:
        fil = att_gora.pop()
        if fil in sedda:
            continue
        sedda.add(fil)
        for beroende in _lokala_importer(SKRIPT / fil):
            assert beroende in kopierade, f"{fil} importerar {beroende}, som Dockerfile.drift inte kopierar"
            assert beroende in slapps, f"{beroende} saknas i allowlisten i Dockerfile.drift.dockerignore"
            att_gora.append(beroende)
    assert kopierade <= slapps, f"kopieras men stoppas av allowlisten: {sorted(kopierade - slapps)}"
