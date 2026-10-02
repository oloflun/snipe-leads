#!/usr/bin/env python3
"""Genererar skarpa provutkast för textkvalitetsgranskningen (2026-10-03).

Kör de riktiga LLM-vägarna mot SYNTETISKA fixtures (ingen kunddata):
- Iris V2-utkast (run_outreach_draft_v2) x10
- Inkorgens omformulering (forbattra/kortare/personligare) x10 vardera
- Mejltriagens svarsutkast (triage_email_llm) x10

Varje text körs genom app.textkvalitet.kontrollera och skrivs till en
markdownrapport för manuell genomläsning:
    var/textkvalitetsprov-<datum>.md

Nyckeln: den betalda Gemini-nyckeln läses ur .env.deploy och exporteras i
processen UTAN att någonsin skrivas ut (läckagespärren i CLAUDE.md).

Körning (från snajp-support/):
    .venv/Scripts/python.exe scripts/generera_textkvalitetsprov.py
"""

from __future__ import annotations

import asyncio
import os
import sys
from datetime import date
from pathlib import Path

ROT = Path(__file__).resolve().parents[1]  # snajp-support/
REPO = ROT.parent
sys.path.insert(0, str(ROT))


def _las_env_deploy() -> dict[str, str]:
    varden: dict[str, str] = {}
    for rad in (REPO / ".env.deploy").read_text(encoding="utf-8-sig").splitlines():
        rad = rad.strip()
        if not rad or rad.startswith("#") or "=" not in rad:
            continue
        namn, _, varde = rad.partition("=")
        varden[namn.strip()] = varde.strip().strip('"')
    return varden


_nycklar = _las_env_deploy()
os.environ["LLM_PROVIDER"] = "gemini"
#: PROV_ANTAL begränsar antalet prover per kategori (gratisnyckelns kvot).
PROV_ANTAL = int(os.environ.get("PROV_ANTAL", "0")) or None
# Produktionen kör gemini-2.5-flash via Vertex-servicekontot. AI Studio-
# nyckeln (enda vägen lokalt) serverar inte längre 2.5-flash till nya
# konton, så provet får köras på en nyare modell: sätt PROV_MODELL för att
# styra. Prompts, grindar och kvalitetslager är desamma.
os.environ["MODEL"] = os.environ.get("PROV_MODELL", "gemini-2.5-flash")
os.environ["GEMINI_API_KEY"] = _nycklar["RAILWAY_DEVELOPMENT_GEMINI_API_KEY"]
# PROV_NYCKEL=lokal => gratisnyckeln ur snajp-support/.env i stället för
# den betalda ur .env.deploy (t.ex. när förskottskrediten är slut).
if os.environ.get("PROV_NYCKEL") == "lokal":
    for _rad in (ROT / ".env").read_text(encoding="utf-8-sig").splitlines():
        if _rad.startswith("GEMINI_API_KEY="):
            os.environ["GEMINI_API_KEY"] = _rad.partition("=")[2].strip().strip('"')
os.environ.pop("GOOGLE_SERVICE_ACCOUNT_JSON", None)

from app.agent.leads_research_v2 import run_outreach_draft_v2  # noqa: E402
from app.agent.triage import triage_email_llm  # noqa: E402
from app.config import get_settings  # noqa: E402
from app.email_pipeline.omformulering import omformulera_utkast  # noqa: E402
from app.storage.memory import MemoryStorage  # noqa: E402
from app.textkvalitet import kontrollera  # noqa: E402

TENANT = "textkvalitetsprov"

