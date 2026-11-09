"""Plattformsadminens lösenord får inte stå som reservvärde i ett skript.

Fas 0-fyndet K1 (2026-11-09): tre QA-skript bar `process.env.QA_ADMIN_LOSEN ??
"<lösenordet>"`, och `railway_agentsajt.py` hade det som konstant. Kontot läser
alla kunder och byter kund med skrivrätt, så ett lösenord i koden var ett
lösenord i varje klon och i hela historiken.

Testet letar efter FORMEN, inte värdet: en adminhemlighet med en strängliteral
som reserv. Hemligheten ska läsas ur miljön eller `.env.deploy`
(scripts/qa_hemlighet.mjs) och skriptet ska stanna när den saknas.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SKRIPT = ROOT / "scripts"

#: `process.env.X_LOSEN ?? "..."` och `os.environ.get("X_PASSWORD", "...")`
#: för de namn som hör till riktiga konton. Lokala och syntetiska testkonton
#: (QA_KUND, QA_TEST, QA_NY) står utanför med flit: de finns bara som fixturer.
_ADMINNAMN = r"(?:QA_ADMIN_LOSEN|AGENTSAJT_LOSEN)"
_JS_RESERV = re.compile(rf"process\.env\.{_ADMINNAMN}\s*(?:\?\?|\|\|)\s*[\"'`]")
_PY_RESERV = re.compile(rf"environ\.get\(\s*[\"']{_ADMINNAMN}[\"']\s*,\s*[\"']")


def test_inget_skript_bar_adminlosenordet_som_reservvarde():
    traffar = []
    for fil in sorted(SKRIPT.glob("*")):
        if fil.suffix not in (".mjs", ".js", ".py", ".ts", ".sh", ".ps1"):
            continue
        text = fil.read_text(encoding="utf-8", errors="replace")
        if _JS_RESERV.search(text) or _PY_RESERV.search(text):
            traffar.append(fil.name)
    assert not traffar, (
        f"Adminlösenord med strängliteral som reserv i: {traffar}. "
        "Läs det med hemlighet() ur scripts/qa_hemlighet.mjs eller ur .env.deploy."
    )


def test_agentsajtens_inloggning_laser_losenordet_ur_hemlighetsfilen():
    kalla = (SKRIPT / "railway_agentsajt.py").read_text(encoding="utf-8")
    assert 'store.get("QA_ADMIN_LOSEN")' in kalla
    assert not re.search(r"^LOSEN\s*=\s*[\"']", kalla, re.MULTILINE), (
        "railway_agentsajt.py bär lösenordet som konstant igen."
    )
