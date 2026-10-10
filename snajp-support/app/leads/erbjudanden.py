"""Erbjudandena i Iris kalla mejl: katalog, kundens val, tilldelning och mätning.

Antons beställning 2026-10-10: A/B-testa de erbjudanden kunden väljer, mät
resultaten löpande och kunna byta erbjudande enkelt.

## Var delarna bor

- **Katalogen** är `agent-core/prompts/leads-erbjudanden.md`: ett `## nyckel`-
  avsnitt per erbjudande, och de gemensamma reglerna överst. Läses en gång
  per process, samma mönster som `leads_systemprompt.skrivstil`.
- **Kundens val** står i leads-agentens inställningar
  (`agent_configs.settings["erbjudanden"]`, samma ställe som `signatur`):
  `{"aktiva": [{"nyckel", "vikt"}], "villkor": {nyckel: text}}`.
- **Tilldelningen** sker per prospekt i utkaststeget (`for_trad`), och valet
  sparas som en `offers`-rad per kund och nyckel plus `outreach_threads.offer_id`
  (migration 010, tabellerna fanns men användes inte).
- **Mätningen** räknas ur trådarnas verkliga läge (`storage.erbjudande_utfall`)
  och sammanställs här (`sammanstall`).

## Invarianterna

- Villkoren är kundens text och det enda mejlet får lova om erbjudandet.
  Katalogen innehåller inga villkor. Villkoren går ordagrant in i ärendet
  (användarpositionen, INV-SEC-009), aldrig i systemprompten, och in i
  faktagrindens underlag så att deras siffror släpps igenom men inga andra.
- Ett erbjudande är bara valbart med ifyllda villkor.
- Inget valbart erbjudande = exakt dagens beteende: inget block, ingen rad.
"""

from __future__ import annotations

import hashlib
import logging
import math
import re
from dataclasses import dataclass
from functools import lru_cache
from typing import Any

from ..agentcore.registry import AGENT_CORE_ROOT

logger = logging.getLogger("snajp-support.leads.erbjudanden")

KATALOG_FIL = AGENT_CORE_ROOT / "prompts" / "leads-erbjudanden.md"

#: Kundens villkor per erbjudande, i tecken. Längre än så är det ett avtal,
#: inte ett erbjudande i ett kallt mejl.
VILLKOR_MAX = 600
VIKT_MAX = 10
#: Skickade mejl per arm innan någon arm får kallas ledande.
MIN_SKICKADE = 30
#: Signifikansnivån för tvåproportionstestet.
ALFA = 0.05

_OM_FILEN = re.compile(r"^> \*\*Om filen:\*\*.*\n+", re.MULTILINE)
#: Raderna i ett avsnitt som är katalogens metadata, inte skrivregler.
_METARAD = re.compile(r"^\*\*(?:Namn|Kräver villkor):\*\*.*\n?", re.MULTILINE)
_NAMN = re.compile(r"^\*\*Namn:\*\*\s*(.+)$", re.MULTILINE)


@dataclass(frozen=True)
class Erbjudande:
    nyckel: str
    namn: str
    #: Avsnittets skrivregler (hävstång, hur mejlet bär det, uppmaning, undvik).
    regler: str


@lru_cache(maxsize=1)
def _las() -> tuple[str, dict[str, Erbjudande]]:
    text = _OM_FILEN.sub("", KATALOG_FIL.read_text(encoding="utf-8"))
    delar = re.split(r"(?m)^## ", text)
    # Huvudet: titeln bort, de gemensamma reglerna kvar.
    gemensamt = re.sub(r"^# .*\n+", "", delar[0]).strip()
    katalog: dict[str, Erbjudande] = {}
    for del_ in delar[1:]:
        nyckel, _, kropp = del_.partition("\n")
        namn = _NAMN.search(kropp)
        katalog[nyckel.strip()] = Erbjudande(
            nyckel=nyckel.strip(),
            namn=namn.group(1).strip() if namn else nyckel.strip(),
            regler=_METARAD.sub("", kropp).strip(),
        )
    return gemensamt, katalog


def katalog() -> dict[str, Erbjudande]:
    """Nyckel → erbjudande, i filens ordning."""
    return _las()[1]


def gemensamt() -> str:
    """De gemensamma reglerna som följer med varje erbjudande."""
    return _las()[0]


# -- Kundens val ----------------------------------------------------------