#: Tio syntetiska prospekt: (bolag, research_summary-fras, evidens).
BOLAG = [
    ("Nordform Möbler", "Svensk möbeltillverkare med växande e-handel.",
     ("Fri frakt över 1 000 kr", "Rekryterar två kundtjänstmedarbetare")),
    ("Fjällvind Outdoor", "Friluftsbutik med säsongstoppar vintertid.",
     ("Öppnade butik i Åre i september", "Vanligaste frågan gäller leveranstid")),
    ("Brohav Marin", "Båttillbehör till fritidsskeppare.",
     ("365 dagars öppet köp", "Säsongslager byggs upp inför våren")),
    ("Lindqvist & Söner Bygg", "Byggvaruhandel för proffs.",
     ("Ny webbshop lanserad i år", "Telefonkö på morgnarna enligt egen sajt")),
    ("Sörmlands Teknikservice", "IT-drift för småföretag.",
     ("Erbjuder svarstid under fyra timmar", "Anställer en tredje tekniker")),
    ("Granbacka Trädgård", "Plantskola med postorder.",
     ("Fraktfritt för medlemmar", "Många frågor om leveransfönster på våren")),
    ("Vikström Industri", "Legotillverkning i rostfritt.",
     ("Certifierade enligt ISO 9001", "Utökar med ett andra skift")),
    ("Havsnära Fastighetsservice", "Fastighetsskötsel längs kusten.",
     ("Jour dygnet runt", "Tar över tre nya föreningar i höst")),
    ("Åkerlunds Kontorsmaterial", "Kontorsmaterial till företag.",
     ("Leverans nästa dag i hela landet", "Returfrågor är vanligaste ärendet")),
    ("Stigbergets Cykel", "Cykelbutik med verkstad.",
     ("Verkstaden fullbokad två veckor fram", "Säljer servicepaket per år")),
]

#: Tio svarsutkast som omformuleringsknapparna får arbeta med.
OMFORMULERINGSUTKAST = [
    ("Leveransfråga", "Hej Anna!\n\nTack för din fråga. Din order skickades i går och "
     "beräknas vara framme inom två till tre vardagar. Du får ett spårningsnummer via "
     "mejl när paketet lämnar terminalen.\n\nVänliga hälsningar,\nKundtjänst"),
    ("Retur", "Hej!\n\nDu har 30 dagars öppet köp. Skicka tillbaka varan i "
     "originalförpackningen så återbetalar vi inom fem vardagar efter att returen "
     "nått oss. Returfrakten kostar 49 kr.\n\nVänliga hälsningar,\nKundtjänst"),
    ("Faktura", "Hej Johan!\n\nFakturan förföll den 15:e men vi har förlängt "
     "betaltiden till månadsskiftet. Ingen påminnelseavgift tas ut den här gången.\n\n"
     "Vänliga hälsningar,\nEkonomi"),
    ("Garantiärende", "Hej!\n\nGarantin täcker fabrikationsfel i två år. Beskriv "
     "gärna felet och bifoga en bild så återkommer vi med en åtgärd inom en "
     "vardag.\n\nVänliga hälsningar,\nKundtjänst"),
    ("Öppettider", "Hej Maria!\n\nButiken har öppet vardagar 9–18 och lördagar "
     "10–15. Under midsommarhelgen håller vi stängt.\n\nVänliga hälsningar,\nButiken"),
    ("Reklamation", "Hej!\n\nTråkigt att varan var skadad vid leverans. Vi skickar "
     "en ny utan kostnad och du behöver inte returnera den skadade. Ersättaren går "
     "i väg i morgon.\n\nVänliga hälsningar,\nKundtjänst"),
    ("Abonnemang", "Hej Karin!\n\nDitt abonnemang förnyas den 1 november. Vill du "
     "säga upp det behöver vi din uppsägning senast en månad innan, alltså den "
     "1 oktober.\n\nVänliga hälsningar,\nKundtjänst"),
    ("Teknisk fråga", "Hej!\n\nFelet du beskriver brukar bero på en föråldrad "
     "drivrutin. Uppdatera via vår supportsida, starta om enheten och hör av dig "
     "om problemet kvarstår.\n\nVänliga hälsningar,\nSupport"),
    ("Prisfråga", "Hej Erik!\n\nPriset för servicepaketet är 2 495 kr per år "
     "inklusive moms. I paketet ingår två servicetillfällen och fri felsökning.\n\n"
     "Vänliga hälsningar,\nKundtjänst"),
    ("Orderändring", "Hej!\n\nVi har ändrat leveransadressen enligt ditt önskemål. "
     "Ordern skickas till Storgatan 12 i Uppsala i stället. Allt annat är "
     "oförändrat.\n\nVänliga hälsningar,\nKundtjänst"),
]

