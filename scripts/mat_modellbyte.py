"""Mätning inför bytet från gemini-2.5 (pensionsdatum 2026-10-20): samma
evalsviter mot varje kandidat, lokalt, utan någon driftsatt miljö.

    python scripts/mat_modellbyte.py --modell gemini-2.5-flash --region europe-west1 \
        --utkastmodell gemini-2.5-pro --matning alla --etikett bas
    python scripts/mat_modellbyte.py --modell gemini-3.8-flash --region eu --matning alla --etikett g38
    python scripts/mat_modellbyte.py --modell gemini-3.5-flash --region europe-west3 --matning support

Underlag och resultat: docs/compliance/modellbyte-underlag.md.

## Vad som mäts, och mot vilken data

Bara repots egna fixturer. Ingen databas öppnas (DATABASE_URL töms i den här
processen och allt körs mot MemoryStorage), och ingen kunddata finns i någon
av sviterna:

  support  `evals/support_livrustning.json` genom `run_support_agent`, med
           kunskapsbasens ögonblicksbild `evals/kb/livrustning.json` (pilot-
           kundens publika produktinformation), bedömd av
           `evals.bedomning.bedom_support`. Samma fall och mall som
           `python -m evals.kor kor --agent support`, men i processen i stället
           för genom en miljös api.
  golden   `app.agent.evals.SUPPORT_GOLDEN` (Nordlys, syntetisk) genom
           `kor_support_evals`: eskaleringsbeslut, kategori, faktagrind.
  triage   samma supportfall genom mejlinkorgens `triage_email_llm`, med hela
           kunskapsbasen: eskaleringsbeslutet mot fallets utfall, och
           svarsutkastet mot `bedom_support`.
  iris     `evals/iris_utkast.json` (påhittade bolag, .example-adresser) genom
           `run_outreach_draft_v2`, bedömd av `bedom_iris` OCH av stilgrinden
           som låser facit (INV-LEADS-UTKAST-002: `stilkontroll.kontrollera`
           med facitets tillåtna fynd, `amne_fynd`).

Kunskapsbasens sökning i MemoryStorage är ordöverlapp (inbäddningar används
inte), så alla kandidater får samma träffar. Svarscachen är av.

## Nycklar

Servicekontot läses ur snajp-support/.env (utvecklarnas lokala fil, se
HANDOFF-2026-09-12-VERTEX-AI.md) av det här skriptet och läggs bara i den egna
processens miljö. Det skrivs aldrig ut.

## Kostnad

Varje mätning körs en gång per kandidat. Tokens räknas på varje anrop, och
körningen avbryts när --tak-kr passeras. Listpriserna (USD per miljon tokens,
icke-global ändpunkt, hämtade 2026-11-18 ur cloud.google.com/vertex-ai/
generative-ai/pricing) står i PRIS.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROT = Path(__file__).resolve().parents[1]
SUPPORT = ROT / "snajp-support"
sys.path.insert(0, str(SUPPORT))

UT = ROT / "var" / "modellbyte"
USD_SEK = 10.5

#: USD per miljon tokens (in, ut inklusive tänkande). Icke-global ändpunkt
#: (regional eller multiregion), som är 10 % dyrare än global. 2.5-modellerna
#: har ett pris oavsett ändpunkt. gemini-3.8-flash: introduktionspris t.o.m.
#: 2026-12-31, därefter 1.65 / 8.25.
PRIS = {
    "gemini-2.5-flash": (0.30, 2.50),
    "gemini-2.5-pro": (1.25, 10.00),
    "gemini-2.5-flash-lite": (0.10, 0.40),
    "gemini-3.8-flash": (0.825, 4.125),
    "gemini-3.8-flash@2027": (1.65, 8.25),
    "gemini-3.5-flash": (1.65, 9.90),
    "gemini-3.5-flash-lite": (0.33, 2.75),
    # 2026-11-20: AI Studio-prislistan (aistudio.google.com/docs/pricing,
    # global) + 10 % för eu, samma påslag som bekräftats i kontots SKU-lista
    # för 3.8-flash och 3.5-flash-lite.
    "gemini-3.6-flash": (0.825, 4.125),
    "gemini-4-hydrogen": (1.65, 8.25),
    "gemini-4-neon": (3.30, 16.50),
    # 3.7-flash står inte i prislistans ordagranna del; 3.8:s pris som
    # platshållare så att kostnadstaket ändå räknar.
    "gemini-3.7-flash": (0.825, 4.125),
}


# -- Miljön ---------------------------------------------------------------------


def _lokal_env() -> Path:
    for katalog in [SUPPORT, *SUPPORT.parents]:
        kandidat = katalog / "snajp-support" / ".env" if katalog != SUPPORT else katalog / ".env"
        if kandidat.exists():
            return kandidat
    # Ett git-arbetsträd saknar den oincheckade filen; huvudkatalogen har den.
    for katalog in SUPPORT.parents:
        if katalog.name == ".claude" and (katalog.parent / "snajp-support" / ".env").exists():
            return katalog.parent / "snajp-support" / ".env"
    sys.exit("Hittar ingen snajp-support/.env med GOOGLE_SERVICE_ACCOUNT_JSON.")


def _las_servicekonto() -> str:
    for rad in _lokal_env().read_text(encoding="utf-8-sig").splitlines():
        namn, _, varde = rad.strip().partition("=")
        if namn.strip() == "GOOGLE_SERVICE_ACCOUNT_JSON":
            return varde.strip().strip("'").strip('"')
    sys.exit("GOOGLE_SERVICE_ACCOUNT_JSON saknas i snajp-support/.env.")


def satt_miljo(args: argparse.Namespace) -> None:
    os.environ["DATABASE_URL"] = ""
    os.environ["SEMANTIC_CACHE"] = "off"
    os.environ["ENVIRONMENT"] = "lokal"
    os.environ["LLM_PROVIDER"] = "gemini"
    os.environ["MODEL"] = args.modell
    os.environ["GOOGLE_CLOUD_REGION"] = args.region
    # Ingen reserv: kandidaterna finns inte i reservregionerna, och ett byte
    # vid 429 hade blandat in en annan region i mätningen.
    os.environ["VERTEX_RESERVREGIONER"] = args.region
    os.environ["VERTEX_INBADDNING_REGION"] = "europe-west1"
    # Samma chattgräns som development kör med 3.8 (underlaget avsnitt 6.2,
    # LLM_TIMEOUT_CHATT_S=60). Med kodens standard 20 s föll 3.8 på tid i
    # varje supportfall 2026-11-20, och mätningen sa då inget om svaren.
    os.environ["LLM_TIMEOUT_CHATT_S"] = str(args.chattgrans_s)
    os.environ["VISION_MODEL"] = args.modell
    utkast = args.utkastmodell or args.modell
    os.environ["LEADS_DRAFT_MODEL"] = utkast
    os.environ["LEADS_HUMANIZER_MODEL"] = utkast
    # --nyckelfil: ett annat projekts servicekonto (t.ex. kreditprojektet), så
    # att mätningen inte drar på produktionens kapacitet (risken i underlaget,
    # avsnitt 7). Filen läses i processen och skrivs aldrig ut.
    os.environ["GOOGLE_SERVICE_ACCOUNT_JSON"] = (
        Path(args.nyckelfil).read_text(encoding="utf-8") if args.nyckelfil else _las_servicekonto()
    )


# -- Tokens ---------------------------------------------------------------------


class Matare:
    """Räknar tokens per modell på varje chat.completions-anrop i processen."""

    def __init__(self, tak_kr: float) -> None:
        self.per_modell: dict[str, dict[str, int]] = {}
        self.anrop = 0
        self.tak_kr = tak_kr

    def installera(self) -> None:
        from openai.resources.chat.completions import AsyncCompletions

        original = AsyncCompletions.create
        matare = self

        async def create(self_, *a, **kw):
            svar = await original(self_, *a, **kw)
            modell = str(kw.get("model") or "").split("/")[-1]
            u = getattr(svar, "usage", None)
            rad = matare.per_modell.setdefault(modell, {"in": 0, "ut": 0, "tank": 0, "anrop": 0})
            rad["anrop"] += 1
            matare.anrop += 1
            if u is not None:
                rad["in"] += int(getattr(u, "prompt_tokens", 0) or 0)
                rad["ut"] += int(getattr(u, "completion_tokens", 0) or 0)
                detaljer = getattr(u, "completion_tokens_details", None)
                rad["tank"] += int(getattr(detaljer, "reasoning_tokens", 0) or 0) if detaljer else 0
            if matare.kostnad_kr() > matare.tak_kr:
                raise SystemExit(f"Kostnadstaket {matare.tak_kr} kr passerat, mätningen avbryts.")
            return svar

        AsyncCompletions.create = create  # type: ignore[method-assign]

    def kostnad_kr(self) -> float:
        summa = 0.0
        for modell, r in self.per_modell.items():
            pin, put = PRIS.get(modell, (0.0, 0.0))
            # Vertex debiterar tänkandet som utdata. OpenAI-lagret räknar det
            # inte alltid i completion_tokens, så det läggs på separat.
            summa += (r["in"] * pin + (r["ut"] + r["tank"]) * put) / 1e6
        return summa * USD_SEK

    def ogonblick(self) -> dict[str, Any]:
        return {"per_modell": json.loads(json.dumps(self.per_modell)), "kr": round(self.kostnad_kr(), 3)}


# -- Mätningarna -------------------------------------------------------------------


def _las(fil: str) -> dict[str, Any]:
    return json.loads((SUPPORT / "evals" / fil).read_text(encoding="utf-8"))


async def _livrustning(storage) -> tuple[str, list[dict[str, Any]]]:
    kb = json.loads((SUPPORT / "evals" / "kb" / "livrustning.json").read_text(encoding="utf-8"))
    tenant = await storage.create_tenant(slug="eval-livrustning", name="Livrustning AB", kraver_avtal=False)
    for a in kb:
        await storage.add_kb_article(tenant["id"], title=a["title"], content=a["content"], category=a["category"])
    return tenant["id"], kb


async def mat_support(urval: int | None) -> list[dict[str, Any]]:
    from app.agent.support_agent import run_support_agent
    from app.storage.memory import MemoryStorage
    from evals import bedomning

    rader = []
    for fall in _las("support_livrustning.json")["fall"][:urval]:
        storage = MemoryStorage()
        tenant_id, kb = await _livrustning(storage)
        start = time.perf_counter()
        try:
            res = await run_support_agent(
                storage, tenant_id, message=fall["fraga"], subject=fall.get("amne", ""), channel="web",
                customer_email=f"{fall['id']}@eval.example", customer_name=None, attachments=[], is_test=True,
            )
            fel = None
        except Exception as e:  # noqa: BLE001 — ett kraschat fall är ett underkänt fall
            res, fel = {}, f"{type(e).__name__}: {str(e)[:200]}"
        latens = time.perf_counter() - start
        krit = bedomning.bedom_support(fall, res) if not fel else {"utfall": False, "fakta": False, "inga_fel": False, "format": False}
        rader.append({
            "id": fall["id"], "typ": fall.get("typ"), "godkand": all(krit.values()), "kriterier": krit,
            "fel": fel, "latens_s": round(latens, 2), "kategori": res.get("category"),
            "eskalerade": bool(res.get("escalated") or res.get("overlamnad")), "svar": res.get("reply"),
        })
        print(f"  support {fall['id']}: {'OK ' if rader[-1]['godkand'] else 'FEL'} {latens:.1f}s", flush=True)
    return rader


async def mat_golden() -> list[dict[str, Any]]:
    from app.agent.evals import kor_support_evals

    rapport = await kor_support_evals()
    for r in rapport["resultat"]:
        print(f"  golden {r['case']}: {'OK ' if r['godkand'] else 'FEL'} {r['latency_ms']} ms", flush=True)
    return rapport["resultat"]


async def mat_triage(urval: int | None) -> list[dict[str, Any]]:
    from app.agent.triage import triage_email_llm
    from evals import bedomning

    kb = json.loads((SUPPORT / "evals" / "kb" / "livrustning.json").read_text(encoding="utf-8"))
    rader = []
    for fall in _las("support_livrustning.json")["fall"][:urval]:
        start = time.perf_counter()
        try:
            res = await triage_email_llm(
                sender=f"{fall['id']}@eval.example", subject=fall.get("amne", "") or "Fråga",
                body=fall["fraga"], kb_articles=kb, foretagsnamn="Livrustning AB",
            )
            fel = None
        except Exception as e:  # noqa: BLE001
            res, fel = {}, f"{type(e).__name__}: {str(e)[:200]}"
        latens = time.perf_counter() - start
        vill = fall.get("utfall", "svar")
        eskalering_ratt = vill == "valfritt" or ((vill == "overlamning") == bool(res.get("escalate")))
        krit = bedomning.bedom_support(fall, {"reply": res.get("draft_reply"), "escalated": res.get("escalate")}) if not fel else {}
        rader.append({
            "id": fall["id"], "godkand": bool(not fel and eskalering_ratt and all(krit.values())),
            "eskalering_ratt": eskalering_ratt and not fel, "kriterier": krit, "fel": fel,
            "kategori": res.get("category"), "beslut": res.get("beslut"), "latens_s": round(latens, 2),
            "utkast": res.get("draft_reply"),
        })
        print(f"  triage {fall['id']}: {'OK ' if rader[-1]['godkand'] else 'FEL'} {res.get('category')} {latens:.1f}s", flush=True)
    return rader


#: Fynd som facitets egna utkast bär (tests/leads/test_utkastfacit_2026_10_16.py).
FACIT_TILLATNA = {"lang_mening", "samma_uppmaning", "for_langt", "kopierat_exempel", "svara_sa_avslut", "kravande_ingang"}


async def mat_iris(urval: int | None) -> list[dict[str, Any]]:
    from app.agent.leads_research_v2 import run_outreach_draft_v2
    from app.leads import stilkontroll as stil
    from app.storage.memory import MemoryStorage
    from evals import bedomning

    svit = _las("iris_utkast.json")
    rubrik = _las("iris_rubrik.json")
    rader = []
    for fall in svit["fall"][:urval]:
        storage = MemoryStorage()
        tenant = await storage.create_tenant(slug="eval-iris", name="Evalbolaget AB", kraver_avtal=False)
        tid = tenant["id"]
        await storage.save_context_doc(tid, kind="product_marketing", content=f"Evalbolaget AB.\n\n{fall['offer_summary']}", source="evalsviten")
        await storage.save_context_doc(tid, kind="customer_research", content=(
            "Målgrupp: svenska små och medelstora företag som får kundfrågor via mejl och chatt "
            "och saknar en egen kundtjänstavdelning. Beslutsfattare är oftast VD, ägare eller kundansvarig."
        ), source="evalsviten")
        prospekt = await storage.create_prospect(tid, company_name=fall["company_name"], contact_email=fall["prospect_email"])
        trad = await storage.ensure_outreach_thread(tid, prospect_id=prospekt["id"])
        from app.leads.context_pack import build_context_pack

        context_pack, _ = await build_context_pack(storage, tid)
        start = time.perf_counter()
        try:
            res = await run_outreach_draft_v2(
                storage, tid, thread_id=trad["id"], prospect_email=fall["prospect_email"],
                tenant_name="Evalbolaget AB", company_name=fall["company_name"], offer_summary=fall["offer_summary"],
                context_pack=context_pack, brief=fall["brief"], research_summary=fall["research_summary"],
                research_evidence=tuple(fall["research_evidence"]), is_test=True, struktur=fall.get("struktur") or "a",
            )
            fel = None
        except Exception as e:  # noqa: BLE001
            res, fel = {}, f"{type(e).__name__}: {str(e)[:200]}"
        latens = time.perf_counter() - start
        krit = bedomning.bedom_iris(fall, res, rubrik) if not fel else {"levererat": False, "inga_pahitt": False, "skrivregler": False}
        kropp = str(res.get("body") or "")
        brodtext = re.split(r"\n-- ?\n|\nVänliga hälsningar|\nMed vänlig hälsning|\nHälsningar", kropp)[0].strip()
        stilfynd = sorted({a.kod for a in stil.kontrollera(brodtext).anmarkningar} - FACIT_TILLATNA) if brodtext else ["tomt"]
        amnesfynd = [getattr(a, "kod", str(a)) for a in stil.amne_fynd(str(res.get("subject") or ""), bolag=fall["company_name"], produkt=None)] if res.get("subject") else ["tomt"]
        rader.append({
            "id": fall["id"], "typ": fall.get("typ"), "godkand": all(krit.values()), "kriterier": krit,
            "stilgrind_ok": not stilfynd and not amnesfynd, "stilfynd": stilfynd, "amnesfynd": amnesfynd,
            "signal": bedomning.iris_signal(fall, res), "fel": fel, "latens_s": round(latens, 2),
            "amne": res.get("subject"), "brodtext": brodtext,
        })
        print(f"  iris {fall['id']}: {'OK ' if rader[-1]['godkand'] else 'FEL'} stil={'OK' if rader[-1]['stilgrind_ok'] else stilfynd + amnesfynd} {latens:.0f}s", flush=True)
    return rader


def sammanfatta(rader: list[dict[str, Any]], nycklar: tuple[str, ...]) -> dict[str, Any]:
    n = len(rader) or 1
    ut: dict[str, Any] = {"fall": len(rader), "godkanda": sum(1 for r in rader if r.get("godkand"))}
    for k in nycklar:
        ut[k] = sum(1 for r in rader if r.get(k) or (r.get("kriterier") or {}).get(k))
    lat = sorted(r.get("latens_s") or (r.get("latency_ms", 0) / 1000) for r in rader)
    ut["latens_median_s"] = round(lat[len(lat) // 2], 2) if lat else None
    ut["latens_p90_s"] = round(lat[min(len(lat) - 1, int(n * 0.9))], 2) if lat else None
    return ut


async def main() -> None:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--modell", required=True)
    p.add_argument("--region", required=True)
    p.add_argument("--utkastmodell", default="", help="LEADS_DRAFT_MODEL och LEADS_HUMANIZER_MODEL; tom = --modell")
    p.add_argument("--matning", default="alla", choices=["alla", "support", "golden", "triage", "iris"])
    p.add_argument("--urval", type=int, default=None, help="första N fallen per svit")
    p.add_argument("--iris-urval", type=int, default=10)
    p.add_argument("--etikett", required=True)
    p.add_argument("--tak-kr", type=float, default=150.0)
    p.add_argument("--chattgrans-s", type=float, default=60.0, help="LLM_TIMEOUT_CHATT_S; development kör 60")
    p.add_argument("--nyckelfil", default="", help="servicekontots JSON-fil; tom = GOOGLE_SERVICE_ACCOUNT_JSON i snajp-support/.env")
    args = p.parse_args()
    satt_miljo(args)

    from unittest.mock import patch

    matare = Matare(args.tak_kr)
    matare.installera()
    UT.mkdir(parents=True, exist_ok=True)
    resultat: dict[str, Any] = {
        "etikett": args.etikett, "modell": args.modell, "region": args.region,
        "utkastmodell": args.utkastmodell or args.modell, "start": datetime.now(timezone.utc).isoformat(),
        "matningar": {},
    }

    async def _ingen_inbaddning(_text: str):
        return None

    # Inbäddningarna används inte av MemoryStorage-sökningen; utan dem slipper
    # varje kandidat ett anrop som inte påverkar svaret.
    with patch("app.agent.embeddings.embed_text", new=_ingen_inbaddning):
        planer = {
            "support": (lambda: mat_support(args.urval), ("utfall", "fakta", "inga_fel", "format")),
            "golden": (mat_golden, ()),
            "triage": (lambda: mat_triage(args.urval), ("eskalering_ratt", "fakta", "inga_fel", "format")),
            "iris": (lambda: mat_iris(args.iris_urval), ("levererat", "inga_pahitt", "skrivregler", "stilgrind_ok", "signal")),
        }
        valda = list(planer) if args.matning == "alla" else [args.matning]
        for namn in valda:
            kor, nycklar = planer[namn]
            fore = matare.ogonblick()
            start = time.perf_counter()
            print(f"== {namn} ({args.modell} @ {args.region})", flush=True)
            rader = await kor()
            efter = matare.ogonblick()
            resultat["matningar"][namn] = {
                "sammanfattning": sammanfatta(rader, nycklar), "tid_s": round(time.perf_counter() - start, 1),
                "kr": round(efter["kr"] - fore["kr"], 3), "tokens_efter": efter["per_modell"], "rader": rader,
            }
            fil = UT / f"{args.etikett}.json"
            fil.write_text(json.dumps(resultat, ensure_ascii=False, indent=1), encoding="utf-8")
            print(f"   {namn}: {resultat['matningar'][namn]['sammanfattning']} kr={resultat['matningar'][namn]['kr']}", flush=True)
    resultat["kr_totalt"] = round(matare.kostnad_kr(), 3)
    (UT / f"{args.etikett}.json").write_text(json.dumps(resultat, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"Klart: {UT / (args.etikett + '.json')} ({resultat['kr_totalt']} kr)")


if __name__ == "__main__":
    asyncio.run(main())