def normalisera(raw: Any) -> dict[str, Any]:
    """Kundens sparade val, tolerant läst: okända nycklar faller bort, vikten
    hålls inom 0–10 och villkoren strippas. Skrivvägen (`validera`) är strikt;
    läsvägen ska aldrig fälla en körning för ett gammalt värde."""
    raw = raw if isinstance(raw, dict) else {}
    kat = katalog()
    villkor = {
        k: str(v).strip()[:VILLKOR_MAX]
        for k, v in (raw.get("villkor") or {}).items()
        if k in kat and isinstance(v, str) and v.strip()
    }
    aktiva: list[dict[str, Any]] = []
    for rad in raw.get("aktiva") or []:
        if not isinstance(rad, dict) or rad.get("nyckel") not in kat:
            continue
        if any(a["nyckel"] == rad["nyckel"] for a in aktiva):
            continue
        try:
            vikt = int(rad.get("vikt", 1))
        except (TypeError, ValueError):
            vikt = 1
        aktiva.append({"nyckel": rad["nyckel"], "vikt": min(max(vikt, 0), VIKT_MAX)})
    return {"aktiva": aktiva, "villkor": villkor}


def validera(aktiva: list[dict[str, Any]], villkor: dict[str, str]) -> dict[str, Any]:
    """Skrivvägen: kastar ValueError med ett svenskt besked. Typer och
    gränser (vikt 0–10, villkorslängd) prövas redan av API-schemat."""
    kat = katalog()
    for nyckel in [a["nyckel"] for a in aktiva] + list(villkor):
        if nyckel not in kat:
            raise ValueError(f"Okänt erbjudande: {nyckel}.")
    nycklar = [a["nyckel"] for a in aktiva]
    if len(nycklar) != len(set(nycklar)):
        raise ValueError("Ett erbjudande står två gånger bland de aktiva.")
    for a in aktiva:
        if not str(villkor.get(a["nyckel"]) or "").strip():
            raise ValueError(
                f"Fyll i villkoren för {kat[a['nyckel']].namn} innan erbjudandet slås på."
            )
    return normalisera({"aktiva": aktiva, "villkor": villkor})


def valbara(val: dict[str, Any]) -> list[tuple[str, int]]:
    """De aktiva erbjudandena som får användas: i katalogen, vikt över noll och
    med ifyllda villkor. Katalogens ordning, så att tilldelningen inte beror på
    i vilken ordning kunden råkade slå på dem."""
    vikter = {a["nyckel"]: a["vikt"] for a in val.get("aktiva") or []}
    villkor = val.get("villkor") or {}
    return [
        (nyckel, vikter[nyckel])
        for nyckel in katalog()
        if vikter.get(nyckel, 0) > 0 and str(villkor.get(nyckel) or "").strip()
    ]


def tilldela(tenant_id: str, prospect_id: str, armar: list[tuple[str, int]]) -> str | None:
    """Viktad, deterministisk tilldelning: samma prospekt får samma erbjudande
    så länge de aktiva och vikterna är desamma. En hash och inte slumpen, så
    att ett omskrivet utkast inte byter arm och förstör mätningen."""
    total = sum(vikt for _, vikt in armar)
    if total <= 0:
        return None
    digest = hashlib.sha256(f"{tenant_id}:{prospect_id}".encode("utf-8")).digest()
    punkt = int.from_bytes(digest[:8], "big") % total
    for nyckel, vikt in armar:
        if punkt < vikt:
            return nyckel
        punkt -= vikt
    return None  # nås inte: punkt < total


def block(nyckel: str, villkor: str) -> str:
    """Promptblocket för utkaststeget och humanizern. Kundens villkor står
    ordagrant under sin egen rubrik, som katalogens gemensamma regler pekar på."""
    erbjudande = katalog()[nyckel]
    return (
        "## Erbjudandet i det här mejlet\n"
        "Kunden har valt det här erbjudandet för mejlet. Det bär stycke 3 och 4 i "
        "skrivstilen och går före vinkeln under \"Erbjudandet som styr vinkeln\". "
        "Skriv det i skrivstilen, med villkoren nedan som det enda mejlet lovar.\n"
        # Provkörningen 2026-10-10 (scripts/prova_erbjudanden.py): katalogens
        # exempel på uppmaningar gick ordagrant in i mejlen, samma fråga i
        # upp till elva av tolv, och villkor skrivna i ni-form blandade
        # tilltalet i mejl till en namngiven person.
        "- Citaten nedan visar formen, aldrig orden. Skriv uppmaningen med egna "
        "ord, knuten till just det här bolagets situation.\n"
        "- Återge villkorens innehåll exakt, varken mer eller mindre, men i mejlets "
        "tilltal (du eller ni) och i hela meningar.\n"
        "- Lägg erbjudandet i en egen mening efter meningen om vad tjänsten gör åt dem, "
        "och håll båda under 20 ord.\n\n"
        f"{gemensamt()}\n\n"
        f"### {erbjudande.namn}\n{erbjudande.regler}\n\n"
        f"### Villkor för erbjudandet\n{villkor.strip()}"
    )


