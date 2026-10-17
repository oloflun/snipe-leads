"""Kundtjänst › Översikt — talen bakom supportens översiktsflik.

Sebbes beställning 2026-10-07: Leads-översiktens layout, anpassad för
support. Frontenden är `components/snajp/SupportOversikt.tsx`.

## Var talen kommer ifrån

Allt räknas ur supportmejlen (`ss_emails`), deras senaste klassning och
beslutsloggen — inte ur `ss_tickets`, som `weekly_analytics` använder. Det
är mejlen kunden ser i Ärenden, och det är dem översikten ska stämma med.

* **Hur ärendet besvarades** följer mejlets status: `auto_sent` är agentens
  eget svar, `sent` är ett utkast någon godkänt, `escalated`, `taken_over`
  och `rejected` har gått till en människa, och resten väntar.
* **Svarstiden** är tiden från `received_at` till första `auto_sent` eller
  `approved_and_sent` i beslutsloggen. Ett mejl utan svar har ingen svarstid
  och räknas inte in i medianen; det syns i stället som väntande.
* **KB-träff** är andelen klassade mejl vars klassning hittade minst en
  källa i kunskapsbasen.
* **Kunskapsbasens luckor** är agentens öppna KB-förslag (`agent_suggestions`,
  kind `kb_article`, status `ny`), de som Lärande-vyn låter kunden godkänna.

Perioden är rullande: de senaste 28 dygnen mot de 28 före. Veckoserien är
kalenderveckor (måndag, UTC), samma som `weekly_analytics`.

Aggregeringen bor här och inte i lagringen, så att Postgres och
MemoryStorage bara levererar rader och inte kan räkna olika.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from statistics import median
from typing import Any

PERIOD_DYGN = 28
VECKOR = 12

AUTO = ("auto_sent",)
GODKANT = ("sent",)
MANNISKA = ("escalated", "taken_over", "rejected")

#: Svarstidshinkarna i minuter: (id, övre gräns). Sista hinken saknar tak.
HINKAR: tuple[tuple[str, float], ...] = (
    ("15m", 15),
    ("1h", 60),
    ("4h", 240),
    ("24h", 1440),
    ("mer", float("inf")),
)


def _tid(iso: str | None) -> datetime | None:
    if not iso:
        return None
    try:
        t = datetime.fromisoformat(iso)
    except ValueError:
        return None
    return t if t.tzinfo else t.replace(tzinfo=timezone.utc)


def _veckostart(t: datetime) -> datetime:
    t = t.astimezone(timezone.utc)
    return (t - timedelta(days=t.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)


def _svarstid(m: dict[str, Any]) -> float | None:
    mottaget, svar = _tid(m.get("received_at")), _tid(m.get("forsta_svar"))
    if not mottaget or not svar:
        return None
    return max(0.0, (svar - mottaget).total_seconds() / 60)


def _median(tal: list[float]) -> int | None:
    return round(median(tal)) if tal else None


def _period(mejl: list[dict[str, Any]]) -> dict[str, Any]:
    tider = [t for t in (_svarstid(m) for m in mejl) if t is not None]
    klassade = [m for m in mejl if m.get("kb_traffar") is not None]
    status = [m["status"] for m in mejl]
    return {
        "inkomna": len(mejl),
        "auto": sum(1 for s in status if s in AUTO),
        "godkant": sum(1 for s in status if s in GODKANT),
        "manniska": sum(1 for s in status if s in MANNISKA),
        "vantar": sum(1 for s in status if s not in AUTO + GODKANT + MANNISKA),
        "svarstid_median": _median(tider),
        "inom_timme": (sum(1 for t in tider if t <= 60) / len(tider)) if tider else None,
        "kb_traff": (sum(1 for m in klassade if m["kb_traffar"] > 0) / len(klassade)) if klassade else None,
    }


def underlagets_start(nu: datetime) -> datetime:
    """Tidigaste mottagningstid översikten behöver: tolv kalenderveckor bakåt,
    vilket alltid täcker de två rullande perioderna (56 dygn)."""
    return min(_veckostart(nu) - timedelta(weeks=VECKOR - 1), nu - timedelta(days=2 * PERIOD_DYGN))


def bygg_oversikt(
    underlag: dict[str, Any],
    kb_forslag: list[dict[str, Any]],
    *,
    nu: datetime | None = None,
) -> dict[str, Any]:
    nu = nu or datetime.now(timezone.utc)
    mejl = underlag.get("mejl", [])
    for m in mejl:
        m["_mottaget"] = _tid(m.get("received_at"))
    mejl = [m for m in mejl if m["_mottaget"] is not None]

    grans_nu = nu - timedelta(days=PERIOD_DYGN)
    grans_forra = nu - timedelta(days=2 * PERIOD_DYGN)
    i_perioden = [m for m in mejl if m["_mottaget"] >= grans_nu]
    forra = [m for m in mejl if grans_forra <= m["_mottaget"] < grans_nu]

    # Veckoserien: kalendern, inte raderna. En tyst vecka är en nollrad.
    denna = _veckostart(nu)
    veckor = []
    for i in range(VECKOR - 1, -1, -1):
        start = denna - timedelta(weeks=i)
        rader = [m for m in mejl if _veckostart(m["_mottaget"]) == start]
        tider = [t for t in (_svarstid(m) for m in rader) if t is not None]
        veckor.append(
            {
                "week": f"v{start.isocalendar().week}",
                "start": start.isoformat(),
                "inkomna": len(rader),
                "besvarade": sum(1 for m in rader if m["status"] in AUTO + GODKANT),
                "eskalerade": sum(1 for m in rader if m["status"] in MANNISKA),
                "svarstid_median": _median(tider),
            }
        )

    kategorier: dict[str, dict[str, Any]] = {}
    for m in i_perioden:
        nyckel = m.get("category") or "okand"
        rad = kategorier.setdefault(nyckel, {"id": nyckel, "antal": 0, "eskalerade": 0})
        rad["antal"] += 1
        if m["status"] in MANNISKA:
            rad["eskalerade"] += 1

    hinkar = {h: 0 for h, _ in HINKAR}
    for t in (_svarstid(m) for m in i_perioden):
        if t is None:
            continue
        hinkar[next(h for h, tak in HINKAR if t <= tak)] += 1

    vantande = [m for m in mejl if m["status"] == "awaiting_approval"]
    aldsta = min((m["_mottaget"] for m in vantande), default=None)

    luckor = [
        r
        for r in kb_forslag
        if r.get("agent_type") == "support" and r.get("kind") == "kb_article" and r.get("status") == "ny"
    ]

    korningar = underlag.get("korningar") or {}
    return {
        "period_dygn": PERIOD_DYGN,
        "veckor": veckor,
        "nu": _period(i_perioden),
        "forra": _period(forra),
        "kategorier": sorted(kategorier.values(), key=lambda r: r["antal"], reverse=True),
        "svarstider": [{"id": h, "antal": hinkar[h]} for h, _ in HINKAR],
        "vantande": {"antal": len(vantande), "aldsta": aldsta.isoformat() if aldsta else None},
        "kb_luckor": {
            "antal": len(luckor),
            "rader": [
                {
                    "id": str(r["id"]),
                    "titel": r.get("title")
                    or (r["content"].get("title") if isinstance(r.get("content"), dict) else None)
                    or "",
                    "created_at": str(r.get("created_at") or ""),
                }
                for r in luckor[:5]
            ],
        },
        "drift": {
            "korningar": int(korningar.get("antal") or 0),
            "tokens_in": int(korningar.get("tokens_in") or 0),
            "tokens_out": int(korningar.get("tokens_out") or 0),
            "cache": int(korningar.get("cache") or 0),
            "modell": korningar.get("modell"),
            "kb_artiklar": int(underlag.get("kb_artiklar") or 0),
        },
    }