#: Tio syntetiska kundmejl för triagen, plus en liten kunskapsbas.
TRIAGE_KB = [
    {"title": "Leveranstider", "content": "Standardleverans tar 2–4 vardagar. "
     "Expressleverans (99 kr) levereras nästa vardag vid beställning före kl 14."},
    {"title": "Returer och öppet köp", "content": "30 dagars öppet köp. Returfrakt "
     "49 kr. Återbetalning inom 5 vardagar efter mottagen retur."},
    {"title": "Garanti", "content": "Två års garanti mot fabrikationsfel. Garantin "
     "omfattar inte slitage eller ovarsam hantering."},
    {"title": "Priser och moms", "content": "Alla priser på sajten anges inklusive "
     "moms. Företagskunder kan få faktura med 30 dagars betaltid."},
]

TRIAGE_MEJL = [
    ("kund1@example.se", "Var är min order?", "Hej! Jag beställde för fem dagar "
     "sedan och har inte fått något. Ordernummer 10234. När kommer den?"),
    ("kund2@example.se", "Retur av byxor", "Hej, byxorna var för små. Hur gör jag "
     "för att skicka tillbaka dem och få pengarna tillbaka?"),
    ("kund3@example.se", "Trasig vid leverans", "Lampan jag köpte var sönder när "
     "paketet kom. Jag är ganska besviken. Vad gör vi nu?"),
    ("kund4@example.se", "Fråga om garanti", "Min maskin har slutat fungera efter "
     "ett år. Täcker garantin det här? Kvitto finns."),
    ("kund5@example.se", "Expressleverans?", "Hej! Om jag beställer i dag före "
     "lunch, kan jag få paketet i morgon? Vad kostar det?"),
    ("kund6@example.se", "Faktura till företag", "Vi vill beställa som företag. "
     "Går det att få faktura i stället för kortbetalning?"),
    ("kund7@example.se", "Ångra köp", "Jag beställde fel färg i går. Kan jag ändra "
     "eller ångra beställningen innan den skickas?"),
    ("kund8@example.se", "Pris på frakt", "Vad kostar frakten till Kiruna? Och "
     "finns det fri frakt över något belopp?"),
    ("kund9@example.se", "Återbetalning dröjer", "Jag skickade tillbaka min retur "
     "för två veckor sedan men har inte fått pengarna. Vad händer?"),
    ("kund10@example.se", "Offert på 20 stycken", "Hej, vi behöver 20 stycken av "
     "er produkt X200 till kontoret. Kan ni ge pris och leveranstid?"),
]


def _bedomning(text: str, sprak: str = "sv") -> tuple[str, str]:
    r = kontrollera(text, sprak=sprak)
    status = "FLAGGAD" if r.kraver_granskning else "ok"
    return status, r.sammanfattning()


