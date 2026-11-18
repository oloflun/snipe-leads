#!/usr/bin/env python3
"""Konfigurationsbaslinjen för Railway-projektet brave-passion (ISO 27001 A.8.9).

    python scripts/railway_baslinje.py --jamfor   # avvikelser mot baslinjefilen, exit 1 vid avvikelse
    python scripts/railway_baslinje.py --skriv    # skriv om baslinjefilen med läget just nu

## Vad baslinjen är

`docs/compliance/railway-baslinje.json` är det godkända läget för projektets
båda miljöer (main, development) och alla tjänster: källa (repo och den gren
deploy-triggern pekar på), byggare och Dockerfile, start- och byggkommando,
rotkatalog, region, repliker, hälsokontroll, omstartspolicy, publika domäner,
TCP-proxy på/av, volymer, cron, sleep och VARIABELNAMNEN. Värden står bara för
variabler på en uttrycklig vitlista (`VITLISTA_*` nedan) och bara när värdet har
en ofarlig form; allt annat redovisas som enbart ett namn i `variabler`. Ett
namn som inte står på vitlistan är en hemlighet. Ingen hash av hemligheter
heller, så en ändrad hemlighet med oförändrat namn syns inte i jämförelsen.

## När den uppdateras

Före en avsiktlig ändring i Railway: kör `--jamfor` och se att läget stämmer
med baslinjen. Efter ändringen: kör `--jamfor` igen, granska att avvikelserna
är exakt de avsedda, kör `--skriv` och commita filen med ett meddelande som
säger vad som ändrades och varför. En avvikelse som ingen kan förklara är en
oavsiktlig ändring och ska rättas eller beslutas, inte skrivas in i baslinjen.

## Vad som fortfarande saknas

Railway loggar inte ändringar av variabler eller inställningar. Någon
ändringslogg för Railway finns alltså inte; det som finns är den här baslinjen
och git-historiken för baslinjefilen. En ändring som görs och återställs mellan
två jämförelser lämnar inga spår.

## Gränser

Enbart läsning mot Railways GraphQL-API: inga mutationer. Token läses ur
miljövariabeln RAILWAY_TOKEN, `.env.deploy` i repots rot eller
`~/.railway/config.json` (Railway-CLI:ts inloggning) och skrivs aldrig ut.
Variabelvärden filtreras i `maskera_variabler` direkt när svaret kommit, innan
något skrivs till terminal eller fil. Jämförelsen och maskeringen är rena
funktioner (tests/test_railway_baslinje.py).
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request
from collections.abc import Callable, Mapping
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

REPO_ROOT = Path(__file__).resolve().parents[1]
BASLINJEFIL = REPO_ROOT / "docs" / "compliance" / "railway-baslinje.json"

#: Railway-projektet brave-passion (samma id som railway_region.py och DEPLOY.md).
PROJECT_ID = "b4ec4f98-2d00-4410-bfae-12fb69652d0b"
PROJEKTNAMN = "brave-passion"
MILJOER = ("main", "development")

ENDPOINT = "https://backboard.railway.com/graphql/v2"
USER_AGENT = "snajp-railway-client/1.0"  # utan den svarar Cloudflare 403 (se railway.py)

# --------------------------------------------------------------------------
# Maskering av variabler. Allt här är rena funktioner.
# --------------------------------------------------------------------------

#: Namn som aldrig får visa ett värde, även om de skulle matcha en vitlista.
_ALDRIG = re.compile(r"KEY|SECRET|TOKEN|PASS|LOSEN|NYCKEL|PRIVATE_KEY|CREDENTIAL|JSON|_DSN|AUTH_", re.I)

#: Lägen och leverantörsnamn: värdet ska vara ett kort gemener-ord.
VITLISTA_ORD = frozenset({
    "LLM_PROVIDER", "MODEL", "EMAIL_PROVIDER", "NODE_ENV",
    "RAILWAY_ENVIRONMENT_NAME", "RAILWAY_ENVIRONMENT", "RAILWAY_SERVICE_NAME", "RAILWAY_PROJECT_NAME",
    "INKORG_JEV", "IRIS_JEV", "LEADS_PIPELINE", "LEADS_MERINFO", "LEADS_REGISTER", "SEMANTIC_CACHE",
})
#: Mönster för modellnamn (t.ex. GEMINI_MODEL): samma krav som VITLISTA_ORD.
VITLISTA_ORD_MONSTER = re.compile(r"^[A-Z0-9_]*_MODEL$")
_ORD = re.compile(r"^[a-z][a-z0-9._-]{0,47}$")

#: Av/på-flaggor: värdet visas bara om det är ett av de booleska orden.
VITLISTA_FLAGGOR = frozenset({
    "GALLRING_AKTIV", "SYNK_APPLY", "MIGRERA_APPLY", "WEBBPOOL_FORDELNING",
})
VITLISTA_FLAGGOR_MONSTER = re.compile(r"^WEBBPOOL_[A-Z_]+$")
_BOOL = frozenset({"true", "false", "0", "1", "on", "off", "yes", "no", "pa", "på", "av", "shadow"})

#: Talvärden (intervall, budgetar, trösklar).
VITLISTA_TAL = frozenset({
    "PORT", "INBOX_POLL_SECONDS", "LEADS_WORKERS",
    "AUTO_SEND_MIN_CONFIDENCE", "WEBBPOOL_DAGSTAK", "SSL_CERT_DAYS",
})
_TAL = re.compile(r"^-?\d{1,12}(\.\d{1,6})?$")

#: Publika adresser: http(s)-URL utan användare/lösenord, utan query och fragment.
VITLISTA_URL = frozenset({
    "SITE_URL", "NEXT_PUBLIC_SITE_URL", "PUBLIC_BASE_URL", "SNAJP_SUPPORT_URL",
    "SUPPORT_EXTERN_URL", "FLYTT_MAL_URL", "SNAJP_SUPPORT_INTERNAL_URL",
})
_URL = re.compile(r"^https?://[A-Za-z0-9.-]+(:\d{1,5})?(/[A-Za-z0-9._~/-]*)?$")

#: Värdnamn som Railway själv sätter.
VITLISTA_VARD = frozenset({"RAILWAY_PUBLIC_DOMAIN", "RAILWAY_PRIVATE_DOMAIN", "RAILWAY_STATIC_URL"})
VITLISTA_VARD_MONSTER = re.compile(r"^RAILWAY_SERVICE_[A-Z0-9_]+_URL$")
_VARD = re.compile(r"^[A-Za-z0-9.-]{1,253}$")


def synligt_varde(namn: str, varde: Any) -> str | None:
    """Värdet som får sparas för variabeln, eller None (= bara "satt").

    Två grindar: namnet måste stå på en vitlista OCH värdet måste ha den form
    vitlistan lovar. En vitlistad flagga som plötsligt bär en adress eller en
    nyckel visas alltså inte.
    """
    if not isinstance(varde, str):
        return None
    if _ALDRIG.search(namn):
        return None
    v = varde.strip()
    if "@" in v:  # e-post eller user@host i en URL: aldrig
        return None
    if namn in VITLISTA_ORD or VITLISTA_ORD_MONSTER.match(namn):
        return v if _ORD.match(v) else None
    if namn in VITLISTA_FLAGGOR or VITLISTA_FLAGGOR_MONSTER.match(namn):
        return v if v.lower() in _BOOL else None
    if namn in VITLISTA_TAL:
        return v if _TAL.match(v) else None
    if namn in VITLISTA_URL:
        return v if _URL.match(v) else None
    if namn in VITLISTA_VARD or VITLISTA_VARD_MONSTER.match(namn):
        return v if _VARD.match(v) else None
    return None


def maskera_variabler(variabler: Mapping[str, Any]) -> dict[str, Any]:
    """{namn: värde} -> {"variabler": [namn...], "varden": {namn: vitlistat värde}}."""
    namn = sorted(variabler)
    varden = {}
    for n in namn:
        s = synligt_varde(n, variabler[n])
        if s is not None:
            varden[n] = s
    return {"variabler": namn, "varden": varden}


_URL_MED_ANVANDARE = re.compile(r"[A-Za-z][A-Za-z0-9+.-]*://[^\s/@]*@[^\s]*")
_TILLDELNING = re.compile(r"(KEY|SECRET|TOKEN|PASS|LOSEN|NYCKEL)[A-Z_]*\s*=", re.I)


def rensa_text(varde: Any) -> Any:
    """Fritext ur inställningarna (kommandon, image). URL med inloggning maskeras
    helt; en text som tilldelar något som liknar en hemlighet ersätts helt."""
    if isinstance(varde, list):
        return [rensa_text(x) for x in varde]
    if not isinstance(varde, str):
        return varde
    if _TILLDELNING.search(varde):
        return "<maskerat: möjlig hemlighet>"
    return _URL_MED_ANVANDARE.sub("<maskerad url>", varde)


# --------------------------------------------------------------------------
# Hämtning (nätverk). Svaren normaliseras och maskeras innan de lämnar funktionen.
# --------------------------------------------------------------------------

PROJEKTFRAGA = """
query($id: String!) {
  project(id: $id) {
    name
    environments { edges { node {
      id name
      config(decryptVariables: false)
      deploymentTriggers { edges { node { serviceId repository branch provider checkSuites } } }
      volumeInstances { edges { node { serviceId mountPath deletedAt volume { name } } } }
    } } }
    services { edges { node { id name
      serviceInstances { edges { node {
        environmentId deletedAt
        source { repo image }
        builder dockerfilePath railwayConfigFile buildCommand startCommand preDeployCommand
        rootDirectory watchPatterns region numReplicas
        healthcheckPath healthcheckTimeout restartPolicyType restartPolicyMaxRetries
        cronSchedule sleepApplication drainingSeconds overlapSeconds
        domains { serviceDomains { domain } customDomains { domain } }
      } } }
    } } }
  }
}
"""

INSTANSFRAGA = """
query($p: String!, $e: String!, $s: String!) {
  variables(projectId: $p, environmentId: $e, serviceId: $s)
  tcpProxies(environmentId: $e, serviceId: $s) { applicationPort deletedAt }
}
"""


def _token() -> str:
    """RAILWAY_TOKEN, sedan .env.deploy, sedan Railway-CLI:ts inloggning. Skrivs aldrig ut."""
    tok = os.environ.get("RAILWAY_TOKEN", "").strip()
    if tok:
        return tok
    env = REPO_ROOT / ".env.deploy"
    if env.exists():
        for rad in env.read_text(encoding="utf-8").splitlines():
            rad = rad.strip()
            if rad.startswith("RAILWAY_TOKEN="):
                tok = rad.split("=", 1)[1].strip().strip('"').strip("'")
                if tok:
                    return tok
    konfig = Path.home() / ".railway" / "config.json"
    if konfig.exists():
        try:
            anvandare = json.loads(konfig.read_text(encoding="utf-8")).get("user") or {}
        except (OSError, ValueError):
            anvandare = {}
        tok = anvandare.get("token") or anvandare.get("accessToken") or ""
        if tok:
            return tok
    sys.exit("Ingen Railway-token: sätt RAILWAY_TOKEN, lägg den i .env.deploy eller logga in med `railway login`.")


def gql(fraga: str, variabler: dict) -> dict:
    """Ett läsande GraphQL-anrop. Felutskriften bär bara status och felmeddelanden."""
    if re.search(r"^\s*mutation\b", fraga):
        raise ValueError("railway_baslinje gör inga mutationer")
    req = urllib.request.Request(
        ENDPOINT,
        data=json.dumps({"query": fraga, "variables": variabler}).encode(),
        headers={
            "Authorization": f"Bearer {_token()}",
            "Content-Type": "application/json",
            "User-Agent": USER_AGENT,
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=90) as resp:
            svar = json.load(resp)
    except urllib.error.HTTPError as exc:
        sys.exit(f"Railway svarade HTTP {exc.code}; ingen baslinje hämtad.")
    except urllib.error.URLError as exc:
        sys.exit(f"Railway gick inte att nå ({exc.reason}); ingen baslinje hämtad.")
    if svar.get("errors"):
        meddelanden = "; ".join(str(e.get("message", "?"))[:200] for e in svar["errors"])
        sys.exit(f"Railway avvisade frågan: {meddelanden}")
    return svar["data"]


def _kanter(conn: Any) -> list[dict]:
    return [k["node"] for k in ((conn or {}).get("edges") or [])]


def regioner_ur_konfig(konfig: Any, service_id: str) -> dict[str, Any] | None:
    """{region: repliker} ur miljöns konfig (deploy.multiRegionConfig). Bara den
    sökvägen läses; resten av konfigen (där variablerna också ligger) lämnas orörd."""
    try:
        mrc = konfig["services"][service_id]["deploy"]["multiRegionConfig"]
    except (KeyError, TypeError):
        return None
    if not isinstance(mrc, dict):
        return None
    ut: dict[str, Any] = {}
    for region, inst in mrc.items():
        if isinstance(region, str) and re.fullmatch(r"[a-z0-9-]{1,40}", region):
            antal = inst.get("numReplicas") if isinstance(inst, dict) else None
            ut[region] = antal if isinstance(antal, int) else None
    return ut


def normalisera_instans(instans: Mapping[str, Any], triggers: list[dict], volymer: list[dict],
                        tcp: list[dict], regioner: dict[str, Any] | None = None) -> dict[str, Any]:
    """Inställningarna för en tjänst i en miljö, sorterade och rensade.

    Regionen och replikerna står i miljöns multiRegionConfig; instansens egna
    fält region/numReplicas är oftast tomma hos Railway och används bara som
    reserv.
    """
    if regioner is None and instans.get("region"):
        regioner = {instans["region"]: instans.get("numReplicas")}
    kalla = instans.get("source") or {}
    domaner = instans.get("domains") or {}
    return {
        "kalla": {"repo": kalla.get("repo"), "image": rensa_text(kalla.get("image"))},
        "deploy_trigger": sorted(
            ({"repo": t.get("repository"), "gren": t.get("branch"), "leverantor": t.get("provider"),
              "vanta_pa_ci": t.get("checkSuites")} for t in triggers),
            key=lambda t: json.dumps(t, sort_keys=True),
        ),
        "byggare": instans.get("builder"),
        "dockerfile": instans.get("dockerfilePath"),
        "railway_konfigfil": instans.get("railwayConfigFile"),
        "byggkommando": rensa_text(instans.get("buildCommand")),
        "startkommando": rensa_text(instans.get("startCommand")),
        "fore_deploy": rensa_text(instans.get("preDeployCommand")),
        "rotkatalog": instans.get("rootDirectory"),
        "bevakade_sokvagar": sorted(instans.get("watchPatterns") or []),
        "regioner_och_repliker": regioner or {},
        "halsokontroll": {"sokvag": instans.get("healthcheckPath"), "timeout_s": instans.get("healthcheckTimeout")},
        "omstart": {"policy": instans.get("restartPolicyType"), "max_forsok": instans.get("restartPolicyMaxRetries")},
        "cron": instans.get("cronSchedule"),
        "sleep": instans.get("sleepApplication"),
        "draining_s": instans.get("drainingSeconds"),
        "overlap_s": instans.get("overlapSeconds"),
        "domaner": {
            "railway": sorted(d["domain"] for d in (domaner.get("serviceDomains") or []) if d.get("domain")),
            "egna": sorted(d["domain"] for d in (domaner.get("customDomains") or []) if d.get("domain")),
        },
        # Bara på/av och intern port: proxyns publika adress och port är databasens ingång.
        "tcp_proxy": {
            "pa": bool(tcp),
            "portar": sorted(p.get("applicationPort") for p in tcp if p.get("applicationPort") is not None),
        },
        "volymer": sorted(
            ({"namn": ((v.get("volume") or {}).get("name")), "monteringssokvag": v.get("mountPath")} for v in volymer),
            key=lambda v: json.dumps(v, sort_keys=True),
        ),
    }


def hamta(fraga: Callable[[str, dict], dict] = gql) -> dict[str, Any]:
    """Läget just nu, i baslinjens form. Värden maskeras innan de lämnar funktionen."""
    projekt = fraga(PROJEKTFRAGA, {"id": PROJECT_ID})["project"]
    if projekt is None:
        sys.exit("Projektet hittades inte med den här token; ingen baslinje hämtad.")
    miljoer = {m["id"]: m for m in _kanter(projekt.get("environments"))}
    regioner: dict[str, dict[str, Any]] = {}
    for miljo in miljoer.values():
        konfig = miljo.pop("config", None)  # konfigen lämnar aldrig funktionen
        tjanst_ids = [t["id"] for t in _kanter(projekt.get("services"))]
        regioner[miljo["id"]] = {sid: regioner_ur_konfig(konfig, sid) for sid in tjanst_ids}
        del konfig
    ut: dict[str, Any] = {}
    for miljo in miljoer.values():
        if miljo["name"] not in MILJOER:
            continue
        ut[miljo["name"]] = {"tjanster": {}}
    for tjanst in _kanter(projekt.get("services")):
        for instans in _kanter(tjanst.get("serviceInstances")):
            miljo = miljoer.get(instans.get("environmentId"))
            if not miljo or miljo["name"] not in MILJOER or instans.get("deletedAt"):
                continue
            triggers = [t for t in _kanter(miljo.get("deploymentTriggers")) if t.get("serviceId") == tjanst["id"]]
            volymer = [v for v in _kanter(miljo.get("volumeInstances"))
                       if v.get("serviceId") == tjanst["id"] and not v.get("deletedAt")]
            svar = fraga(INSTANSFRAGA, {"p": PROJECT_ID, "e": miljo["id"], "s": tjanst["id"]})
            maskat = maskera_variabler(svar.get("variables") or {})
            tcp = [p for p in (svar.get("tcpProxies") or []) if not p.get("deletedAt")]
            del svar  # råa värden lämnar aldrig funktionen
            ut[miljo["name"]]["tjanster"][tjanst["name"]] = {
                "installningar": normalisera_instans(instans, triggers, volymer, tcp,
                                                     regioner[miljo["id"]].get(tjanst["id"])),
                **maskat,
            }
    return {
        "projekt": projekt.get("name") or PROJEKTNAMN,
        "projekt_id": PROJECT_ID,
        "hamtad": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "miljoer": ut,
    }


# --------------------------------------------------------------------------
# Jämförelse och fil. Rena funktioner.
# --------------------------------------------------------------------------

def till_json(baslinje: Mapping[str, Any]) -> str:
    """Deterministisk text: sorterade nycklar, två blanksteg, LF och avslutande radbrytning."""
    return json.dumps(baslinje, sort_keys=True, indent=2, ensure_ascii=False) + "\n"


def _plana(varde: Any, prefix: str = "") -> dict[str, Any]:
    """Inställningar som platta nycklar (halsokontroll.sokvag) så att varje skillnad blir en rad."""
    if isinstance(varde, dict):
        ut: dict[str, Any] = {}
        for k, v in varde.items():
            ut.update(_plana(v, f"{prefix}.{k}" if prefix else k))
        return ut
    return {prefix: varde}


def _visa(v: Any) -> str:
    return json.dumps(v, ensure_ascii=False, sort_keys=True)


def jamfor(baslinje: Mapping[str, Any], nu: Mapping[str, Any]) -> list[str]:
    """En rad per avvikelse mellan baslinjen och läget nu. Tom lista = inga avvikelser.

    `hamtad` jämförs inte. Värden finns bara för vitlistade variabler, så en
    ändrad hemlighet med oförändrat namn syns inte (med flit, se docstringen).
    """
    rader: list[str] = []
    if baslinje.get("projekt") != nu.get("projekt"):
        rader.append(f"~ projekt: {baslinje.get('projekt')} -> {nu.get('projekt')}")
    gm, nm = baslinje.get("miljoer") or {}, nu.get("miljoer") or {}
    for miljo in sorted(set(gm) | set(nm)):
        if miljo not in nm:
            rader.append(f"- miljö {miljo}")
            continue
        if miljo not in gm:
            rader.append(f"+ miljö {miljo}")
            continue
        gt, nt = gm[miljo].get("tjanster") or {}, nm[miljo].get("tjanster") or {}
        for tjanst in sorted(set(gt) | set(nt)):
            plats = f"[{miljo}/{tjanst}]"
            if tjanst not in nt:
                rader.append(f"- tjänst {plats}")
                continue
            if tjanst not in gt:
                rader.append(f"+ tjänst {plats}")
                continue
            g, n = gt[tjanst], nt[tjanst]
            gi, ni = _plana(g.get("installningar") or {}), _plana(n.get("installningar") or {})
            for nyckel in sorted(set(gi) | set(ni)):
                if gi.get(nyckel) != ni.get(nyckel):
                    rader.append(f"~ inställning {plats} {nyckel}: {_visa(gi.get(nyckel))} -> {_visa(ni.get(nyckel))}")
            gv, nv = set(g.get("variabler") or []), set(n.get("variabler") or [])
            for namn in sorted(gv - nv):
                rader.append(f"- variabel {plats} {namn}")
            for namn in sorted(nv - gv):
                rader.append(f"+ variabel {plats} {namn}")
            gvard, nvard = g.get("varden") or {}, n.get("varden") or {}
            for namn in sorted((set(gvard) | set(nvard)) & gv & nv):
                fore = gvard.get(namn, "(satt)")
                efter = nvard.get(namn, "(satt)")
                if fore != efter:
                    rader.append(f"~ värde {plats} {namn}: {fore} -> {efter}")
    return rader


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Railway-konfigurationens baslinje (ISO 27001 A.8.9).")
    grupp = parser.add_mutually_exclusive_group(required=True)
    grupp.add_argument("--skriv", action="store_true", help=f"skriv baslinjen till {BASLINJEFIL.relative_to(REPO_ROOT)}")
    grupp.add_argument("--jamfor", action="store_true", help="visa avvikelser mot baslinjefilen; exit 1 om något avviker")
    args = parser.parse_args(argv)

    if args.jamfor:
        if not BASLINJEFIL.exists():
            print(f"Baslinjefilen saknas: {BASLINJEFIL.relative_to(REPO_ROOT)}. Kör --skriv först.")
            return 2
        baslinje = json.loads(BASLINJEFIL.read_text(encoding="utf-8"))
        nu = hamta()
        rader = jamfor(baslinje, nu)
        print(f"Railway {nu['projekt']}: baslinjen från {baslinje.get('hamtad')} mot läget {nu['hamtad']}")
        for rad in rader:
            print(f"  {rad}")
        print(f"{len(rader)} avvikelse(r).")
        return 1 if rader else 0

    nu = hamta()
    BASLINJEFIL.parent.mkdir(parents=True, exist_ok=True)
    with open(BASLINJEFIL, "w", newline="\n", encoding="utf-8") as fil:
        fil.write(till_json(nu))
    antal = sum(len(m["tjanster"]) for m in nu["miljoer"].values())
    print(f"Baslinjen skriven: {BASLINJEFIL.relative_to(REPO_ROOT)} ({len(nu['miljoer'])} miljöer, {antal} tjänstinstanser).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