@dataclass(frozen=True)
class Valt:
    nyckel: str
    villkor: str

    def block(self) -> str:
        return block(self.nyckel, self.villkor)


async def for_trad(storage, tenant_id: str, thread: dict[str, Any]) -> Valt | None:
    """Erbjudandet för trådens nästa utkast, eller None (dagens beteende).

    Sparar valet (offers-rad + outreach_threads.offer_id). Går sparandet fel
    skrivs utkastet utan erbjudande: ett mejl med ett erbjudande som inte
    räknas hade gjort mätningen tyst fel, och mätningen är skälet till att
    erbjudandet väljs här."""
    if not thread.get("id"):
        return None
    installningar = await storage.get_agent_settings(tenant_id, agent_type="leads")
    val = normalisera(installningar.get("erbjudanden"))
    nyckel = tilldela(tenant_id, str(thread.get("prospect_id") or thread["id"]), valbara(val))
    if not nyckel:
        return None
    try:
        await storage.tilldela_erbjudande(tenant_id, thread["id"], nyckel=nyckel)
    except Exception:  # noqa: BLE001 — se docstringen
        logger.exception("Kunde inte spara erbjudandet för tråd %s; utkastet skrivs utan.", thread["id"])
        return None
    return Valt(nyckel=nyckel, villkor=val["villkor"][nyckel])


# -- Mätningen ------------------------------------------------------------


def p_varde(x1: int, n1: int, x2: int, n2: int) -> float:
    """Tvåsidigt p-värde för tvåproportions z-testet (poolad varians)."""
    if n1 <= 0 or n2 <= 0:
        return 1.0
    pool = (x1 + x2) / (n1 + n2)
    se = math.sqrt(pool * (1 - pool) * (1 / n1 + 1 / n2))
    if se == 0:
        return 1.0
    z = (x1 / n1 - x2 / n2) / se
    return math.erfc(abs(z) / math.sqrt(2))


def sammanstall(rader: list[dict[str, Any]]) -> dict[str, Any]:
    """Utfallet per erbjudande ur `storage.erbjudande_utfall`, med andelar och
    en försiktig ledare.

    Ledaren avgörs på positiva svar per skickat mejl: det är det kunden vill
    ha mer av, och svar räknar även nej. En arm kallas ledande först när minst
    två armar har `MIN_SKICKADE` skickade och skillnaden mot den näst bästa
    håller i ett tvåproportions z-test (p < `ALFA`). Annars är det för tidigt
    att säga, för alla."""
    per = {str(r.get("nyckel")): r for r in rader}
    armar: list[dict[str, Any]] = []
    for nyckel, erbjudande in katalog().items():
        r = per.get(nyckel) or {}
        arm = {
            "nyckel": nyckel,
            "namn": erbjudande.namn,
            **{f: int(r.get(f) or 0) for f in ("utkast", "skickade", "svar", "positiva", "moten")},
        }
        n = arm["skickade"]
        arm["svarsfrekvens"] = round(arm["svar"] / n, 4) if n else None
        arm["positiv_andel"] = round(arm["positiva"] / n, 4) if n else None
        armar.append(arm)

    mogna = sorted(
        (a for a in armar if a["skickade"] >= MIN_SKICKADE),
        key=lambda a: a["positiva"] / a["skickade"],
        reverse=True,
    )
    ledare, p = None, None
    if len(mogna) >= 2:
        bast, tvaa = mogna[0], mogna[1]
        p = p_varde(bast["positiva"], bast["skickade"], tvaa["positiva"], tvaa["skickade"])
        if p < ALFA and bast["positiva"] / bast["skickade"] > tvaa["positiva"] / tvaa["skickade"]:
            ledare = bast["nyckel"]
    for arm in armar:
        arm["lage"] = "leder" if arm["nyckel"] == ledare else "for_tidigt"
    return {
        "armar": armar,
        "ledare": ledare,
        "p_varde": None if p is None else round(p, 4),
        "min_skickade": MIN_SKICKADE,
    }
