#!/usr/bin/env python3
"""Säkerhetsbevakningen: CERT-SE:s flöde och GitHub Advisory Database mot vår stack.

ISO 27001 A.5.6 (kontakt med intressegrupper). Körs av
.github/workflows/sakerhetsbevakning.yml, som läser utdata och skapar ärendena;
skriptet själv skriver ingenting i GitHub.

Vad skriptet gör:
  1. Läser stacken ur .github/sakerhetsbevakning.json (sökord för CERT-SE,
     ekosystem och paket för GitHub-advisories).
  2. Hämtar CERT-SE:s RSS-flöde och GitHubs globala advisories (GET /advisories,
     filtrerat på ekosystem, paket och publiceringsdatum).
  3. Behåller poster publicerade de senaste --dagar dagarna som nämner ett
     sökord eller berör ett paket.
  4. Tar bort träffar vars nyckel (GHSA-id, CERT-SE-länk) redan står i ett
     ärende (--kanda-nycklar: ärendekropparna, öppna och stängda).
  5. Skriver JSON med träffarna och färdiga ärendetexter (--ut).

Filtrering, dedup och ärendetext är rena funktioner utan nätverk, testade i
tests/test_sakerhetsbevakning.py. Bara standardbiblioteket.

Ingen hemlighet utöver den valfria GITHUB_TOKEN (höjer API-gränsen), och
ingenting ur repots data lämnar körningen: anropen bär bara paketnamn och datum.

Slutkod: 0 om båda källorna kunde läsas, 2 om någon källa föll (utdata skrivs
ändå, med felen i "fel"), 1 vid felaktig konfiguration.
"""

from __future__ import annotations

import argparse
import html
import json
import os
import re
import sys
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

GITHUB_API = "https://api.github.com/advisories"
NYCKELMARKOR = "sakerhetsbevakning-nyckel"
NYCKEL_RE = re.compile(r"<!--\s*" + NYCKELMARKOR + r":\s*(\S+)\s*-->")
TILLATNA_LANKAR = ("https://www.cert.se/", "https://github.com/advisories/")
MAX_TRAFFAR_PER_ARENDE = 15
ANVANDARAGENT = "snajp-sakerhetsbevakning"


@dataclass
class Traff:
    nyckel: str
    kalla: str  # "CERT-SE" eller "GitHub Advisory Database"
    rubrik: str
    lank: str
    publicerad: str  # ISO 8601, UTC
    matchat: list[str] = field(default_factory=list)
    allvarlighet: str = ""
    cve: str = ""
    typ: str = ""
    # Per berört paket: ekosystem, namn, intervall, rättad version, vår version, bedömning.
    paket: list[dict] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Rena hjälpfunktioner
# ---------------------------------------------------------------------------


