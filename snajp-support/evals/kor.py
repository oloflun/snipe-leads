"""Kör evalsviterna mot en driftsatt miljö och bedömer svaren.

    python -m evals.kor forbered --env development          # egna evalkunder + kunskapsbas
    python -m evals.kor kor --env development --agent alla --etikett fore
    python -m evals.kor jamfor fore efter                   # före mot efter

Sviterna körs mot api:t som en kund gör: supporten genom chatten (is_test),
Iris genom utkastvägen och kvittohanteraren genom uppladdningen. Evalkunderna
är egna, tomma kunder (`eval-…`), så inget blandas med en riktig kunds data.

Nycklar läses ur `.env.deploy` och skrivs aldrig ut. `forbered` lägger
evalkundernas nycklar i samma fil (`EVAL_<MILJÖ>_NYCKLAR`).
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

from . import bedomning

HAR = Path(__file__).resolve().parent
UT = HAR.parents[1] / "docs" / "stabilitet-2026-11" / "eval"
SVITER = {"support": "support_livrustning.json", "iris": "iris_utkast.json", "kvitto": "kvitto.json"}


# -- Miljö och nycklar -----------------------------------------------------------


def _envfil(angiven: str | None) -> Path:
    if angiven:
        return Path(angiven)
    for katalog in [Path.cwd(), *Path.cwd().parents, *HAR.parents]:
        if (katalog / ".env.deploy").exists():
            return katalog / ".env.deploy"
    # Ett git-arbetsträd har inte den oincheckade filen; huvudkatalogen har den.
    for katalog in HAR.parents:
        if katalog.name == ".claude" and (katalog.parent / ".env.deploy").exists():
            return katalog.parent / ".env.deploy"
    sys.exit("Hittar ingen .env.deploy. Ange den med --env-fil.")


def _las_env(fil: Path) -> dict[str, str]:
    ut: dict[str, str] = {}
    for rad in fil.read_text(encoding="utf-8").splitlines():
        rad = rad.strip()
        if rad and not rad.startswith("#") and "=" in rad:
            namn, varde = rad.split("=", 1)
            ut[namn.strip()] = varde.strip().strip('"').strip("'")
    return ut


class Miljo:
    def __init__(self, namn: str, envfil: Path) -> None:
        self.namn = namn
        self.envfil = envfil
        env = _las_env(envfil)
        prefix = f"RAILWAY_{namn.upper()}_"
        if prefix + "API_URL" not in env:
            sys.exit(f"{prefix}API_URL saknas i {envfil.name}.")
        self.api = env[prefix + "API_URL"].rstrip("/")
        self.master = env.get(prefix + "MASTER_API_KEY", "")
        self.nycklar = [n for n in env.get(f"EVAL_{namn.upper()}_NYCKLAR", "").split(",") if n]
        #: Kvittohanterarens evalkund heter som bolaget i sviten och har dess
        #: org.nr, så att kundfakturorna (intäkter) går att känna igen.
        self.kvittonyckel = env.get(f"EVAL_{namn.upper()}_KVITTONYCKEL", "")

    def spara_varde(self, namn: str, varde: str) -> None:
        rader = [r for r in self.envfil.read_text(encoding="utf-8").splitlines() if not r.startswith(namn + "=")]
        rader.append(f"{namn}={varde}")
        self.envfil.write_text("\n".join(rader) + "\n", encoding="utf-8")

    def spara_nycklar(self, nycklar: list[str]) -> None:
        namn = f"EVAL_{self.namn.upper()}_NYCKLAR"
        rader = [r for r in self.envfil.read_text(encoding="utf-8").splitlines() if not r.startswith(namn + "=")]
        rader.append(f"{namn}={','.join(nycklar)}")
        self.envfil.write_text("\n".join(rader) + "\n", encoding="utf-8")
        self.nycklar = nycklar


def _las_svit(agent: str) -> list[dict[str, Any]]:
    return json.loads((HAR / SVITER[agent]).read_text(encoding="utf-8"))["fall"]


# -- forbered ------------------------------------------------------------------


def forbered(miljo: Miljo, antal: int, kb_fil: Path, behall: bool = False) -> None:
    """Skapar evalkunder. Den FÖRSTA är supportens: den får kunskapsbasen och
    ingenting annat. De övriga är Iris (forbered-iris ger dem affärskontext).
    `behall` lägger de nya kunderna före de befintliga i stället för att
    ersätta dem."""
    if not miljo.master:
        sys.exit("Masternyckeln för miljön saknas i .env.deploy.")
    stampel = datetime.now(timezone.utc).strftime("%m%d%H%M")
    nycklar: list[str] = []
    with httpx.Client(timeout=120) as klient:
        for nr in range(1, antal + 1):
            svar = klient.post(
                miljo.api + "/api/keys",
                headers={"X-API-Key": miljo.master},
                json={"tenant_name": f"Evalkund {stampel}-{nr}", "slug": f"eval-{stampel}-{nr}"},
            )
            svar.raise_for_status()
            kropp = svar.json()
            nyckel = next((v for k, v in kropp.items() if "key" in k.lower() and isinstance(v, str)), None)
            if not nyckel:
                sys.exit(f"Svaret från /api/keys bar ingen nyckel (fält: {sorted(kropp)}).")
            nycklar.append(nyckel)
            print(f"evalkund {nr} av {antal} skapad (eval-{stampel}-{nr})")
        artiklar = json.loads(kb_fil.read_text(encoding="utf-8"))
        svar = klient.post(
            miljo.api + "/api/kb",
            headers={"X-API-Key": nycklar[0]},
            json={"articles": [{"title": a["title"], "content": a["content"], "category": a["category"]} for a in artiklar]},
            timeout=300,
        )
        svar.raise_for_status()
        kropp = svar.json()
        print(f"kunskapsbas: {len(kropp.get('created') or [])} artiklar, {kropp.get('embeddings')} med vektor")
    miljo.spara_nycklar(nycklar + (miljo.nycklar if behall else []))
    print(f"{len(miljo.nycklar)} nycklar sparade i {miljo.envfil.name} (inte utskrivna)")


KVITTOBOLAG = "Evalbolaget AB"
KVITTOBOLAG_ORGNR = "559900-4172"


def forbered_kvitto(miljo: Miljo) -> None:
    """En egen evalkund för kvittohanteraren, med svitens bolagsnamn och org.nr."""
    if not miljo.master:
        sys.exit("Masternyckeln för miljön saknas i .env.deploy.")
    stampel = datetime.now(timezone.utc).strftime("%m%d%H%M")
    with httpx.Client(timeout=120, headers={"X-API-Key": miljo.master}) as klient:
        svar = klient.post(miljo.api + "/api/keys", json={"tenant_name": KVITTOBOLAG, "slug": f"eval-{stampel}-kvitto"})
        svar.raise_for_status()
        kropp = svar.json()
        orgnr = klient.put(
            f"{miljo.api}/api/admin/tenants/{kropp['tenant_id']}/kunddata", json={"orgnr": KVITTOBOLAG_ORGNR}
        )
        orgnr.raise_for_status()
    miljo.spara_varde(f"EVAL_{miljo.namn.upper()}_KVITTONYCKEL", kropp["api_key"])
    print(f"kvittohanterarens evalkund skapad (eval-{stampel}-kvitto), nyckeln sparad i {miljo.envfil.name}")


def forbered_iris(miljo: Miljo) -> None:
    """Evalkundernas affärskontext: utan produktbeskrivning skriver Iris inget
    utkast alls (leads/business_context.py). Texten är svitens erbjudande."""
    if not miljo.nycklar:
        sys.exit("Inga evalnycklar för miljön. Kör `forbered` först.")
    erbjudande = _las_svit("iris")[0]["offer_summary"]
    underlag = {
        "product_marketing": f"Evalbolaget AB.\n\n{erbjudande}",
        "customer_research": (
            "Målgrupp: svenska små och medelstora företag som får kundfrågor via mejl och chatt "
            "och saknar en egen kundtjänstavdelning. Beslutsfattare är oftast VD, ägare eller kundansvarig."
        ),
    }
    # Supportens evalkund (den första) får ingen affärskontext: den ska bara
    # bära kunskapsbasen, annars beskriver dess supportsvar fel bolag.
    with httpx.Client(timeout=120) as klient:
        for nr, nyckel in enumerate(miljo.nycklar[1:] or miljo.nycklar, 2):
            for slag, text in underlag.items():
                svar = klient.post(
                    miljo.api + "/api/leads/context-docs",
                    headers={"X-API-Key": nyckel},
                    json={"kind": slag, "content": text, "source": "evalsviten"},
                )
                svar.raise_for_status()
            status = klient.get(miljo.api + "/api/leads/onboarding/status", headers={"X-API-Key": nyckel}).json()
            print(f"evalkund {nr}: affärskontext sparad, saknas fortfarande: {status.get('missing') or 'inget'}")


# -- Körning per agent -----------------------------------------------------------


def _steg(resultat: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {"skill": s.get("skill"), "ms": s.get("latency_ms"), "forsok": s.get("attempts")}
        for s in (resultat.get("step_log") or [])
        if isinstance(s, dict) and "skill" in s
    ]


def _vanta_jobb(klient: httpx.Client, api: str, huvud: dict[str, str], job_id: str, tak_s: float) -> dict[str, Any]:
    start = time.perf_counter()
    while time.perf_counter() - start < tak_s:
        time.sleep(0.5)
        try:
            jobb = klient.get(f"{api}/api/jobs/{job_id}", headers=huvud).json()
        except (httpx.HTTPError, ValueError):
            continue
        if jobb.get("status") in ("completed", "failed"):
            return jobb
    return {"status": "tidsgrans", "error": f"inget svar på {tak_s:.0f} s"}


def _kor_support(miljo: Miljo, fall: dict[str, Any], nr: int) -> dict[str, Any]:
    huvud = {"X-API-Key": miljo.nycklar[0]}
    with httpx.Client(timeout=60) as klient:
        start = time.perf_counter()
        svar = klient.post(
            miljo.api + "/api/chat",
            headers=huvud,
            json={
                "message": fall["fraga"],
                "subject": fall.get("amne", ""),
                "customer_email": f"{uuid.uuid4()}@session.snajp.se",
                "is_test": True,
            },
        )
        if svar.status_code != 202:
            return {"fel": f"start {svar.status_code}: {svar.text[:200]}", "latens_s": 0.0, "svar": {}}
        jobb = _vanta_jobb(klient, miljo.api, huvud, svar.json()["job_id"], 240)
        latens = time.perf_counter() - start
    res = jobb.get("result") or {}
    return {
        "fel": None if jobb.get("status") == "completed" else str(jobb.get("error") or jobb.get("status")),
        "latens_s": round(latens, 2),
        "svar": {
            "reply": res.get("reply"), "escalated": res.get("escalated"), "overlamnad": res.get("overlamnad"),
            "escalation_code": res.get("escalation_code"), "category": res.get("category"),
            "svarslage": res.get("svarslage"), "steg": _steg(res),
        },
    }


def _kor_iris(miljo: Miljo, fall: dict[str, Any], nr: int) -> dict[str, Any]:
    iriskunder = miljo.nycklar[1:] or miljo.nycklar
    huvud = {"X-API-Key": iriskunder[nr % len(iriskunder)]}
    with httpx.Client(timeout=60) as klient:
        start = time.perf_counter()
        ny = klient.post(
            miljo.api + "/api/leads/prospects",
            headers=huvud,
            json={"company_name": fall["company_name"], "contact_email": fall["prospect_email"]},
        )
        if ny.status_code >= 400:
            return {"fel": f"prospekt {ny.status_code}: {ny.text[:200]}", "latens_s": 0.0, "svar": {}}
        kropp = ny.json()
        prospekt_id = (kropp.get("prospect") or kropp).get("id")
        svar = klient.post(
            miljo.api + "/api/leads/outreach/draft",
            headers=huvud,
            json={
                "prospect_id": prospekt_id,
                **{k: fall[k] for k in ("prospect_email", "company_name", "offer_summary", "brief",
                                         "research_summary", "research_evidence")},
                "struktur": fall.get("struktur") or "a",
            },
        )
        if svar.status_code != 202:
            return {"fel": f"start {svar.status_code}: {svar.text[:200]}", "latens_s": 0.0, "svar": {}}
        jobb = _vanta_jobb(klient, miljo.api, huvud, svar.json()["job_id"], 1200)
        latens = time.perf_counter() - start
    res = jobb.get("result") or {}
    return {
        "fel": None if jobb.get("status") == "completed" else str(jobb.get("error") or jobb.get("status")),
        "latens_s": round(latens, 2),
        "svar": {
            "subject": res.get("subject"), "body": res.get("body"), "queued": res.get("queued"),
            "escalated": res.get("escalated"), "escalation_reason": res.get("escalation_reason"),
            "tokens_in": res.get("tokens_in"), "steg": _steg(res),
        },
    }


def _kor_kvitto(miljo: Miljo, fall: dict[str, Any], nr: int, etikett: str = "") -> dict[str, Any]:
    huvud = {"X-API-Key": miljo.kvittonyckel or miljo.nycklar[nr % len(miljo.nycklar)]}
    pdf = bedomning.enkel_pdf(fall["text"], titel=f"{etikett}-{fall['id']}-{uuid.uuid4().hex[:8]}")
    with httpx.Client(timeout=180) as klient:
        start = time.perf_counter()
        svar = klient.post(
            miljo.api + "/api/kvitton/underlag",
            headers=huvud,
            files={"fil": (fall["filnamn"], pdf, "application/pdf")},
            data={"riktning": fall["riktning"]} if fall.get("riktning") else None,
        )
        latens = time.perf_counter() - start
    if svar.status_code == 422:
        return {"fel": None, "latens_s": round(latens, 2), "svar": {"avvisad": True, "skal": svar.text[:300]}}
    if svar.status_code >= 400:
        return {"fel": f"{svar.status_code}: {svar.text[:200]}", "latens_s": round(latens, 2), "svar": {}}
    kropp = svar.json()
    rad = kropp.get("underlag") or {}
    return {
        "fel": None,
        "latens_s": round(latens, 2),
        "svar": {
            "status": kropp.get("status"), "brister": kropp.get("brister"),
            "underlag": {k: rad.get(k) for k in ("datum", "motpart", "brutto", "momssats", "kategori",
                                                   "riktning", "belopp_original", "status")},
        },
    }


def kor(miljo: Miljo, agent: str, etikett: str, urval: int | None, samtidiga: int) -> dict[str, Any]:
    if not miljo.nycklar:
        sys.exit("Inga evalnycklar för miljön. Kör `forbered` först.")
    fall = _las_svit(agent)
    if urval:
        fall = [f for f in fall if f.get("kor_live", True)][:urval]
    rubrik = json.loads((HAR / "iris_rubrik.json").read_text(encoding="utf-8")) if agent == "iris" else {}
    korare = {"support": _kor_support, "iris": _kor_iris, "kvitto": _kor_kvitto}[agent]

    def ett(arg: tuple[int, dict[str, Any]]) -> dict[str, Any]:
        nr, f = arg
        try:
            utfall = korare(miljo, f, nr, etikett) if agent == "kvitto" else korare(miljo, f, nr)
        except Exception as fel:  # noqa: BLE001 — ett fall som faller stoppar inte sviten
            utfall = {"fel": f"{type(fel).__name__}: {fel}", "latens_s": 0.0, "svar": {}}
        if agent == "support":
            kriterier = bedomning.bedom_support(f, utfall["svar"])
        elif agent == "iris":
            kriterier = bedomning.bedom_iris(f, utfall["svar"], rubrik)
        else:
            kriterier = bedomning.bedom_kvitto(f, utfall["svar"])
        if utfall["fel"]:
            kriterier = {k: False for k in kriterier}
        if agent == "iris":
            utfall["upplysning"] = {"signal": bedomning.iris_signal(f, utfall["svar"])}
        print(f"  {'ok ' if all(kriterier.values()) else 'NEJ'} {f['id']:<34} {utfall['latens_s']:>6.1f} s"
              + (f"  ({utfall['fel'][:60]})" if utfall["fel"] else ""), flush=True)
        return {"id": f["id"], "typ": f.get("typ"), "kriterier": kriterier, **utfall}

    with ThreadPoolExecutor(max_workers=samtidiga) as pool:
        rader = list(pool.map(ett, enumerate(fall)))

    latenser = sorted(r["latens_s"] for r in rader if not r["fel"])
    try:
        commit = httpx.get(miljo.api + "/health", timeout=15).json().get("commit")
    except Exception:  # noqa: BLE001
        commit = None
    rapport = {
        "etikett": etikett, "agent": agent, "miljo": miljo.namn, "commit": commit,
        "tid": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "sammanfattning": bedomning.sammanfatta(rader),
        "tekniska_fel": sum(1 for r in rader if r["fel"]),
        "latens_s": {
            "p50": round(statistics.median(latenser), 1) if latenser else None,
            "p95": round(latenser[max(0, int(len(latenser) * 0.95) - 1)], 1) if latenser else None,
            "max": latenser[-1] if latenser else None,
        },
        "fall": rader,
    }
    if agent == "iris":
        rapport["signal_andel"] = round(sum(bool((r.get("upplysning") or {}).get("signal")) for r in rader) / len(rader), 3)
    if agent == "support":
        forsok = [s["forsok"] for r in rader for s in r["svar"].get("steg") or [] if s["skill"] == "cs:ticket-triage"]
        rapport["triage_omforsok_andel"] = round(sum(1 for f in forsok if (f or 1) > 1) / len(forsok), 3) if forsok else None
    UT.mkdir(parents=True, exist_ok=True)
    (UT / f"{etikett}-{agent}.json").write_text(json.dumps(rapport, ensure_ascii=False, indent=1), encoding="utf-8")
    s = rapport["sammanfattning"]
    print(f"{agent}: {s['godkanda']}/{s['antal']} godkända ({s['andel']:.0%}), "
          f"p50 {rapport['latens_s']['p50']} s, p95 {rapport['latens_s']['p95']} s, "
          f"{rapport['tekniska_fel']} tekniska fel")
    print("   per kriterium:", s["per_kriterium"])
    return rapport


def ombedom(etikett: str) -> None:
    """Bedömer sparade svar på nytt mot sviten som den ser ut nu, utan att
    köra om något. Används när ett falls förväntan har rättats: svaren är
    desamma, och före och efter ska mätas mot samma mall."""
    for agent in SVITER:
        fil = UT / f"{etikett}-{agent}.json"
        if not fil.exists():
            continue
        rapport = json.loads(fil.read_text(encoding="utf-8"))
        fall = {f["id"]: f for f in _las_svit(agent)}
        rubrik = json.loads((HAR / "iris_rubrik.json").read_text(encoding="utf-8")) if agent == "iris" else {}
        for rad in rapport["fall"]:
            f = fall.get(rad["id"])
            if f is None:
                continue
            if agent == "support":
                kriterier = bedomning.bedom_support(f, rad["svar"])
            elif agent == "iris":
                kriterier = bedomning.bedom_iris(f, rad["svar"], rubrik)
                rad["upplysning"] = {"signal": bedomning.iris_signal(f, rad["svar"])}
            else:
                kriterier = bedomning.bedom_kvitto(f, rad["svar"])
            rad["kriterier"] = {k: False for k in kriterier} if rad.get("fel") else kriterier
            rad["typ"] = f.get("typ")
        rapport["sammanfattning"] = bedomning.sammanfatta(rapport["fall"])
        if agent == "iris":
            rapport["signal_andel"] = round(
                sum(bool((r.get("upplysning") or {}).get("signal")) for r in rapport["fall"]) / len(rapport["fall"]), 3
            )
        rapport["ombedomd"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
        fil.write_text(json.dumps(rapport, ensure_ascii=False, indent=1), encoding="utf-8")
        s = rapport["sammanfattning"]
        print(f"{agent}: {s['godkanda']}/{s['antal']} godkända ({s['andel']:.0%}) {s['per_kriterium']}")


def jamfor(fore: str, efter: str) -> None:
    for agent in SVITER:
        a, b = UT / f"{fore}-{agent}.json", UT / f"{efter}-{agent}.json"
        if not (a.exists() and b.exists()):
            continue
        ra, rb = json.loads(a.read_text(encoding="utf-8")), json.loads(b.read_text(encoding="utf-8"))
        sa, sb = ra["sammanfattning"], rb["sammanfattning"]
        print(f"\n{agent}: {sa['godkanda']}/{sa['antal']} → {sb['godkanda']}/{sb['antal']} godkända, "
              f"p50 {ra['latens_s']['p50']} → {rb['latens_s']['p50']} s, p95 {ra['latens_s']['p95']} → {rb['latens_s']['p95']} s")
        for k in sorted(set(sa["per_kriterium"]) | set(sb["per_kriterium"])):
            print(f"   {k:<14} {sa['per_kriterium'].get(k)} → {sb['per_kriterium'].get(k)}")
        fa = {r["id"]: all(r["kriterier"].values()) for r in ra["fall"]}
        fb = {r["id"]: all(r["kriterier"].values()) for r in rb["fall"]}
        print("   nu godkända:", sorted(i for i in fb if fb[i] and not fa.get(i, False)) or "inga")
        print("   nu underkända:", sorted(i for i in fb if not fb[i] and fa.get(i, False)) or "inga")


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="kommando", required=True)
    f = sub.add_parser("forbered")
    f.add_argument("--env", default="development")
    f.add_argument("--env-fil")
    f.add_argument("--antal", type=int, default=3)
    f.add_argument("--kb", default=str(HAR / "kb" / "livrustning.json"))
    f.add_argument("--behall", action="store_true", help="lägg de nya kunderna före de befintliga")
    k = sub.add_parser("kor")
    k.add_argument("--env", default="development")
    k.add_argument("--env-fil")
    k.add_argument("--agent", choices=[*SVITER, "alla"], default="alla")
    k.add_argument("--etikett", required=True)
    k.add_argument("--urval", type=int)
    k.add_argument("--samtidiga", type=int, default=3)
    fi = sub.add_parser("forbered-iris")
    fi.add_argument("--env", default="development")
    fi.add_argument("--env-fil")
    fk = sub.add_parser("forbered-kvitto")
    fk.add_argument("--env", default="development")
    fk.add_argument("--env-fil")
    o = sub.add_parser("ombedom")
    o.add_argument("etikett")
    j = sub.add_parser("jamfor")
    j.add_argument("fore")
    j.add_argument("efter")
    a = p.parse_args()
    if a.kommando == "jamfor":
        jamfor(a.fore, a.efter)
        return
    if a.kommando == "ombedom":
        ombedom(a.etikett)
        return
    if a.env == "main":
        sys.exit("Evalsviterna körs inte mot produktionen.")
    miljo = Miljo(a.env, _envfil(a.env_fil))
    if a.kommando == "forbered":
        forbered(miljo, a.antal, Path(a.kb), a.behall)
        return
    if a.kommando == "forbered-kvitto":
        forbered_kvitto(miljo)
        return
    if a.kommando == "forbered-iris":
        forbered_iris(miljo)
        return
    for agent in SVITER if a.agent == "alla" else [a.agent]:
        kor(miljo, agent, a.etikett, a.urval, a.samtidiga)


if __name__ == "__main__":
    main()
