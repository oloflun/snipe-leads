"""Bedömningen av ett researchat bolag — räknad i KOD ur modellens utslag.

## Varför modellen inte får avgöra själv

Uppmätt 2026-09-29 hos Alunix: modellens fria `qualified` fällde en
tvåmansbyrå för "Juristbyråer är inte en del av målgruppen" — ett skäl som
inte stod någonstans i kundens profil. Modellen får därför bara ge ett utslag
PER kriterium i Iris-profilen (ja/nej/okänt, med belägg), och koden här
avgör nivå, poäng och kvalificering (INV-LEADS-PROFIL-001).

## Varför ett utslag utan verifierat belägg blir "okänt"

Ett ja eller nej ska gå att peka på: ett ordagrant citat ur det skrapade
materialet eller ur de mätta webbsignalerna. Ett citat som inte finns där är
en gissning, och en gissning får varken fälla eller lyfta ett bolag.

## Varför motiveringen aldrig kan bli tom

Den är det kunden köper (INV-LEADS-SCORE-001). Tom modellmotivering → koden
skriver den ur utslagen.
"""

from __future__ import annotations

import re
from typing import Any

from .geo import _prefix_ur_postnr
from .profil import KOMMUNER
from .scoring import MISS, OKAND, TRAFF

UTSLAG = {"ja": TRAFF, "nej": MISS, "okänt": OKAND, "okant": OKAND}
_VARDE = {TRAFF: 1.0, OKAND: 0.5, MISS: 0.0}

#: Poängtak för ett fällt bolag — samma tanke som kvalificeringsgrindens
#: TAK_ICP_FIT: modellens övriga bedömning kan vara riktig, men ett fällt
#: bolag ska aldrig sorteras över ett som kvalificerar.
TAK_FALLD = 30
#: Lägsta poäng för A-nivå (alla måste-kriterier ja krävs dessutom).
A_GRANS = 70


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").casefold()).strip(" .\"'”“")


def verifierade_belagg(belagg: object, korpus: str) -> list[dict[str, str]]:
    """Beläggen vars citat faktiskt står i materialet (normaliserat)."""
    k = _norm(korpus)
    ut: list[dict[str, str]] = []
    for b in belagg if isinstance(belagg, list) else []:
        if not isinstance(b, dict):
            continue
        citat = str(b.get("citat") or "").strip()
        if len(_norm(citat)) >= 4 and _norm(citat) in k:
            ut.append({"url": str(b.get("url") or "")[:500], "citat": citat[:300]})
    return ut


def _rad(nyckel: str, etikett: str, vikt: int, utfall: str, motivering: str, *, hart: bool,
         belagg: list[dict[str, str]] | None = None) -> dict[str, Any]:
    return {
        "nyckel": nyckel,
        "etikett": etikett,
        "vikt": vikt,
        "utfall": utfall,
        "motivering": motivering,
        "hart": hart,
        "belagg": belagg or [],
    }


def _ort_rad(profil: dict[str, Any], fynd: dict[str, Any], kand: dict[str, Any]) -> dict[str, Any] | None:
    kommuner = profil.get("kommuner") or []
    if not kommuner:
        return None
    postnr = fynd.get("postnummer") or kand.get("postnr")
    ort = str(fynd.get("ort") or kand.get("ort") or "").strip()
    valda = [KOMMUNER[k.casefold()] for k in kommuner if k.casefold() in KOMMUNER]
    prefix = _prefix_ur_postnr(postnr)
    etikett = "Ligger i " + " eller ".join(kommuner)
    if prefix is not None:
        inne = any(k.innehaller_prefix(prefix) for k in valda)
        return _rad("ort", etikett, 2, TRAFF if inne else MISS,
                    f"Postnummer {postnr} {'ligger' if inne else 'ligger inte'} i målområdet.", hart=True)
    if ort:
        if ort.casefold() in {k.namn.casefold() for k in valda}:
            return _rad("ort", etikett, 2, TRAFF, f"Orten {ort} ligger i målområdet.", hart=True)
        if ort.casefold() in KOMMUNER:
            return _rad("ort", etikett, 2, MISS, f"Orten {ort} ligger utanför målområdet.", hart=True)
        # En ort vi inte känner igen fäller inte: stadsdelar heter annat än
        # kommunen (Västra Frölunda är Göteborg).
        return _rad("ort", etikett, 2, OKAND, f"Orten {ort} kunde inte knytas till en kommun.", hart=True)
    return _rad("ort", etikett, 2, OKAND, "Adressen framgick inte av källmaterialet.", hart=True)