def tolka_datum(text: str) -> datetime | None:
    """RFC 822 (RSS) eller ISO 8601 (GitHub) till UTC. None om det inte går."""
    text = (text or "").strip()
    if not text:
        return None
    try:
        if "T" in text and text[:4].isdigit():
            dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
        else:
            dt = parsedate_to_datetime(text)
    except (TypeError, ValueError, IndexError):
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def ren_text(text: str, maxlangd: int = 300) -> str:
    """HTML bort, blanksteg ihop, och neutraliserad för ett GitHub-ärende.

    Texten kommer utifrån: inga @-omnämnanden (pingar folk), inga HTML-
    kommentarer (kunde förfalska en nyckelmarkör), inga taggar.
    """
    text = html.unescape(text or "")
    text = re.sub(r"<[^>]*>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    text = text.replace("<", "&lt;").replace(">", "&gt;")
    text = text.replace("@", "@​")
    if len(text) > maxlangd:
        text = text[: maxlangd - 1].rstrip() + "…"
    return text


def saker_lank(lank: str) -> str:
    lank = (lank or "").strip()
    return lank if lank.startswith(TILLATNA_LANKAR) and not re.search(r"[\s<>()\[\]]", lank) else ""


def certse_nyckel(lank: str) -> str:
    """Stabil nyckel för en CERT-SE-post: länken, normaliserad."""
    lank = (lank or "").strip()
    if lank.startswith("http://"):
        lank = "https://" + lank[len("http://"):]
    lank = re.sub(r"^https://cert\.se/", "https://www.cert.se/", lank, flags=re.I)
    return lank.split("#", 1)[0].split("?", 1)[0].rstrip("/")


def kanda_nycklar(text: str) -> set[str]:
    """Nycklarna som redan står i ärenden (markörerna i ärendekropparna)."""
    return set(NYCKEL_RE.findall(text or ""))


def sokord_traff(text: str, sokord: list[str]) -> list[str]:
    """Sökorden som förekommer som egna ord i texten, skiftlägesokänsligt."""
    trafflista = []
    for ord_ in sokord:
        monster = r"(?<![\w.])" + re.escape(ord_) + r"(?![\w])"
        if re.search(monster, text or "", flags=re.IGNORECASE):
            trafflista.append(ord_)
    return trafflista


# --- versioner ---------------------------------------------------------------


def _version(text: str):
    """'16.4.6' / 'v5.0.0-beta.32' till en jämförbar tuple, None om okänd form."""
    m = re.fullmatch(r"v?(\d+(?:\.\d+)*)(?:-([0-9A-Za-z.-]+))?(?:\+[0-9A-Za-z.-]+)?", (text or "").strip())
    if not m:
        return None
    tal = [int(x) for x in m.group(1).split(".")]
    tal += [0] * (3 - len(tal))
    if m.group(2) is None:
        pre = (1,)  # en release sorterar efter alla förhandsversioner
    else:
        delar = []
        for d in m.group(2).split("."):
            delar.append((0, int(d), "") if d.isdigit() else (1, 0, d))
        pre = (0, tuple(delar))
    return (tuple(tal), pre)


def i_intervall(version: str, intervall: str) -> bool | None:
    """Ligger versionen i GitHubs intervall ('>= 16.2.0, <= 16.4.4')?

    None när något inte går att tolka; anroparen säger då "kunde inte avgöras".
    """
    v = _version(version)
    if v is None or not (intervall or "").strip():
        return None
    for villkor in intervall.split(","):
        m = re.fullmatch(r"\s*(>=|<=|>|<|=)?\s*(\S+)\s*", villkor)
        if not m:
            return None
        op, grans = m.group(1) or "=", _version(m.group(2))
        if grans is None:
            return None
        ok = {
            ">=": v >= grans,
            "<=": v <= grans,
            ">": v > grans,
            "<": v < grans,
            "=": v == grans,
        }[op]
        if not ok:
            return False
    return True


def npm_versioner(lockfil_text: str) -> dict[str, str]:
    """Paketnamn till installerad version ur package-lock.json (v2/v3)."""
    try:
        data = json.loads(lockfil_text)
    except ValueError:
        return {}
    ut = {}
    for sokvag, post in (data.get("packages") or {}).items():
        if sokvag.startswith("node_modules/") and "/node_modules/" not in sokvag:
            namn = sokvag[len("node_modules/"):]
            if isinstance(post, dict) and post.get("version"):
                ut[namn] = post["version"]
    return ut


def normalisera_pipnamn(namn: str) -> str:
    return re.sub(r"[-_.]+", "-", namn).lower()


def pip_krav(requirements_text: str) -> dict[str, str]:
    """Paketnamn till kravet i requirements.txt ('>=0.115', '>=2.10,<3')."""
    ut = {}
    for rad in (requirements_text or "").splitlines():
        rad = rad.split("#", 1)[0].split(";", 1)[0].strip()
        m = re.match(r"([A-Za-z0-9][A-Za-z0-9._-]*)(\[[^\]]*\])?\s*(.*)$", rad)
        if m:
            ut[normalisera_pipnamn(m.group(1))] = m.group(3).strip() or "(utan krav)"
    return ut


# --- källorna --------------------------------------------------------------


def tolka_rss(xml_text: str) -> list[dict]:
    """RSS 2.0 till poster: rubrik, länk, beskrivning, publicerad (datetime|None)."""
    rot = ET.fromstring(xml_text)
    poster = []
    for item in rot.iter("item"):
        def falt(namn: str) -> str:
            el = item.find(namn)
            return (el.text or "").strip() if el is not None and el.text else ""

        poster.append(
            {
                "rubrik": falt("title"),
                "lank": falt("link") or falt("guid"),
                "beskrivning": falt("description"),
                "publicerad": tolka_datum(falt("pubDate")),
            }
        )
    return poster


def filtrera_certse(poster: list[dict], sokord: list[str], sedan: datetime) -> list[Traff]:
    traffar = []
    for p in poster:
        if p["publicerad"] is None or p["publicerad"] < sedan:
            continue
        rubrik = ren_text(p["rubrik"], 200)
        beskrivning = ren_text(p["beskrivning"], 2000)
        matchat = sokord_traff(f"{rubrik} {beskrivning}", sokord)
        lank = saker_lank(certse_nyckel(p["lank"]))
        if not matchat or not lank:
            continue
        traffar.append(
            Traff(
                nyckel=lank,
                kalla="CERT-SE",
                rubrik=rubrik,
                lank=lank,
                publicerad=p["publicerad"].strftime("%Y-%m-%dT%H:%M:%SZ"),
                matchat=[f"sökord: {m}" for m in matchat],
            )
        )
    return traffar


def filtrera_advisories(
    advisories: list[dict],
    paket: list[dict],
    sedan: datetime,
    npm: dict[str, str] | None = None,
    pip: dict[str, str] | None = None,
) -> list[Traff]:
    """GitHub-advisories som berör ett paket i listan och publicerats sedan `sedan`.

    API-anropet filtrerar redan på paket och datum; filtreringen görs om här så
    att utdata aldrig bär något annat än stacken, oavsett vad API:t returnerar.
    """
    npm, pip = npm or {}, pip or {}
    # Nyckel till namnet i vår lista: det visade namnet kommer därifrån, inte
    # utifrån (ingen sanering behövs, och @auth/core förblir sökbart).
    bevakade = {(p["ekosystem"], _paketnyckel(p["ekosystem"], p["namn"])): p["namn"] for p in paket}
    traffar = []
    for a in advisories:
        if a.get("withdrawn_at"):
            continue
        publicerad = tolka_datum(a.get("published_at") or "")
        ghsa = a.get("ghsa_id") or ""
        if publicerad is None or publicerad < sedan or not re.fullmatch(r"GHSA(-[0-9a-z]{4}){3}", ghsa):
            continue
        berorda = []
        for s in a.get("vulnerabilities") or []:
            pk = s.get("package") or {}
            eko, namn = pk.get("ecosystem") or "", pk.get("name") or ""
            if (eko, _paketnyckel(eko, namn)) not in bevakade:
                continue
            namn = bevakade[(eko, _paketnyckel(eko, namn))]
            intervall = s.get("vulnerable_version_range") or ""
            if eko == "npm":
                var = npm.get(namn, "")
                utfall = i_intervall(var, intervall) if var else None
                bedomning = {True: "berörd", False: "inte berörd"}.get(utfall, "kunde inte avgöras")
                var_text = f"{var} (package-lock.json)" if var else "okänd"
            elif eko == "pip":
                krav = pip.get(normalisera_pipnamn(namn), "")
                var_text = f"{krav} (requirements.txt, ingen låsfil)" if krav else "transitivt, inte låst i requirements.txt"
                bedomning = "kontrollera installerad version"
            else:
                var_text, bedomning = "okänd", "kunde inte avgöras"
            berorda.append(
                {
                    "ekosystem": eko,
                    "namn": namn,
                    "intervall": ren_text(intervall, 100) or "(anges inte)",
                    "rattad": ren_text(s.get("first_patched_version") or "", 50) or "(ingen ännu)",
                    "var_version": var_text,
                    "bedomning": bedomning,
                }
            )
        if not berorda:
            continue
        traffar.append(
            Traff(
                nyckel=ghsa,
                kalla="GitHub Advisory Database",
                rubrik=ren_text(a.get("summary") or "", 200),
                lank=saker_lank(a.get("html_url") or "") or f"https://github.com/advisories/{ghsa}",
                publicerad=publicerad.strftime("%Y-%m-%dT%H:%M:%SZ"),
                matchat=sorted({f"paket: {b['ekosystem']}/{b['namn']}" for b in berorda}),
                allvarlighet=ren_text(a.get("severity") or "", 20),
                cve=ren_text(a.get("cve_id") or "", 30),
                typ=ren_text(a.get("type") or "", 20),
                paket=berorda,
            )
        )
    return traffar


def _paketnyckel(eko: str, namn: str) -> str:
    return normalisera_pipnamn(namn) if eko == "pip" else namn


def nya_traffar(traffar: list[Traff], kanda: set[str]) -> list[Traff]:
    """Dedup: bort med det som redan har ett ärende, och dubbletter i körningen.

    En advisory som hittas i två anrop slås ihop till en träff.
    """
    ut: dict[str, Traff] = {}
    for t in traffar:
        if t.nyckel in kanda:
            continue
        if t.nyckel in ut:
            forsta = ut[t.nyckel]
            forsta.matchat = sorted(set(forsta.matchat) | set(t.matchat))
            sedda = {(p["ekosystem"], p["namn"]) for p in forsta.paket}
            forsta.paket += [p for p in t.paket if (p["ekosystem"], p["namn"]) not in sedda]
            continue
        ut[t.nyckel] = t
    return sorted(ut.values(), key=lambda t: (t.publicerad, t.nyckel))


# --- ärendena --------------------------------------------------------------


def rendera_traff(t: Traff) -> str:
    rader = [
        f"### {t.rubrik or '(utan rubrik)'}",
        "",
        f"- Källa: {t.kalla}",
        f"- Nyckel: `{t.nyckel}`",
        f"- Länk: {t.lank}",
        f"- Publicerad: {t.publicerad}",
        f"- Matchade: {', '.join(t.matchat)}",
    ]
    if t.allvarlighet:
        rader.append(f"- Allvarlighetsgrad: {t.allvarlighet}")
    if t.cve:
        rader.append(f"- CVE: {t.cve}")
    if t.typ and t.typ != "reviewed":
        rader.append(f"- Typ: {t.typ}")
    if t.paket:
        rader += [
            "",
            "| Paket | Berörda versioner | Första rättade | Vår version | Bedömning |",
            "|---|---|---|---|---|",
        ]
        for p in t.paket:
            rader.append(
                f"| {p['ekosystem']}/{p['namn']} | {p['intervall']} | {p['rattad']} | {p['var_version']} | {p['bedomning']} |"
            )
    rader += ["", f"<!-- {NYCKELMARKOR}: {t.nyckel} -->"]
    return "\n".join(rader)


def bygg_arenden(traffar: list[Traff], korning: str = "", datum: str = "", prov: bool = False) -> list[dict]:
    """Ett ärende per körning (fler om träffarna är många), varje träff med sin nyckel."""
    datum = datum or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    arenden = []
    for i in range(0, len(traffar), MAX_TRAFFAR_PER_ARENDE):
        grupp = traffar[i : i + MAX_TRAFFAR_PER_ARENDE]
        if len(grupp) == 1:
            t = grupp[0]
            titel = f"Säkerhetsbevakning: {t.nyckel if t.kalla != 'CERT-SE' else 'CERT-SE'}: {t.rubrik}"[:200]
        else:
            titel = f"Säkerhetsbevakning: {len(grupp)} nya träffar {datum}"
        if prov:
            titel += " (simulerat prov)"
        huvud = [
            "**Säkerhetsbevakningen har hittat nya publiceringar som berör vår stack.**",
            "",
            "Bedöm varje träff: berörs vi, vilken åtgärd (uppdatera, vänta på rättning, inte relevant), och notera beslutet i en kommentar innan ärendet stängs. Stacken och sökorden står i `.github/sakerhetsbevakning.json`.",
        ]
        if korning:
            huvud += ["", f"Körning: {korning}"]
        if prov:
            huvud += ["", "Det här är ett **simulerat prov** (workflow_dispatch med simulera_traff). Ingen verklig publicering; stäng ärendet."]
        kropp = "\n".join(huvud) + "\n\n" + "\n\n---\n\n".join(rendera_traff(t) for t in grupp) + "\n"
        arenden.append({"titel": titel, "kropp": kropp, "nycklar": [t.nyckel for t in grupp]})
    return arenden


def provtraff(korning_id: str, nu: datetime) -> Traff:
    return Traff(
        nyckel=f"PROV-{korning_id or nu.strftime('%Y%m%d%H%M%S')}",
        kalla="Simulerat prov",
        rubrik="Simulerad träff för att prova ärendekedjan",
        lank="https://github.com/advisories",
        publicerad=nu.strftime("%Y-%m-%dT%H:%M:%SZ"),
        matchat=["simulera_traff"],
    )


# ---------------------------------------------------------------------------
# Nätverk (inte i testerna)
# ---------------------------------------------------------------------------


def _hamta(url: str, headers: dict | None = None) -> tuple[bytes, dict]:
    req = urllib.request.Request(url, headers={"User-Agent": ANVANDARAGENT, **(headers or {})})
    with urllib.request.urlopen(req, timeout=30) as svar:
        return svar.read(), dict(svar.headers)


def hamta_certse(url: str) -> list[dict]:
    data, _ = _hamta(url, {"Accept": "application/rss+xml, application/xml"})
    return tolka_rss(data.decode("utf-8"))


def hamta_advisories(ekosystem: str, paket: list[str], typ: str, sedan: datetime, token: str = "") -> list[dict]:
    headers = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    fraga = urllib.parse.urlencode(
        {
            "ecosystem": ekosystem,
            "affects": ",".join(paket),
            "type": typ,
            "published": ">=" + sedan.strftime("%Y-%m-%d"),
            "per_page": "100",
        }
    )
    url, ut = f"{GITHUB_API}?{fraga}", []
    for _ in range(10):  # högst 1 000 advisories per anrop och typ
        data, svarshuvud = _hamta(url, headers)
        ut += json.loads(data)
        nasta = re.search(r'<([^>]+)>;\s*rel="next"', svarshuvud.get("Link", "") or svarshuvud.get("link", ""))
        if not nasta:
            break
        url = nasta.group(1)
    return ut


# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    rot = Path(__file__).resolve().parents[1]
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--konfig", default=str(rot / ".github" / "sakerhetsbevakning.json"))
    ap.add_argument("--dagar", type=int, default=7, help="publicerat de senaste N dagarna")
    ap.add_argument("--kanda-nycklar", help="fil med befintliga ärendekroppar (nycklarna läses ur markörerna)")
    ap.add_argument("--ut", required=True, help="JSON-fil att skriva träffar och ärenden till")
    ap.add_argument("--korning", default="", help="länk till körningen, skrivs i ärendet")
    ap.add_argument("--simulera-traff", action="store_true", help="lägg till en provträff")
    args = ap.parse_args(argv)

    try:
        konfig = json.loads(Path(args.konfig).read_text(encoding="utf-8"))
        sokord = konfig["certse"]["sokord"]
        paket = konfig["github"]["paket"]
    except (OSError, ValueError, KeyError) as fel:
        print(f"Konfigurationen går inte att läsa: {fel}", file=sys.stderr)
        return 1

    nu = datetime.now(timezone.utc)
    sedan = nu - timedelta(days=args.dagar)
    kanda = kanda_nycklar(Path(args.kanda_nycklar).read_text(encoding="utf-8")) if args.kanda_nycklar else set()

    def las(relativ: str) -> str:
        try:
            return (rot / relativ).read_text(encoding="utf-8")
        except OSError:
            return ""

    kallor = konfig.get("versionskallor", {})
    npm = npm_versioner(las(kallor.get("npm", "package-lock.json")))
    pip = pip_krav(las(kallor.get("pip", "snajp-support/requirements.txt")))

    traffar: list[Traff] = []
    fel: list[str] = []

    certse_url = konfig["certse"].get("flode", "https://www.cert.se/feed/rss.xml")
    try:
        poster = hamta_certse(certse_url)
        traffar += filtrera_certse(poster, sokord, sedan)
        print(f"CERT-SE: {len(poster)} poster i flödet.")
    except Exception as e:  # noqa: BLE001 - en källa som faller ska inte fälla den andra
        fel.append(f"CERT-SE ({certse_url}): {type(e).__name__}: {e}")

    token = os.environ.get("GITHUB_TOKEN", "")
    for eko in sorted({p["ekosystem"] for p in paket}):
        namn = [p["namn"] for p in paket if p["ekosystem"] == eko]
        for typ in konfig["github"].get("typer", ["reviewed"]):
            try:
                adv = hamta_advisories(eko, namn, typ, sedan, token)
                traffar += filtrera_advisories(adv, paket, sedan, npm, pip)
                print(f"GitHub {eko}/{typ}: {len(adv)} advisories sedan {sedan:%Y-%m-%d}.")
            except Exception as e:  # noqa: BLE001
                fel.append(f"GitHub Advisory Database ({eko}, {typ}): {type(e).__name__}: {e}")

    nya = nya_traffar(traffar, kanda)
    print(f"{len(traffar)} träffar, {len(nya)} nya efter dedup mot {len(kanda)} kända nycklar.")
    if args.simulera_traff:
        nya.append(provtraff(os.environ.get("GITHUB_RUN_ID", ""), nu))
    arenden = bygg_arenden(nya, args.korning, nu.strftime("%Y-%m-%d"), prov=args.simulera_traff)

    Path(args.ut).write_text(
        json.dumps({"traffar": [asdict(t) for t in nya], "arenden": arenden, "fel": fel}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"{len(arenden)} ärenden att skapa{' (med provträff)' if args.simulera_traff else ''}.")
    for f in fel:
        print(f"::error::{f}")
    return 2 if fel else 0


if __name__ == "__main__":
    sys.exit(main())
