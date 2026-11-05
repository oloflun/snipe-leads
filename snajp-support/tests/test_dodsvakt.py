"""Dödsvakten: en låst händelseloop avslutar processen, en frisk gör det inte.

Bakgrund 2026-11-05: api hängde i produktionen och www.snajp.se visade "svårt
att nå sin motor" på varje flik tills tjänsten startades om för hand. Railway
startar bara om en process som dör. Testerna kör i en egen process, eftersom
vakten avslutar hela processen när den löser ut.
"""

from __future__ import annotations

import subprocess
import sys
import textwrap
from pathlib import Path

ROT = Path(__file__).resolve().parents[1]


def _kor(kropp: str) -> subprocess.CompletedProcess:
    skript = textwrap.dedent(
        """
        import asyncio, time
        from app.loopvakt import starta_dodsvakt

        async def main():
        {kropp}

        asyncio.run(main())
        print("KLAR")
        """
    ).format(kropp=textwrap.indent(textwrap.dedent(kropp), "    "))
    return subprocess.run(
        [sys.executable, "-c", skript], cwd=ROT, capture_output=True, text=True, timeout=30
    )


def test_last_loop_avslutar_processen_med_stacken():
    # time.sleep håller loopen, precis som en regex eller ett synkront anrop.
    utfall = _kor(
        """
        starta_dodsvakt(1)
        time.sleep(4)
        """
    )
    assert utfall.returncode != 0
    assert "KLAR" not in utfall.stdout
    # Stacken pekar ut raden som höll loopen: det är diagnosen i Railways logg.
    assert "Timeout" in utfall.stderr or "Thread" in utfall.stderr


def test_frisk_loop_lever_vidare():
    utfall = _kor(
        """
        stoppa = starta_dodsvakt(1)
        await asyncio.sleep(3)
        stoppa()
        """
    )
    assert utfall.returncode == 0, utfall.stderr
    assert "KLAR" in utfall.stdout


def test_stoppad_vakt_loser_inte_ut_efter_att_loopen_stangt():
    # TestClient och lifespan-slutet stänger loopen; processen lever vidare.
    utfall = _kor(
        """
        stoppa = starta_dodsvakt(1)
        await asyncio.sleep(0.1)
        stoppa()
        time.sleep(2.5)
        """
    )
    assert utfall.returncode == 0, utfall.stderr


def test_noll_ar_av():
    utfall = _kor(
        """
        stoppa = starta_dodsvakt(0)
        time.sleep(1.5)
        stoppa()
        """
    )
    assert utfall.returncode == 0, utfall.stderr
