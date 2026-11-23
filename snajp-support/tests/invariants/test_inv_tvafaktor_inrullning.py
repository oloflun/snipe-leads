"""Inrullningen av tvåfaktor kräver lösenordet på nytt (Codex runda 15, 2026-11-20).

En adminsession ensam fick rulla in en ny hemlighet. Med en stulen session
till ett konto utan aktiv tvåfaktor kunde en angripare då rulla in sin egen
hemlighet, få återställningskoderna och stänga ute ägaren. Nu prövar
`paborjaInrullning` lösenordet, under inloggningens spärr mot gissning, innan
någon hemlighet skapas, och databasen godtar bara en påbörjad inrullning från
de senaste femton minuterna (migration 148).

Statiskt: ordningen i servern och tidsgränsen i den senaste definitionen av
`tvafaktor_aktivera`. Databastestet `tests/db/test_tvafaktor.py` prövar
tidsgränsen mot en riktig databas.
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
ACTION = ROOT / "lib" / "actions" / "tvafaktor.ts"
MIGRATIONER = ROOT / "db" / "migrations"


def _funktion(kalla: str, namn: str) -> str:
    start = kalla.index(f"export async function {namn}(")
    slut = kalla.find("\nexport async function ", start + 1)
    return kalla[start: slut if slut > 0 else len(kalla)]


def test_inrullningen_provar_losenordet_innan_hemligheten_skapas():
    kropp = _funktion(ACTION.read_text(encoding="utf-8"), "paborjaInrullning")
    assert re.search(r"paborjaInrullning\(losenord: string\)", kropp)
    ordning = ["lasLosenordshash(", "arSparrad(", "verifyPassword(", "registreraForsok(",
               "nyTotpHemlighet(", "paborjaTvafaktor("]
    positioner = [kropp.find(steg) for steg in ordning]
    assert all(p >= 0 for p in positioner), dict(zip(ordning, positioner))
    assert positioner == sorted(positioner), dict(zip(ordning, positioner))


def test_aktiveringen_godtar_bara_en_farsk_paborjan():
    senaste = None
    for fil in sorted(MIGRATIONER.glob("*.sql")):
        text = fil.read_text(encoding="utf-8")
        if "create or replace function public.tvafaktor_aktivera(" in text:
            senaste = (fil.name, text)
    assert senaste is not None
    namn, text = senaste
    assert "and uppdaterad_at > now() - interval '15 minutes'" in text, namn
