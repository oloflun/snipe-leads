"""Ingen menypost i inställningarna får peka på en sida som inte finns.

`settingsGroups` (menyn) och `settingsSections` (dispatchern) är två listor i
samma fil, och de måste stämma överens. Gör de inte det svarar posten 404 —
alltså en meny som leder till en tom sida, vilket är hur "Röst och tonläge
dirigerar till Översikt" en gång upptäcktes.

Testet läser filen som text i stället för att köra TypeScript. Det räcker för
frågan som ställs, och det kan köras i samma svit som resten.
"""

from __future__ import annotations

import re
from pathlib import Path

ROUTES = Path(__file__).resolve().parents[1] / "lib" / "routes.ts"
KALLA = ROUTES.read_text(encoding="utf-8")


def _menyposter() -> set[str]:
    """Alla `href: "/settings…"` inuti settingsGroups."""
    block = KALLA.split("export const settingsGroups")[1].split("export function settingsGroups")[0]
    return set(re.findall(r'href:\s*"(/settings[^"]*)"', block))


def _dispatcherns_sluggar() -> set[str]:
    """Nycklarna i `settingsSections`, översatta till adresser."""
    block = KALLA.split("const settingsSections:")[1].split("};")[0]
    sluggar = set(re.findall(r'^\s*"?([a-z]*)"?:\s*"[a-z]+"', block, re.MULTILINE))
    return {"/settings" if s == "" else f"/settings/{s}" for s in sluggar}


def test_varje_menypost_har_en_sida():
    meny = _menyposter()
    assert meny, "Inga menyposter lästes — regexen har slutat matcha, inte menyn."

    saknade = sorted(meny - _dispatcherns_sluggar())
    assert not saknade, (
        f"{saknade} står i inställningsmenyn men saknas i settingsSections. "
        "Posten svarar 404 för den som klickar."
    )


def test_min_arbetsyta_ar_borta_ur_installningarna():
    """Sidan var en mock-sammanfattning som dessutom visades för supportkunder.
    Sammanfattningen är numera startsidan; två av samma sak är en för många."""
    assert "/settings/arbetsyta" not in KALLA
    assert '"arbetsyta"' not in KALLA


def test_menyn_anvander_vanlig_svenska():
    """Sälj och support ska inte mötas av ICP, autonomi eller SOUL i menyn."""
    block = KALLA.split("export const settingsGroups")[1].split("export function settingsGroups")[0]
    etiketter = re.findall(r"sv:\s*\"([^\"]+)\"", block)
    jargon = [e for e in etiketter if any(ord in e.lower() for ord in ("icp", "soul", "autonomi"))]
    assert not jargon, f"Menyn ska tala vanlig svenska, inte {jargon}."


def test_rosten_ar_delad_mellan_agenterna():
    """SOUL styr hur BÅDA agenterna låter. Låg den kvar bakom leads-grinden
    svarade /settings/soul 404 för en supportkund."""
    grind = KALLA.split("const settingsSectionProduct")[1].split("};")[0]
    assert "soul" not in grind
    assert "regler" in grind, "Kundtjänstens regelsida ska kräva support-paketet."
