"""Benchmark: V1-kedjan (9+4 anrop) mot V2-kedjan (1+2 anrop) på samma fixtures.

Mäter det beslutsgrinden i kostnadsplanen kräver innan LEADS_PIPELINE=v2
flippas i drift:

  1. tokens in/ut och kostnad per lead (Haiku-pris faktiskt + extrapolerad
     Gemini flash-kostnad med konstanterna ur lib/admin/halsa.ts)
  2. leadskvalitet: qualified-överensstämmelse mot fixture-facit och att
     kontaktfälten är ORDAGRANT korrekta (kontakten SKA komma ur materialet)
  3. utkastkvalitet: blind parvis A/B-dom (Haiku som domare) + checklista

Modell: claude-haiku-4-5 via en skript-lokal Anthropic-adapter — proxy för
gemini-3.6-flash (samma storleksklass). Adaptern imiterar exakt den yta
step_runner använder (chat.completions.create med response_format=json),
så BÅDA kedjorna körs genom sina RIKTIGA kodvägar (playbooks, grindar,
kontrakt) mot MemoryStorage. Ingen produktionsyta röras: KANDA_PROVIDERS
i config.py utökas inte, adaptern lever bara här.

Körning:

    python scripts/benchmark_leads_kedja.py                 # Haiku, båda kedjorna
    python scripts/benchmark_leads_kedja.py --modell gemini # RIKTIGA modellen
    python scripts/benchmark_leads_kedja.py --kedja v2      # bara V2
    python scripts/benchmark_leads_kedja.py --utan-dom      # hoppa domaren
    python scripts/benchmark_leads_kedja.py --max-fixtures 3

--modell haiku kräver ANTHROPIC_API_KEY (miljön eller snajp-support/.env).
--modell gemini går genom produktionens EGNA LLM-klient (LLM_PROVIDER=gemini,
gemini-3.6-flash, nyckeln ur snajp-support/.env) — det är den mätning
beslutsgrinden faktiskt kräver, men den kostar riktiga ören per anrop.
Datat är syntetiska fixtures mot MemoryStorage — ingen kunddata lämnar
maskinen i något läge.

Utdata: markdown-tabell till stdout + JSON till var/benchmark_leads/.
Haiku är en RIKTNINGSVISARE, inte facit — beslutet att radera V1 ska även
stödjas av 1–2 riktiga Gemini-körningar via scripts/run_live_leads.py med
is_test=True (se planen).
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, patch

import httpx

ROT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROT / "snajp-support"))

FIXTURES = ROT / "snajp-support" / "fixtures" / "leads_benchmark"
UTKATALOG = ROT / "var" / "benchmark_leads"

HAIKU_MODELL = "claude-haiku-4-5"
# Anthropic-listpris för Haiku 4.5 (USD/Mtok) — bara för den faktiska
# körkostnaden i rapporten. Gemini-extrapoleringen är beslutsunderlaget.
HAIKU_USD_IN, HAIKU_USD_UT = 1.00, 5.00
# Spegel av lib/admin/halsa.ts:67 — kr per miljon tokens för gemini flash.
GEMINI_KR_IN, GEMINI_KR_UT = 7.14, 35.71

TENANT = "00000000-0000-4000-a000-00000000be9c"


class HaikuAdapter:
    """OpenAI-kompatibel yta (chat.completions.create) ovanpå Anthropics
    Messages API. Bara det step_runner faktiskt använder."""

    def __init__(self, api_key: str) -> None:
        self._client = httpx.AsyncClient(
            base_url="https://api.anthropic.com",
            headers={"x-api-key": api_key, "anthropic-version": "2023-06-01"},
            timeout=120.0,
        )
        self.tokens_in = 0
        self.tokens_out = 0
        self.anrop = 0
        self.chat = self
        self.completions = self

    async def create(self, *, model, response_format, temperature, messages, **kwargs):
        system = "\n\n".join(m["content"] for m in messages if m["role"] == "system")
        user_msgs = [
            {"role": m["role"], "content": m["content"]}
            for m in messages
            if m["role"] != "system"
        ]
        svar = await self._client.post(
            "/v1/messages",
            json={
                "model": HAIKU_MODELL,
                "max_tokens": 4096,
                "temperature": temperature,
                "system": system
                + "\n\nSvara ENBART med ett giltigt JSON-objekt, ingen annan text.",
                "messages": user_msgs,
            },
        )
        svar.raise_for_status()
        data = svar.json()
        text = "".join(b.get("text", "") for b in data.get("content", []))
        # Haiku kan linda in JSON i ```-staket trots instruktionen.
        text = text.strip()
        if text.startswith("```"):
            text = text.strip("`")
            if text.startswith("json"):
                text = text[4:]
        usage = data.get("usage", {})
        self.tokens_in += usage.get("input_tokens", 0)
        self.tokens_out += usage.get("output_tokens", 0)
        self.anrop += 1

        message = type("M", (), {"content": text.strip()})()
        usage_obj = type(
            "U",
            (),
            {
                "prompt_tokens": usage.get("input_tokens", 0),
                "completion_tokens": usage.get("output_tokens", 0),
                "completion_tokens_details": None,
            },
        )()
        return type(
            "R", (), {"choices": [type("C", (), {"message": message})()], "usage": usage_obj}
        )()

    async def stang(self) -> None:
        await self._client.aclose()


def _las_api_nyckel() -> str:
    nyckel = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if nyckel:
        return nyckel
    env = ROT / "snajp-support" / ".env"
    if env.is_file():
        for rad in env.read_text(encoding="utf-8").splitlines():
            if rad.startswith("ANTHROPIC_API_KEY="):
                return rad.split("=", 1)[1].strip()
    sys.exit("ANTHROPIC_API_KEY saknas (miljön eller snajp-support/.env).")


def _fake_scrape(material: str):
    async def _impl(context, url):
        context.scraped_sources.append({"url": url, "length": len(material)})
        return json.dumps({"content": material}, ensure_ascii=False)

    return AsyncMock(side_effect=_impl)


async def _kor_fixture(
    kedja: str, fixture: dict, adapter: HaikuAdapter | None
) -> dict[str, Any]:
    """adapter=None => gemini-läget: inga patchar på LLM-klienten, produktionens
    egen klient används och tokens läses ur kedjornas egna trace-summor."""
    from app.storage.memory import MemoryStorage

    if kedja == "v2":
        from app.agent.leads_research_v2 import (
            run_outreach_draft_v2 as run_draft,
            run_research_step_v2 as run_research,
        )
    else:
        from app.agent.leads_agent import (
            run_outreach_draft as run_draft,
            run_research_step as run_research,
        )

    storage = MemoryStorage()
    await storage.save_context_doc(
        TENANT, kind="product_marketing", content=fixture["context_pack"], source="benchmark"
    )
    prospect = await storage.create_prospect(
        TENANT,
        company_name=fixture["company_name"],
        profil={"website": fixture["website"]},
    )
    await storage.create_prospect_source(
        TENANT,
        prospect_id=prospect["id"],
        source_url=fixture["website"],
        source_type="company_website",
        lawful_basis="berättigat intresse (B2B)",
    )

    from contextlib import nullcontext

    if adapter is not None:
        in_fore, ut_fore, anrop_fore = adapter.tokens_in, adapter.tokens_out, adapter.anrop
        klientpatch = patch("app.agent.step_runner.get_llm_client", return_value=adapter)
    else:
        in_fore = ut_fore = anrop_fore = 0
        klientpatch = nullcontext()
    with (
        klientpatch,
        patch(
            "app.agent.leads_agent._scrape_registered_source_impl",
            new=_fake_scrape(fixture["material"]),
        ),
    ):
        research = await run_research(
            storage,
            TENANT,
            prospect_id=prospect["id"],
            tenant_name="Snajp",
            context_pack=fixture["context_pack"],
            brief="",
            is_test=True,
        )
        utkast: dict[str, Any] = {}
        rad = await storage.get_prospect(TENANT, prospect["id"]) or {}
        if rad.get("contact_email"):
            thread = await storage.ensure_outreach_thread(TENANT, prospect_id=prospect["id"])
            try:
                utkast = await run_draft(
                    storage,
                    TENANT,
                    thread_id=thread["id"],
                    prospect_email=rad["contact_email"],
                    tenant_name="Snajp",
                    company_name=fixture["company_name"],
                    offer_summary=research.get("offer_summary") or "",
                    context_pack=fixture["context_pack"],
                    brief="",
                    research_summary=research.get("final_output") or "",
                    research_evidence=tuple(research.get("research_evidence") or ()),
                    is_test=True,
                )
            except Exception as fel:  # noqa: BLE001 — ett fällt utkast är ett mätvärde
                utkast = {"fel": f"{type(fel).__name__}: {fel}"}

    facit = fixture["facit"]
    kontakt_ratt = (rad.get("contact_email") or None) == facit.get("contact_email")
    kval = research.get("qualified")
    kval_ratt = None if facit.get("qualified") is None else (bool(kval) == facit["qualified"])

    if adapter is not None:
        anrop = adapter.anrop - anrop_fore
        tokens_in = adapter.tokens_in - in_fore
        tokens_out = adapter.tokens_out - ut_fore
    else:
        # gemini-läget: kedjornas egna trace-summor är mätningen.
        anrop = len(research.get("step_log") or []) + len(utkast.get("step_log") or [])
        tokens_in = int(research.get("tokens_in") or 0) + int(utkast.get("tokens_in") or 0)
        tokens_out = int(research.get("tokens_out") or 0) + int(utkast.get("tokens_out") or 0)

    return {
        "fixture": fixture["company_name"],
        "anrop": anrop,
        "tokens_in": tokens_in,
        "tokens_out": tokens_out,
        "qualified": kval,
        "qualified_ratt": kval_ratt,
        "contact_email": rad.get("contact_email"),
        "contact_ratt": kontakt_ratt,
        "stopped_early": research.get("stopped_early"),
        "utkast_subject": utkast.get("subject"),
        "utkast_body": utkast.get("body"),
        "utkast_koat": utkast.get("queued"),
        "utkast_fel": utkast.get("fel"),
        "grounding_ok": (utkast.get("grounding") or {}).get("ok"),
    }


async def _doma(adapter: HaikuAdapter, fixture_namn: str, a: dict, b: dict) -> dict[str, Any]:
    """Blind parvis dom: A/B slumpas inte (deterministisk ordning V1=A) men
    domaren vet inte vilken kedja som är vilken. Domaranropets tokens bokförs
    separat av anroparen (adapter-instansen är domarens egen)."""
    svar = await adapter.create(
        model=HAIKU_MODELL,
        response_format={"type": "json_object"},
        temperature=0.0,
        messages=[
            {
                "role": "system",
                "content": (
                    "Du bedömer två kalla B2B-mejl på svenska, blint. Returnera JSON: "
                    "vinnare ('A'|'B'|'oavgjort'), motivering (svenska, kort), "
                    "checklista_a och checklista_b (objekt med bool-fälten: "
                    "personaliserat_grundat, inga_ogrundade_pastaenden, ren_text, "
                    "naturlig_svenska, en_tydlig_cta)."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"## Prospekt\n{fixture_namn}\n\n"
                    f"## Mejl A\nÄmne: {a.get('utkast_subject')}\n\n{a.get('utkast_body')}\n\n"
                    f"## Mejl B\nÄmne: {b.get('utkast_subject')}\n\n{b.get('utkast_body')}"
                ),
            },
        ],
    )
    try:
        return json.loads(svar.choices[0].message.content)
    except (TypeError, ValueError):
        return {"vinnare": "oavgjort", "motivering": "Domarsvaret gick inte att tolka."}


def _kostnad(tokens_in: int, tokens_out: int) -> dict[str, float]:
    return {
        "haiku_usd": round(tokens_in / 1e6 * HAIKU_USD_IN + tokens_out / 1e6 * HAIKU_USD_UT, 4),
        "gemini_kr": round(tokens_in / 1e6 * GEMINI_KR_IN + tokens_out / 1e6 * GEMINI_KR_UT, 4),
    }


async def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--kedja", choices=("v1", "v2", "bada"), default="bada")
    parser.add_argument("--modell", choices=("haiku", "gemini"), default="haiku")
    parser.add_argument("--utan-dom", action="store_true")
    parser.add_argument("--max-fixtures", type=int, default=0, help="0 = alla")
    args = parser.parse_args()

    fixtures = [
        json.loads(p.read_text(encoding="utf-8")) for p in sorted(FIXTURES.glob("*.json"))
    ]
    if not fixtures:
        sys.exit(f"Inga fixtures i {FIXTURES}.")
    if args.max_fixtures > 0:
        fixtures = fixtures[: args.max_fixtures]

    if args.modell == "haiku":
        nyckel = _las_api_nyckel()
        # Kodvägarna läser settings.model bara för agent_runs-loggen —
        # anropen går genom adaptern. Deepseek-provider för att slippa
        # llm_provider_fault utan riktiga nycklar (syntetisk data,
        # MemoryStorage — exakt det läge DeepSeek-beslutet tillåter).
        os.environ.setdefault("LLM_PROVIDER", "deepseek")
        os.environ.setdefault("DEEPSEEK_API_KEY", "benchmark-not-a-real-credential-0000")
        koradapter: HaikuAdapter | None = HaikuAdapter(nyckel)
    else:
        # RIKTIGA modellen via produktionens egen klient. Nyckeln läses av
        # Settings ur snajp-support/.env (GEMINI_API_KEY) — echa den aldrig.
        os.environ["LLM_PROVIDER"] = "gemini"
        os.environ["MODEL"] = "gemini-3.6-flash"
        koradapter = None

    from app.config import get_settings

    get_settings.cache_clear()
    if args.modell == "gemini" and not get_settings().gemini_api_key:
        sys.exit("GEMINI_API_KEY saknas i snajp-support/.env — kan inte köra --modell gemini.")

    kedjor = ["v1", "v2"] if args.kedja == "bada" else [args.kedja]
    resultat: dict[str, list[dict[str, Any]]] = {}
    try:
        for kedja in kedjor:
            rader = []
            for fixture in fixtures:
                print(f"[{kedja}] {fixture['company_name']} ...", flush=True)
                rader.append(await _kor_fixture(kedja, fixture, koradapter))
            resultat[kedja] = rader
    finally:
        if koradapter is not None:
            await koradapter.stang()

    domar: list[dict[str, Any]] = []
    domare_tokens = {"in": 0, "ut": 0}
    if not args.utan_dom and len(kedjor) == 2 and args.modell == "haiku":
        domadapter = HaikuAdapter(_las_api_nyckel())
        try:
            for a, b in zip(resultat["v1"], resultat["v2"]):
                if a.get("utkast_body") and b.get("utkast_body"):
                    dom = await _doma(domadapter, a["fixture"], a, b)
                    dom["fixture"] = a["fixture"]
                    dom["A"], dom["B"] = "v1", "v2"
                    domar.append(dom)
        finally:
            domare_tokens = {"in": domadapter.tokens_in, "ut": domadapter.tokens_out}
            await domadapter.stang()
    elif not args.utan_dom and len(kedjor) == 2:
        # gemini-läget: samma dom via produktionens klient.
        from app.agent.llm import get_llm_client

        client = get_llm_client()
        for a, b in zip(resultat["v1"], resultat["v2"]):
            if not (a.get("utkast_body") and b.get("utkast_body")):
                continue
            svar = await client.chat.completions.create(
                model=get_settings().model,
                response_format={"type": "json_object"},
                temperature=0.0,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "Du bedömer två kalla B2B-mejl på svenska, blint. Returnera "
                            "JSON: vinnare ('A'|'B'|'oavgjort'), motivering (kort)."
                        ),
                    },
                    {
                        "role": "user",
                        "content": (
                            f"## Prospekt\n{a['fixture']}\n\n"
                            f"## Mejl A\nÄmne: {a.get('utkast_subject')}\n\n{a.get('utkast_body')}\n\n"
                            f"## Mejl B\nÄmne: {b.get('utkast_subject')}\n\n{b.get('utkast_body')}"
                        ),
                    },
                ],
            )
            usage = getattr(svar, "usage", None)
            if usage:
                domare_tokens["in"] += getattr(usage, "prompt_tokens", 0) or 0
                domare_tokens["ut"] += getattr(usage, "completion_tokens", 0) or 0
            try:
                dom = json.loads(svar.choices[0].message.content or "{}")
            except (TypeError, ValueError):
                dom = {"vinnare": "oavgjort", "motivering": "Domarsvaret gick inte att tolka."}
            dom["fixture"] = a["fixture"]
            dom["A"], dom["B"] = "v1", "v2"
            domar.append(dom)

    # -- Rapport ----------------------------------------------------------
    etikett = "Haiku-proxy" if args.modell == "haiku" else "gemini-3.6-flash (RIKTIG)"
    print(f"\n# Benchmark: leads-kedjan V1 mot V2 ({etikett})\n")
    print("| Kedja | Anrop/lead | Tokens in/lead | Tokens ut/lead | Haiku USD/lead | ~Gemini kr/lead |")
    print("|---|---|---|---|---|---|")
    sammanfattning: dict[str, Any] = {}
    for kedja in kedjor:
        rader = resultat[kedja]
        n = len(rader)
        t_in = sum(r["tokens_in"] for r in rader)
        t_ut = sum(r["tokens_out"] for r in rader)
        anrop = sum(r["anrop"] for r in rader)
        kost = _kostnad(t_in, t_ut)
        sammanfattning[kedja] = {
            "leads": n,
            "anrop_per_lead": round(anrop / n, 1),
            "tokens_in_per_lead": t_in // n,
            "tokens_out_per_lead": t_ut // n,
            "haiku_usd_per_lead": round(kost["haiku_usd"] / n, 4),
            "gemini_kr_per_lead": round(kost["gemini_kr"] / n, 4),
            "kontakt_ratt": sum(1 for r in rader if r["contact_ratt"]),
            "qualified_ratt": sum(1 for r in rader if r["qualified_ratt"]),
            "qualified_bedombara": sum(1 for r in rader if r["qualified_ratt"] is not None),
        }
        s = sammanfattning[kedja]
        print(
            f"| {kedja} | {s['anrop_per_lead']} | {s['tokens_in_per_lead']:,} "
            f"| {s['tokens_out_per_lead']:,} | {s['haiku_usd_per_lead']} "
            f"| **{s['gemini_kr_per_lead']}** |"
        )

    print("\n| Kedja | Kontaktfält ordagrant rätt | Qualified rätt (av bedömbara) |")
    print("|---|---|---|")
    for kedja in kedjor:
        s = sammanfattning[kedja]
        print(
            f"| {kedja} | {s['kontakt_ratt']}/{s['leads']} "
            f"| {s['qualified_ratt']}/{s['qualified_bedombara']} |"
        )

    if domar:
        print("\n## Utkastdomar (blind parvis, A=v1, B=v2)\n")
        for dom in domar:
            print(f"- **{dom['fixture']}**: vinnare {dom.get('vinnare')} — {dom.get('motivering')}")
        print(
            f"\nDomarens egna tokens (bokförs separat): "
            f"{domare_tokens['in']:,} in / {domare_tokens['ut']:,} ut"
        )

    UTKATALOG.mkdir(parents=True, exist_ok=True)
    utfil = UTKATALOG / "senaste.json"
    utfil.write_text(
        json.dumps(
            {
                "sammanfattning": sammanfattning,
                "resultat": resultat,
                "domar": domar,
                "domare_tokens": domare_tokens,
                "modell": HAIKU_MODELL if args.modell == "haiku" else "gemini-3.6-flash",
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"\nJSON: {utfil}")


if __name__ == "__main__":
    asyncio.run(main())