def _storlek_rad(profil: dict[str, Any], fynd: dict[str, Any], kand: dict[str, Any]) -> dict[str, Any] | None:
    lo, hi = profil.get("anstallda_min"), profil.get("anstallda_max")
    if lo is None and hi is None:
        return None
    etikett = f"Storlek {lo if lo is not None else '—'}–{hi if hi is not None else '—'} anställda"
    antal = fynd.get("antal_anstallda")
    if antal is None:
        antal = kand.get("anstallda")
    try:
        antal = int(antal) if antal is not None and not isinstance(antal, bool) else None
    except (TypeError, ValueError):
        antal = None
    if antal is None:
        return _rad("storlek", etikett, 1, OKAND, "Antalet anställda framgick inte.", hart=True)
    inne = (lo is None or antal >= lo) and (hi is None or antal <= hi)
    return _rad("storlek", etikett, 1, TRAFF if inne else MISS,
                f"{antal} anställda enligt källmaterialet.", hart=True)


def bedom(
    profil: dict[str, Any],
    fynd: dict[str, Any],
    *,
    korpus: str,
    kandidat: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Modellens utslag + hårda fakta → nivå, poäng, rader och motivering.

    `korpus` = skrapat material + mätta webbsignaler; beläggen verifieras mot
    den. Returnerar fälten som sparas på prospektraden plus de bakåt-
    kompatibla `qualified`/`icp_fit`/`disqualifiers` som resten av kedjan
    (eskalering, utkastgrind) redan läser."""
    kand = kandidat or {}
    utslag_per_id: dict[str, dict[str, Any]] = {}
    for b in fynd.get("bedomningar") or []:
        if isinstance(b, dict) and b.get("kriterie_id"):
            utslag_per_id[str(b["kriterie_id"])] = b

    rader: list[dict[str, Any]] = []
    fallt: list[str] = []

    for rad in (_ort_rad(profil, fynd, kand), _storlek_rad(profil, fynd, kand)):
        if rad:
            rader.append(rad)
            if rad["utfall"] == MISS:
                fallt.append(f"{rad['etikett']}: {rad['motivering']}")

    for k in profil.get("kriterier") or []:
        b = utslag_per_id.get(k["id"], {})
        utfall = UTSLAG.get(str(b.get("utslag") or "").casefold(), OKAND)
        belagg = verifierade_belagg(b.get("belagg"), korpus)
        if utfall != OKAND and not belagg:
            utfall = OKAND
            motivering = (str(b.get("resonemang") or "").strip() + " (Belägget kunde inte verifieras.)").strip()
        else:
            motivering = str(b.get("resonemang") or "").strip() or "Inget underlag i källmaterialet."
        rader.append(_rad(k["id"], k["text"], k["vikt"], utfall, motivering, hart=k["krav"] == "maste",
                          belagg=belagg))
        if utfall == MISS and k["krav"] == "maste":
            fallt.append(f"{k['text']}: {motivering}")

    for i, u in enumerate(profil.get("uteslut") or [], start=1):
        b = utslag_per_id.get(f"u{i}", {})
        belagg = verifierade_belagg(b.get("belagg"), korpus)
        # För en uteslutning betyder "ja" att bolaget ÄR det kunden inte vill nå.
        if str(b.get("utslag") or "").casefold() == "ja" and belagg:
            motivering = str(b.get("resonemang") or "").strip() or u["text"]
            rader.append(_rad(f"u{i}", f"Uteslut: {u['text']}", 1, MISS, motivering, hart=True, belagg=belagg))
            fallt.append(f"Uteslutet — {u['text']}: {motivering}")

    if not rader:
        # INV-LEADS-SCORE-001: aldrig en tom motivering — säg ärligt varför.
        rader.append(_rad("underlag", "Kundens profil", 1, OKAND,
                          "Profilen saknar kriterier att bedöma mot. Fyll i Affärskontext och målgrupp.",
                          hart=False))

    viktat = [(r["vikt"], _VARDE.get(r["utfall"], 0.5)) for r in rader if not r["nyckel"].startswith("u")]
    total = round(100 * sum(w * v for w, v in viktat) / sum(w for w, _ in viktat)) if viktat else 50

    maste = [r for r in rader if r["hart"] and not r["nyckel"].startswith("u") and r["nyckel"] not in ("ort", "storlek")]
    if fallt:
        niva = "C"
        total = min(total, TAK_FALLD)
    elif all(r["utfall"] == TRAFF for r in maste) and total >= A_GRANS:
        niva = "A"
    else:
        niva = "B"

    motivering = str(fynd.get("motivering") or fynd.get("qualification_reasoning") or "").strip()
    if not motivering:
        ja = [r["etikett"] for r in rader if r["utfall"] == TRAFF]
        okanda = [r["etikett"] for r in rader if r["utfall"] == OKAND]
        delar = []
        if fallt:
            delar.append("Bortvald: " + "; ".join(fallt[:2]) + ".")
        if ja:
            delar.append("Uppfyller: " + ", ".join(ja) + ".")
        if okanda:
            delar.append("Okänt: " + ", ".join(okanda) + ".")
        motivering = " ".join(delar) or "Källmaterialet räckte inte för någon bedömning."
    elif fallt and niva == "C" and not any(f.split(":")[0] in motivering for f in fallt):
        motivering = f"Bortvald: {fallt[0]}. {motivering}"

    # Textkvalitetslagret: motiveringen är kundtext (INV-LEADS-SCORE-001) —
    # putsa blanksteg och entydiga felstavningar innan den sparas. Kapningen
    # till 1200 görs EFTER putsningen så att gränsen gäller den text som visas.
    from ..textkvalitet import putsa as _putsa_text

    motivering, _ = _putsa_text(motivering)

    return {
        "niva": niva,
        "score_total": int(total),
        "score_breakdown": rader,
        "motivering": motivering[:1200],
        "qualified": niva in ("A", "B"),
        "icp_fit": round(total / 100, 2),
        "disqualifiers": fallt,
    }


def demo() -> None:
    profil = {
        "kommuner": ["Göteborg", "Mölndal"],
        "anstallda_min": 1,
        "anstallda_max": 49,
        "kriterier": [{"id": "k1", "text": "Gammal eller ingen hemsida", "krav": "maste", "vikt": 3}],
        "uteslut": [{"text": "bemanningsföretag"}],
    }
    korpus = "Välkommen till Åbergs. © 2014 Åbergs AB. Besöksadress: Sisjövägen 1, 421 32 Västra Frölunda"
    bra = bedom(profil, {"postnummer": "421 32", "antal_anstallda": 2, "bedomningar": [
        {"kriterie_id": "k1", "utslag": "ja", "resonemang": "Copyright 2014.", "belagg": [{"url": "u", "citat": "© 2014 Åbergs AB"}]}
    ]}, korpus=korpus)
    assert bra["niva"] == "A" and bra["qualified"] and bra["motivering"], bra
    # Påhittat citat: utslaget räknas som okänt, bolaget fälls inte.
    gissat = bedom(profil, {"postnummer": "421 32", "bedomningar": [
        {"kriterie_id": "k1", "utslag": "nej", "resonemang": "Modern sajt.", "belagg": [{"citat": "byggd 2025"}]}
    ]}, korpus=korpus)
    assert gissat["niva"] == "B" and gissat["qualified"], gissat
    stort = bedom(profil, {"antal_anstallda": 700, "bedomningar": []}, korpus=korpus)
    assert stort["niva"] == "C" and stort["score_total"] <= TAK_FALLD and stort["disqualifiers"]
    print("bedomning: ok")


if __name__ == "__main__":
    demo()
