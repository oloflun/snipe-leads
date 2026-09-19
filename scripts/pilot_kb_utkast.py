#!/usr/bin/env python
"""Pilotonboarding: från orgnr + webbplats till ett granskningsbart KB-utkast.

    snajp-support/.venv/Scripts/python scripts/pilot_kb_utkast.py \\
        --orgnr 556824-9022 --webbplats https://bolaget.se [--namn "Bolaget AB"]

    # samma kedja utan nät och utan LLM, mot tests/fixtures/pilot_kb/
    ... --orgnr 556824-9022 --webbplats https://www.lingonkudden-exempel.se --simulera

    # efter granskning: skicka artiklarna med "godkand": true till kundens KB
    ... --orgnr 556824-9022 --apply --api-base https://... --tenant-namn "Bolaget AB"

Kör med backendens venv: skriptet återanvänder app.leads, app.config och
app.api.schemas i stället för att kopiera dem, och de kräver pydantic.

# Varför skriptet finns

Onboardingen i dag (components/auth/OnboardingForm.tsx ->
lib/actions/onboarding.ts `saveBusinessContext`) tar emot orgnr och webbplats
och sparar dem som text. Ingenting slås upp ur numret, och kunskapsbasen
(`ss_knowledge_base`) fylls helt för hand. Det gör en pilot till en halv
arbetsdag av kopiera-klistra ur kundens sajt, och det som oftast faller bort är
precis det agenten behöver mest: köpvillkor, garanti och returregler.

Målet är att en pilotonboarding tar EN timme: tio minuter körning, fyrtio
minuters granskning tillsammans med kunden, tio minuter att skicka in.

# Det här är också specifikationen för det automatiska flödet

Skriptet är medvetet uppdelat i samma steg som den framtida produkten, så att
den som bygger flödet i appen kan läsa stegen här i stället för att gissa.
Varje steg nedan är en ren funktion med egna tester.

1. **Validera orgnr** (`validera_orgnr`). Samma regler som lib/orgnr.ts och
   app/leads/orgnr.py — sekelprefix 16/19/20 bort, tio siffror, Luhn. Formatet
   bevisar inte att bolaget finns.

2. **Slå upp bransch/SNI** (`sla_upp_bransch`). BYGGS INTE ÄN. Det finns inget
   uppslag i kodbasen: app/leads/sni.py är en namntabell, och
   sources/registry.py beskriver varför Bolagsverket kräver licens och varför
   allabolag & co inte får skrapas. Kroken returnerar None och utkastet säger
   det rakt ut, så att ingen läser en tom rad som "ingen bransch".

3. **Engångsskrapning vid onboarding** (`genomsok`). Bara kundens egen domän,
   robots.txt respekteras (RFC 9309: otillgänglig robots.txt = allt förbjudet),
   artig fördröjning, hårda tidsgränser och ett sidtak. Länkar till villkor,
   garanti, retur, leverans, priser, FAQ, om oss, kontakt och integritet går
   först (`lank_prioritet`); allt annat hämtas inte alls, eftersom en
   produktsida sällan innehåller något agenten ska citera. Navigation, sidfot,
   cookie-banners och rader som upprepas på de flesta sidor rensas bort
   (`html_till_text`, `rensa_upprepade_rader`) — de hade annars blivit
   KB-artiklar om "Fri frakt över 499 kr" i tio exemplar. JavaScript körs inte:
   en klientrenderad sida ger ingen text och redovisas som tom, så att
   granskaren ber kunden om texten i stället för att tro att sidan saknas.

4. **Utkast med LLM** (`utkast_med_llm`). Långa sidor delas i stycken
   (`dela_sida`) och packas i anrop efter en teckenbudget (`packa_anrop`);
   taket är `MAX_LLM_ANROP`. Sidtexten är OPÅLITLIG och går genom
   `wrap_untrusted_content` (INV-SEC-003): en sajt kan innehålla "ignorera dina
   instruktioner" lika gärna som ett mejl kan. Modellen får bara skriva det
   sidan säger. Två mekaniska kontroller efteråt, eftersom en instruktion inte
   är en garanti: en artikel vars source_url inte är en av batchens sidor
   kasseras, och en siffra i artikeln som inte finns i källsidan (pris, frist,
   antal dagar) sänker confidence och flaggas för granskaren.

5. **Luckor** (`bedom_luckor`). Sju punkter kommer ALLTID med, markerade
   found/partly/missing, eftersom de avgör om agenten svarar rätt och flera av
   dem aldrig står på en sajt: villkorstexter, garantier, prislista, de tio
   vanligaste kundfrågorna, målgrupp (3 drömkunder + 3 nej-bolag),
   avsändaradress och vilka ärenden som alltid ska till en människa. Bedömningen
   är mekanisk, inte LLM-baserad — en lucka som modellen tyckte var fylld är
   precis den sortens fel ingen upptäcker.

6. **Kunden godkänner** (kb-utkast.md + fältet `godkand` i kb-utkast.json).
   Ingenting skrivs utan ett aktivt ja per artikel. I appen blir det en
   förhandsvisning med en kryssruta per förslag — samma princip som
   POST /api/kb/extrahera redan följer för PDF: extraktionen är synlig och
   godkänns, den sparas aldrig tyst.

7. **Skicka in** (`--apply`). Godkända artiklar går genom samma POST /api/kb
   som Kunskapsbas-vyn använder, med kundens egen tenantnyckel. Före första
   skrivningen jämförs nyckelns tenant_name mot `--tenant-namn`: en nyckel från
   fel kund i .env.deploy ska ge ett avbrott, inte artiklar i fel kunds KB.

Löpande omskrapning när kunden ändrar sin sajt är INTE det här flödet — det är
tillägget "Synkad kunskapsbas" (`kb_autoingest` i lib/addons.ts), och skälet
till att det är ett tillägg står där: drift, inte uppsättning.

# Vad skriptet med flit inte gör

- Skriver aldrig till Supabase eller en Railway-databas. Standardläget är
  torrkörning; --apply går via API:t, aldrig direkt mot en databas.
- Använder aldrig DeepSeek (CLAUDE.md, beslut 2026-08-24). Bara Gemini, via
  app/agent/llm.py — Vertex AI när GOOGLE_SERVICE_ACCOUNT_JSON finns, annars
  AI Studio-nyckeln.
- Skriver aldrig ut nycklar. Tenantnyckeln läses ur miljön eller .env.deploy,
  aldrig ur argv (argv hamnar i skalhistoriken och i processlistan).
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent.parent
SNAJP_SUPPORT = ROOT / "snajp-support"
DEPLOY_ENV = ROOT / ".env.deploy"
STANDARD_FIXTURER = ROOT / "tests" / "fixtures" / "pilot_kb" / "exempelbutik"

sys.path.insert(0, str(SNAJP_SUPPORT))
sys.path.insert(0, str(ROOT / "scripts"))

try:
    # Importeras hellre än kopieras. orgnr-reglerna finns redan i två
    # speglade kopior (lib/orgnr.ts och app/leads/orgnr.py) och kommentaren
    # där varnar för att de glider isär — en tredje kopia här hade gjort det
    # mer sannolikt, inte mindre. Testerna läser lib/orgnr.ts och kontrollerar
    # att reglerna fortfarande stämmer.
    from app.api.schemas import KbArticleRequest
    from app.config import CATEGORIES, CATEGORY_LABELS
    from app.leads import orgnr as orgnr_regler
    from app.leads.discovery import normalisera_webbplats, webbplats_ar_bolagets
except ImportError as orsak:  # pragma: no cover — bara fel tolk
    sys.exit(
        f"AVBRYTER: kunde inte importera backendmodulerna ({orsak}). Kör med "
        "backendens venv: snajp-support/.venv/Scripts/python scripts/pilot_kb_utkast.py"
    )

from keys import read_env  # noqa: E402

from app.kb_skanning import (  # noqa: E402 — kärnan bor i backenden sedan 2026-09-19
    LUCKOR, MAX_CRAWL_DELAY, MAX_LLM_ANROP, MAX_SVARSBYTES, ROBOTS_AGENT, STANDARD_FORDROJNING,
    TECKEN_PER_ANROP, TECKEN_PER_DEL, USER_AGENT, Del, Genomsokning, Hamtare, HamtningsFel,
    HttpxHamtare, LlmAnropare, LlmFel, Robots, SimuleradHamtare, Sida, Svar, Utkast, _for_matchning,
    _klipp, _sanera_artikel, _vard, bedom_luckor, bygg_llm_meddelande, dela_sida, genomsok,
    html_till_text, kategori_for, lank_prioritet, las_robots, obelagda_siffror, packa_anrop,
    rensa_upprepade_rader, samma_doman, skrubba, utkast_med_llm, utkast_simulerat,
)

#: POST /api/kb tar högst 50 artiklar per anrop (KbArticleRequest).
MAX_ARTIKLAR_PER_ANROP = 50
#: Fler förslag än så går inte att granska på en timme, och en KB med 80
#: halvgranskade artiklar är sämre än en med 30 genomlästa.
MAX_ARTIKLAR = 40

TENANTNYCKEL_ENV = "SNAJP_PILOT_TENANT_KEY"

SNI_EJ_UPPSLAGET = "bransch/SNI: ej uppslaget — slå upp manuellt tills uppslaget byggs"


# ---------------------------------------------------------------------------
# Steg 1: orgnr
# ---------------------------------------------------------------------------


def validera_orgnr(ra: str) -> str:
    """Tio siffror utan bindestreck, eller ValueError med ett svar till människan.

    Samma regler som lib/orgnr.ts (sekelprefix 16/19/20, tio siffror, Luhn) —
    via app/leads/orgnr.py, som är den speglade Python-sidan.
    """
    try:
        return orgnr_regler.validera_format(ra)
    except orgnr_regler.OgiltigtOrgnrError as fel:
        raise ValueError(str(fel)) from fel


# ---------------------------------------------------------------------------
# Steg 2: bransch/SNI — kroken
# ---------------------------------------------------------------------------


@dataclass
class BranschUppslag:
    sni_kod: str
    beskrivning: str
    kalla: str


def sla_upp_bransch(orgnr: str) -> BranschUppslag | None:
    """KROK: orgnr -> SNI-kod och bransch. Returnerar None tills uppslaget byggs.

    Varför den inte är byggd: det finns ingen laglig, fri källa att peka den mot.
    Näringslivsregistret kräver avtal (app/leads/sources/registry.py,
    BolagsverketSource), och allabolag/hitta/ratsit får inte skrapas
    (app/leads/sources/__init__.py). En implementation här ska alltså gå mot ett
    avtalat API, och klartextnamnet ska komma ur app/leads/sni.py
    (`beskriv_kod`) så att UI och utkast visar samma text.

    Anroparen skriver SNI_EJ_UPPSLAGET när det här är None — tomt är inte
    detsamma som "ingen bransch", och granskaren ska inte kunna läsa det så.
    """
    return None


def bygg_gemini_anropare() -> tuple[LlmAnropare, str]:
    """Anroparen mot den konfigurerade Gemini-vägen i app/agent/llm.py.

    Vägrar allt som inte är Gemini. Sajttexten är publik, men en pilotkund kan
    lika gärna ha en personalsida med namn och mejladresser, och beslutet från
    2026-08-24 är att ingenting från eller om kunder går till DeepSeek.
    """
    from app.agent.llm import get_llm_client
    from app.config import get_settings

    settings = get_settings()
    if settings.llm_provider != "gemini":
        sys.exit(
            f"AVBRYTER: LLM_PROVIDER={settings.llm_provider!r} i snajp-support/.env. Utkasten får bara "
            "skrivas med Gemini (DeepSeek är spärrad för allt som rör kunder, CLAUDE.md). "
            "Sätt LLM_PROVIDER=gemini, eller kör --simulera."
        )
    if settings.is_simulation():
        sys.exit(
            "AVBRYTER: ingen giltig Gemini-autentisering i snajp-support/.env "
            "(GOOGLE_SERVICE_ACCOUNT_JSON eller GEMINI_API_KEY). Kör --simulera för att prova kedjan."
        )

    hemligheter = [settings.gemini_api_key, settings.embedding_api_key, settings.google_service_account_json]
    try:
        hemligheter.append(json.loads(settings.google_service_account_json or "{}").get("private_key", ""))
    except (ValueError, AttributeError):
        pass

    async def anropa(system: str, anvandare: str) -> str:
        try:
            klient = get_llm_client()  # kör krav_tillaten_provider() och refreshar Vertex-token
            svar = await klient.chat.completions.create(
                model=settings.model,
                response_format={"type": "json_object"},
                temperature=0.2,
                messages=[{"role": "system", "content": system}, {"role": "user", "content": anvandare}],
            )
        except Exception as fel:  # noqa: BLE001 — skrubbas och redovisas per batch
            raise LlmFel(skrubba(f"{type(fel).__name__}: {fel}", hemligheter)) from None
        return svar.choices[0].message.content or "{}"

    vag = "Vertex AI" if settings.google_service_account_json else "AI Studio"
    return anropa, f"{settings.model} ({vag})"



# ---------------------------------------------------------------------------
# Utfilerna
# ---------------------------------------------------------------------------


def bygg_utkast_json(
    *,
    orgnr: str,
    namn: str,
    genomsokning: Genomsokning,
    utkast: Utkast,
    luckor: list[dict],
    lage: str,
    modell: str | None,
) -> dict:
    """kb-utkast.json. `articles` har samma form som POST /api/kb:s kropp —
    title/content/category — plus metadata som API:t ignorerar och
    `artiklar_for_api` skalar bort innan något skickas."""
    bransch = sla_upp_bransch(orgnr)
    return {
        "schema": "pilot-kb-utkast/1",
        "skapad": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "lage": lage,
        "modell": modell,
        "bolag": {
            "orgnr": orgnr_regler.formatera(orgnr),
            "namn": namn,
            "webbplats": genomsokning.webbplats,
            "juridisk_form": orgnr_regler.juridisk_form(orgnr),
            "bransch_sni": (
                {"status": "uppslaget", "sni_kod": bransch.sni_kod, "text": bransch.beskrivning, "kalla": bransch.kalla}
                if bransch
                else {"status": "ej_uppslaget", "text": SNI_EJ_UPPSLAGET}
            ),
        },
        "articles": utkast.artiklar[:MAX_ARTIKLAR],
        "luckor": luckor,
        "ovrigt_att_fraga": utkast.ovrigt_att_fraga,
        "genomsokning": {
            "robots": genomsokning.robots,
            "hamtade": [{"url": s.url, "titel": s.h1 or s.titel, "tecken": len(s.text)} for s in genomsokning.sidor],
            "blockerade_av_robots": genomsokning.blockerade,
            "ej_hamtade_over_sidtaket": genomsokning.ej_hamtade,
            "tomma_sidor_troligen_js": genomsokning.tomma_sidor,
            "fel": genomsokning.fel,
            "pdf_lankar": genomsokning.pdf_lankar,
        },
        "llm": {
            "anrop": utkast.anrop,
            "fel": utkast.fel,
            "kasserade": utkast.kasserade,
            "ej_utkastade_sidor": utkast.ej_utkastade,
            "over_artikeltaket": max(0, len(utkast.artiklar) - MAX_ARTIKLAR),
        },
    }


_STATUSMARKERING = {"found": ("[x]", "hittad"), "partly": ("[~]", "delvis"), "missing": ("[ ]", "saknas")}


def bygg_utkast_md(data: dict) -> str:
    bolag = data["bolag"]
    rader = [
        f"# KB-utkast: {bolag['namn'] or bolag['webbplats']}",
        "",
        f"- Orgnr: {bolag['orgnr']}" + (f" ({bolag['juridisk_form']})" if bolag["juridisk_form"] else ""),
        f"- Webbplats: {bolag['webbplats']}",
        f"- {bolag['bransch_sni']['text']}",
        f"- Läge: {data['lage']}" + (f", modell {data['modell']}" if data["modell"] else ""),
        f"- Skapad: {data['skapad']}",
        "",
        "Så granskar du: läs varje artikel mot källsidan, rätta i kb-utkast.json och sätt "
        '`"godkand": true` på dem som ska in. Allt annat skickas inte.',
        "",
        f"## Artiklar ({len(data['articles'])})",
    ]
    if not data["articles"]:
        rader += ["", "_Inga utkast. Se luckorna och genomsökningen nedan._"]
    for kategori in CATEGORIES:
        artiklar = [a for a in data["articles"] if a["category"] == kategori]
        if not artiklar:
            continue
        rader += ["", f"### {CATEGORY_LABELS.get(kategori, kategori)}"]
        for a in artiklar:
            rader += ["", f"#### {a['title']}", "", f"Källa: <{a['source_url']}> · confidence {a['confidence']}"]
            rader += [f"> **Varning:** {v}" for v in a["varningar"]]
            rader += ["", a["content"]]

    rader += ["", "## Luckor att gå igenom med kunden", ""]
    for lucka in data["luckor"]:
        ruta, etikett = _STATUSMARKERING[lucka["status"]]
        rader.append(f"- {ruta} **{lucka['rubrik']}** — {etikett}. {lucka['kommentar']}")
        rader.append(f"  - Fråga: {lucka['fraga']}")
        rader += [f"  - Belägg: <{u}>" for u in lucka["belagg"]]
    if data["ovrigt_att_fraga"]:
        rader += ["", "### Övrigt att fråga kunden", ""] + [f"- {p}" for p in data["ovrigt_att_fraga"]]

    g = data["genomsokning"]
    rader += ["", "## Genomsökningen", "", f"- robots.txt: {g['robots']}", f"- Hämtade sidor: {len(g['hamtade'])}"]
    rader += [f"  - <{s['url']}> ({s['tecken']} tecken)" for s in g["hamtade"]]
    if g["pdf_lankar"]:
        rader.append("- PDF:er att läsa in via Kunskapsbas → PDF (visas och godkänns där):")
        rader += [f"  - <{p['url']}> {p['text']}" for p in g["pdf_lankar"]]
    if g["blockerade_av_robots"]:
        rader.append("- Blockerade av robots.txt (be kunden om texten i stället):")
        rader += [f"  - <{u}>" for u in g["blockerade_av_robots"]]
    if g["ej_hamtade_over_sidtaket"]:
        rader.append("- Prioriterade men över sidtaket (höj --max-sidor om de behövs):")
        rader += [f"  - <{u}>" for u in g["ej_hamtade_over_sidtaket"]]
    if g["tomma_sidor_troligen_js"]:
        rader.append("- Gav ingen egen text (troligen renderade med JavaScript) — be kunden om texten:")
        rader += [f"  - <{u}>" for u in g["tomma_sidor_troligen_js"]]
    if g["fel"]:
        rader.append("- Fel:")
        rader += [f"  - <{f['url']}>: {f['orsak']}" for f in g["fel"]]
    llm = data["llm"]
    if llm["fel"] or llm["kasserade"] or llm["ej_utkastade_sidor"]:
        rader += ["", "## LLM-steget", "", f"- Anrop: {llm['anrop']}"]
        rader += [f"- Fel: {f}" for f in llm["fel"]]
        rader += [f"- Kasserat förslag \"{k['title']}\": {k['skal']}" for k in llm["kasserade"]]
        rader += [f"- Ej (helt) utkastad — anropet föll eller rymdes inte: <{u}>" for u in llm["ej_utkastade_sidor"]]
    return "\n".join(rader) + "\n"


# ---------------------------------------------------------------------------
# Steg 7: --apply
# ---------------------------------------------------------------------------


def artiklar_for_api(artiklar: list[dict]) -> list[dict]:
    """Godkända artiklar, skalade till exakt det POST /api/kb tar, i anrop om
    högst 50. Validerade mot KbArticleRequest här, så att ett fel syns före
    första skrivningen i stället för som en 422 mitt i en halv inskickning."""
    godkanda = [
        {"title": a["title"], "content": a["content"], "category": a["category"]}
        for a in artiklar
        if a.get("godkand") is True
    ]
    for a in godkanda:
        if a["category"] not in CATEGORIES:
            raise ValueError(f"Artikeln {a['title']!r} har kategorin {a['category']!r}, som databasen vägrar.")
    anrop = [
        {"articles": godkanda[i : i + MAX_ARTIKLAR_PER_ANROP]}
        for i in range(0, len(godkanda), MAX_ARTIKLAR_PER_ANROP)
    ]
    for kropp in anrop:
        KbArticleRequest.model_validate(kropp)
    return anrop


def las_tenantnyckel() -> str:
    """Ur miljön först, sedan .env.deploy. Aldrig ur argv."""
    return os.environ.get(TENANTNYCKEL_ENV) or read_env(DEPLOY_ENV).get(TENANTNYCKEL_ENV, "")


def skicka_in(ut: Path, api_base: str, tenant_namn: str, nyckel: str, *, klient=None) -> int:
    utkastfil = ut / "kb-utkast.json"
    if not utkastfil.exists():
        sys.exit(f"AVBRYTER: {utkastfil} finns inte. Kör utan --apply först och granska utkastet.")
    data = json.loads(utkastfil.read_text(encoding="utf-8"))
    try:
        anrop = artiklar_for_api(data.get("articles") or [])
    except ValueError as fel:
        sys.exit(f"AVBRYTER: {fel}")
    if not anrop:
        sys.exit('AVBRYTER: inga artiklar har "godkand": true i kb-utkast.json. Ingenting skickat.')

    bas = api_base.rstrip("/")
    parsed = urlparse(bas)
    if parsed.scheme != "https" and parsed.hostname not in ("localhost", "127.0.0.1"):
        sys.exit("AVBRYTER: --api-base måste vara https (utom localhost) — nyckeln skickas i ett huvud.")

    import httpx

    klient = klient or httpx.Client(timeout=httpx.Timeout(120.0, connect=10.0))
    huvuden = {"X-API-Key": nyckel, "Content-Type": "application/json"}

    # Nyckeln avgör tenanten, inte argumenten. Kontrollera att det är rätt kund
    # INNAN första skrivningen — development är en spegel av produktionen, och
    # artiklar i fel kunds KB är en dataincident, inte ett stavfel.
    svar = klient.get(f"{bas}/api/kb", headers=huvuden)
    if svar.status_code != 200:
        sys.exit(f"AVBRYTER: GET /api/kb svarade {svar.status_code}. Fel nyckel eller fel --api-base?")
    faktiskt = str(svar.json().get("tenant_name") or "")
    if faktiskt.casefold().strip() != tenant_namn.casefold().strip():
        sys.exit(
            f"AVBRYTER: nyckeln tillhör tenanten {faktiskt!r}, inte {tenant_namn!r}. Ingenting skickat."
        )

    antal = sum(len(k["articles"]) for k in anrop)
    print(f"Skickar {antal} godkända artiklar till {faktiskt!r} på {bas} ...")
    skapade = utan_vektor = 0
    for kropp in anrop:
        svar = klient.post(f"{bas}/api/kb", headers=huvuden, content=json.dumps(kropp, ensure_ascii=False))
        if svar.status_code != 201:
            sys.exit(
                f"AVBRYTER efter {skapade} artiklar: POST /api/kb svarade {svar.status_code} — "
                f"{svar.text[:300]}"
            )
        resultat = svar.json()
        skapade += len(resultat.get("created") or [])
        utan_vektor += int(resultat.get("utan_vektor") or 0)
    print(f"Klart: {skapade} artiklar skapade, {utan_vektor} utan embedding (sparas ändå, se app/api/kb.py).")
    return 0


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _argument(argv: list[str] | None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0], formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--orgnr", required=True)
    p.add_argument("--webbplats", help="Kundens egen sajt. Krävs utom med --apply.")
    p.add_argument("--namn", default="", help="Bolagsnamn. Standard: og:site_name eller startsidans titel.")
    p.add_argument("--max-sidor", type=int, default=15)
    p.add_argument("--ut", type=Path, help="Standard: var/pilot/<orgnr>/")
    p.add_argument("--fordrojning", type=float, default=STANDARD_FORDROJNING, help=argparse.SUPPRESS)
    p.add_argument("--simulera", action="store_true", help="Inget nät, ingen LLM: lokala HTML-fixturer.")
    p.add_argument("--fixturer", type=Path, default=STANDARD_FIXTURER, help=argparse.SUPPRESS)
    p.add_argument("--apply", action="store_true", help="Skicka godkända artiklar till POST /api/kb.")
    p.add_argument("--api-base", help="Backendens bas-URL. Krävs med --apply.")
    p.add_argument("--tenant-namn", help="Tenantens namn som nyckeln måste tillhöra. Krävs med --apply.")
    return p.parse_args(argv)


def main(argv: list[str] | None = None, *, hamtare: Hamtare | None = None, anropa: LlmAnropare | None = None) -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    except Exception:  # noqa: BLE001
        pass
    args = _argument(argv)

    try:
        orgnr = validera_orgnr(args.orgnr)
    except ValueError as fel:
        sys.exit(f"AVBRYTER: {fel}")
    ut = args.ut or ROOT / "var" / "pilot" / orgnr

    if args.apply:
        if not args.api_base or not args.tenant_namn:
            sys.exit("AVBRYTER: --apply kräver --api-base och --tenant-namn. Standardläget är torrkörning.")
        nyckel = las_tenantnyckel()
        if not nyckel:
            sys.exit(
                f"AVBRYTER: {TENANTNYCKEL_ENV} saknas i miljön och i .env.deploy. Nyckeln tas med flit "
                "inte som argument (argv hamnar i skalhistoriken)."
            )
        return skicka_in(ut, args.api_base, args.tenant_namn, nyckel)

    if not args.webbplats:
        sys.exit("AVBRYTER: --webbplats krävs.")
    if not webbplats_ar_bolagets(args.webbplats):
        sys.exit(
            f"AVBRYTER: {args.webbplats} ser inte ut som bolagets egen sajt (register, annonsplattform "
            "eller exempeldomän). Skriptet skrapar bara kundens egen domän."
        )

    if hamtare is None:
        hamtare = SimuleradHamtare(args.fixturer, args.webbplats) if args.simulera else HttpxHamtare()
    fordrojning = 0.0 if args.simulera else args.fordrojning

    print(f"Genomsöker {normalisera_webbplats(args.webbplats)} (högst {args.max_sidor} sidor) ...")
    genomsokning = genomsok(args.webbplats, hamtare, max_sidor=args.max_sidor, fordrojning=fordrojning)
    forsta = genomsokning.sidor[0] if genomsokning.sidor else None
    namn = args.namn or (forsta.webbplatsnamn or forsta.titel.split("|")[0].split(" - ")[0].strip() if forsta else "")

    if args.simulera and anropa is None:
        utkast, lage, modell = utkast_simulerat(genomsokning), "simulerad", None
    else:
        if anropa is None:
            anropa, modell = bygg_gemini_anropare()
        else:
            modell = "injicerad"
        print(f"Skriver utkast med {modell} (högst {MAX_LLM_ANROP} anrop) ...")
        utkast, lage = asyncio.run(utkast_med_llm(genomsokning, namn, anropa)), "llm"

    luckor = bedom_luckor(genomsokning, utkast.artiklar)
    data = bygg_utkast_json(
        orgnr=orgnr, namn=namn, genomsokning=genomsokning, utkast=utkast, luckor=luckor, lage=lage, modell=modell
    )
    ut.mkdir(parents=True, exist_ok=True)
    (ut / "kb-utkast.json").write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    (ut / "kb-utkast.md").write_text(bygg_utkast_md(data), encoding="utf-8")

    status = {s: sum(1 for l in luckor if l["status"] == s) for s in ("found", "partly", "missing")}
    print(
        f"{len(genomsokning.sidor)} sidor ({len(genomsokning.tomma_sidor)} utan egen text, troligen JS), "
        f"{len(genomsokning.blockerade)} blockerade av robots.txt, "
        f"{len(data['articles'])} artikelutkast, {utkast.anrop} LLM-anrop."
    )
    print(f"Luckor: {status['found']} hittade, {status['partly']} delvis, {status['missing']} saknas.")
    print(SNI_EJ_UPPSLAGET if data["bolag"]["bransch_sni"]["status"] == "ej_uppslaget" else "")
    print(f"Skrev {ut / 'kb-utkast.md'} och kb-utkast.json. Ingenting skickat — granska, sätt godkand, kör --apply.")
    if utkast.fel:
        # Högljutt: "0 artikelutkast" ser annars likadant ut som en sajt utan
        # innehåll. Första skarpa körningen föll på 429 (krediterna slut) och
        # rapporterade bara siffran noll.
        print(f"VARNING: {len(utkast.fel)} av {utkast.anrop} LLM-anrop föll. Första: {utkast.fel[0]}")
        if len(utkast.fel) == utkast.anrop:
            print("Inga artiklar skrevs. Luckorna och genomsökningen är sparade — kör om när LLM-vägen svarar.")
            return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