async def _iris(rapport: list[str]) -> None:
    rapport.append("\n## Iris — V2-mejlutkast (10 st)\n")
    for namn, sammanfattning, evidens in BOLAG[:PROV_ANTAL]:
        storage = MemoryStorage()
        await storage.save_context_doc(
            TENANT, kind="product_marketing",
            content=(
                "Vi säljer Snajp, en svensk AI-supportagent för småföretag. Den "
                "svarar på kundfrågor grundat i kundens egen kunskapsbas och "
                "eskalerar till människa när underlaget inte räcker. Erbjudande: "
                "pilot på de vanligaste kundfrågorna, utan bindningstid."
            ),
            source="prov",
        )
        prospect = await storage.create_prospect(TENANT, company_name=namn)
        thread = await storage.ensure_outreach_thread(TENANT, prospect_id=prospect["id"])
        try:
            result = await run_outreach_draft_v2(
                storage, TENANT,
                thread_id=thread["id"],
                prospect_email="kontakt@example.se",
                tenant_name="Snajp",
                company_name=namn,
                offer_summary="Pilot på de vanligaste kundfrågorna · 20 minuter?",
                context_pack="## Kontextpaket\nICP: svenska småföretag med kundtjänstfrågor.",
                brief="",
                research_summary=f'{{"company_summary": "{sammanfattning}"}}',
                research_evidence=evidens,
                is_test=True,
            )
        except Exception as fel:  # noqa: BLE001 — provkörning, rapportera och gå vidare
            rapport.append(f"### {namn}\nFEL: {type(fel).__name__}: {fel}\n")
            continue
        meddelanden = storage.outreach_messages.get(TENANT, [])
        if result.get("queued") and meddelanden:
            m = meddelanden[-1]
            status, anm = _bedomning(m["body"])
            rapport.append(
                f"### {namn} — {status}\nÄmne: {m.get('subject', '')}\n\n"
                f"{m['body']}\n\n*Kontroll: {anm}*\n"
            )
        else:
            rapport.append(
                f"### {namn} — ESKALERAT\n{result.get('escalation_reason') or result}\n"
            )


async def _omformulering(rapport: list[str]) -> None:
    for lage in ("forbattra", "kortare", "personligare"):
        rapport.append(f"\n## Omformulering — {lage} (10 st)\n")
        for amne, utkast in OMFORMULERINGSUTKAST[:PROV_ANTAL]:
            try:
                nytt = await omformulera_utkast(
                    lage=lage, content=utkast,
                    email={"subject": amne, "body_text": "(kundens fråga)",
                           "from_name": "Anna Andersson"},
                )
            except Exception as fel:  # noqa: BLE001
                rapport.append(f"### {amne}\nFEL: {type(fel).__name__}: {fel}\n")
                continue
            status, anm = _bedomning(nytt)
            rapport.append(f"### {amne} — {status}\n{nytt}\n\n*Kontroll: {anm}*\n")


async def _triage(rapport: list[str]) -> None:
    rapport.append("\n## Mejltriage — svarsutkast (10 st)\n")
    for avsandare, amne, brodtext in TRIAGE_MEJL[:PROV_ANTAL]:
        try:
            data = await triage_email_llm(
                sender=avsandare, subject=amne, body=brodtext,
                kb_articles=TRIAGE_KB,
                foretagsprofil="Exempelbolaget AB, svensk e-handlare, orgnr 556000-0000.",
            )
        except Exception as fel:  # noqa: BLE001
            rapport.append(f"### {amne}\nFEL: {type(fel).__name__}: {fel}\n")
            continue
        utkast = data.get("draft_reply") or "(tomt)"
        status, anm = _bedomning(utkast)
        rapport.append(
            f"### {amne} — {status} (fack: {data.get('category')}, "
            f"eskalera: {data.get('escalate')})\n{utkast}\n\n*Kontroll: {anm}*\n"
        )


async def main() -> None:
    settings = get_settings()
    if settings.is_simulation():
        print("AVBRYTER: ingen aktiv LLM-nyckel — kontrollen hittade simulering.")
        sys.exit(2)
    print(f"Live mot provider={settings.llm_provider}, modell={settings.model}")

    rapport: list[str] = [
        f"# Textkvalitetsprov {date.today().isoformat()}\n",
        "Skarpa LLM-genererade utkast mot syntetiska fixtures. Varje text har "
        "körts genom app/textkvalitet.kontrollera.\n",
    ]
    await _iris(rapport)
    await _omformulering(rapport)
    await _triage(rapport)

    ut = REPO / "var" / f"textkvalitetsprov-{date.today().isoformat()}.md"
    ut.parent.mkdir(exist_ok=True)
    ut.write_text("\n".join(rapport), encoding="utf-8")
    flaggade = sum(1 for rad in rapport if "— FLAGGAD" in rad)
    totalt = sum(1 for rad in rapport if rad.startswith("### "))
    print(f"Klar: {totalt} prover, {flaggade} flaggade. Rapport: {ut}")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    asyncio.run(main())
