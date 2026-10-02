"""Körningens motor: sök, förfiltrera, triagera — tills N leverbara leads.

## Varför "N" betyder leverbara leads, inte kandidater

Uppmätt 2026-09-29 hos Alunix: kunden beställde 3 leads och fick 3
kandidater som Iris själv underkände — plus inga utkast. Ett beställt antal
är ett löfte om leads kunden kan agera på: kvalificerade (nivå A/B), över
kundens egen tröskel och med en mejlväg, så att utkastagenten kan skriva
till dem (INV-LEADS-N-001).

## Flödet

    sökrunda (profilstyrd, geo-ring för ring)
        → förfilter (kod, känd data)          → tratten
        → Jev-triage (läge pa fäller säkra missar) → tratten
        → kandidatpoolen
    fyll_pa: köar research för så många som behövs; varje avslutat
    prospektjobb rapporterar tillbaka och fyll_pa körs igen, tills målet är
    nått, poolen och rundorna är slut, taket (4×N undersökta) är nått eller
    dygnsbudgeten tar slut. Slutet är alltid ärligt: tratten namnger det
    kriterium som strypte.

Körningens tillstånd bor i batchjobbets eget resultat (jobbstoret, TTL 1 h)
— ingen ny tabell. ponytail: en leads-worker per process (config
leads_workers=1) gör läs-ändra-skriv sekventiellt; fler workers eller
repliker kräver ett lås runt `uppdatera`.
"""

from __future__ import annotations

from collections import Counter
from typing import Any

from . import jev
from .discovery import hitta_bolag
from .forfilter import forfiltrera
from .geo import _prefix_ur_postnr
from .webbsignal import mat_webbplats

MAX_RUNDOR = 3
TAK_FAKTOR = 4
MAX_PER_RUNDA = 10


def ny_korning(*, mal: int, scope: str, overrides: dict | None, is_test: bool) -> dict[str, Any]:
    return {
        "mal": mal,
        "levererade": 0,
        "undersokta": 0,
        "pagaende": 0,
        "kandidater": [],
        "rundor": 0,
        "tak": mal * TAK_FAKTOR,
        "tratt": [],
        "jobs": [],
        "klar": False,
        "slut_orsak": None,
        "flaskhals": None,
        "scope": scope,
        "overrides": overrides,
        "is_test": is_test,
    }


def _ring_index(profil: dict[str, Any], kandidat: dict[str, Any]) -> int:
    """Lägre = tidigare i kundens geografiska prioritet. Okänt sist."""
    prefix = _prefix_ur_postnr(kandidat.get("postnr"))
    for i, ring in enumerate(profil.get("geo_prioritet") or []):
        if prefix is not None and f"{prefix:03d}" in (ring.get("postnr_prefix") or []):
            return i
    return len(profil.get("geo_prioritet") or []) + (0 if prefix is not None else 1)


async def sokrunda(
    profil: dict[str, Any], icp: dict[str, Any], korning: dict[str, Any], *, uteslut: set[str]
) -> None:
    """En sökrunda i nästa geo-ring. Fyller korning["kandidater"] och
    korning["tratt"]; höjer rundor. Kastar DiscoveryError om sökningen
    själv faller (anroparen avgör vad det betyder)."""
    behov = korning["mal"] - korning["levererade"]
    antal = min(MAX_PER_RUNDA, max(3, 2 * behov))
    ring = korning["rundor"]
    korning["rundor"] += 1
    fynd = await hitta_bolag(icp, antal, uteslut_namn=uteslut, profil=profil, ring=ring)
    kvar: list[dict[str, Any]] = []
    for kandidat in fynd:
        skal = forfiltrera(profil, kandidat, exclude_domains=icp.get("exclude_domains"))
        if skal:
            korning["tratt"].append({"namn": kandidat["company_name"], "steg": "förfilter", "skal": skal})
            continue
        fakta = await mat_webbplats(kandidat.get("website"))
        kandidat["webbsignaler"] = fakta.get("rader") or []
        # Registerkällan (merinfo) har redan triagerat sina kandidater; en
        # andra Jev-fråga på samma bolag är bara kostnad.
        triage = kandidat.get("jev_triage") or await jev.triage(
            profil, kandidat, utdrag=fakta.get("utdrag") or "", signaler=kandidat["webbsignaler"]
        )
        if triage:
            kandidat["jev_triage"] = triage
            if triage.get("beslut") == "fall":
                korning["tratt"].append(
                    {
                        "namn": kandidat["company_name"],
                        "steg": "jev",
                        "skal": "; ".join(triage.get("fall_skal") or []),
                        "belagg": triage.get("stodrad"),
                    }
                )
                continue
        kvar.append(kandidat)
    kvar.sort(key=lambda k: _ring_index(profil, k))
    korning["kandidater"].extend(kvar)


def registrera_utfall(korning: dict[str, Any], *, namn: str, leverbar: bool, skal: str | None) -> None:
    korning["pagaende"] = max(0, korning["pagaende"] - 1)
    korning["undersokta"] += 1
    if leverbar:
        korning["levererade"] += 1
    elif skal:
        korning["tratt"].append({"namn": namn, "steg": "research", "skal": skal})


def avsluta(korning: dict[str, Any], orsak: str) -> None:
    """Sätter slutet — och namnger flaskhalsen när målet inte nåddes."""
    korning["klar"] = True
    korning["slut_orsak"] = orsak
    if korning["levererade"] < korning["mal"] and korning["tratt"]:
        typer = Counter(str(t.get("skal") or "").split(":")[0].strip() for t in korning["tratt"])
        korning["flaskhals"] = typer.most_common(1)[0][0] or None


def sammanfatta(korning: dict[str, Any]) -> str:
    """Tratten i en mening, för kunden."""
    delar = [f"{korning['undersokta']} undersökta"]
    typer = Counter(str(t.get("skal") or "").split(":")[0].strip() for t in korning["tratt"])
    delar += [f"{antal} bortvalda: {typ.lower()}" for typ, antal in typer.most_common(3) if typ]
    text = ", ".join(delar) + f" → {korning['levererade']} leads."
    if korning["levererade"] < korning["mal"] and korning.get("flaskhals"):
        text += f" Det som strypte mest: {korning['flaskhals'].lower()}."
    return text


def demo() -> None:
    k = ny_korning(mal=2, scope="research_and_draft", overrides=None, is_test=True)
    k["pagaende"] = 2
    registrera_utfall(k, namn="A", leverbar=True, skal=None)
    registrera_utfall(k, namn="B", leverbar=False, skal="För stort: 700 anställda")
    k["tratt"].append({"namn": "C", "steg": "förfilter", "skal": "För stort: 120 anställda enligt källan"})
    avsluta(k, "slut_pa_kandidater")
    assert k["levererade"] == 1 and k["undersokta"] == 2 and k["flaskhals"] == "För stort"
    assert "För stort" in sammanfatta(k) or "för stort" in sammanfatta(k)
    profil = {"geo_prioritet": [{"etikett": "Sisjön", "postnr_prefix": ["421"]}, {"etikett": "Mölndal", "postnr_prefix": ["431"]}]}
    assert _ring_index(profil, {"postnr": "421 32"}) == 0
    assert _ring_index(profil, {"postnr": "431 30"}) == 1
    assert _ring_index(profil, {}) == 3
    print("korning: ok")


if __name__ == "__main__":
    demo()
