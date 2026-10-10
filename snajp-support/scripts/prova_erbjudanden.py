#!/usr/bin/env python3
"""Provkörning av erbjudandena mot olika kunder (Antons beställning 2026-10-10).

Syntetiska säljare (Snajp med sina tre agenter, en webbyrå, en
redovisningsbyrå, en B2B-städfirma) × syntetiska mottagare (tre branscher,
med och utan namngiven kontakt) × varje erbjudande i katalogen, med
syntetiska villkor per säljare. Utkasten skrivs genom den RIKTIGA vägen
(`run_outreach_draft_v2` mot MemoryStorage, som generera_textkvalitetsprov.py):
skrivstil, erbjudandeblock, faktagrind, humanizer, textkvalitet och köning.

Varje köat utkast prövas sedan med:
- app.textkvalitet.kontrollera
- gissningsgrinden (app/leads/gissnings_gate.py)
- stilkontrollen, och batchkontrollen över varje säljares körning
- ett kort LLM-omdöme (låg temperatur): grammatik- och stavfel ordagrant,
  betyg 1–5 på "låter som en människa skrev det", den mest robotaktiga meningen.

Rapporten hamnar i var/erbjudandeprov-<datum>.md.

INGEN KUNDDATA: allt är påhittat och lagringen är MemoryStorage. DeepSeek är
tillåtet just här (CLAUDE.md, dataskydd); skriptet tömmer DATABASE_URL och
SUPABASE_DB_URL innan något importeras. Nyckeln läses ur miljön eller ur
filen i PROV_ENV_FIL (standard snajp-support/.env) och skrivs aldrig ut.

Körning (från snajp-support/):
    PYTHONPATH=. PYTHONIOENCODING=utf-8 DATABASE_URL= SUPABASE_DB_URL= \\
        python scripts/prova_erbjudanden.py
Valfritt: PROV_KUNDER=snajp,webbyra  PROV_ERBJUDANDEN=riskfri_start  PROV_SAMTIDIGA=6
"""

from __future__ import annotations

import asyncio
import json
import os
import re
import sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

ROT = Path(__file__).resolve().parents[1]  # snajp-support/
REPO = ROT.parent
sys.path.insert(0, str(ROT))

for _namn in ("DATABASE_URL", "SUPABASE_DB_URL"):
    os.environ[_namn] = ""
os.environ["LLM_PROVIDER"] = "deepseek"
os.environ["MODEL"] = os.environ.get("PROV_MODELL", "deepseek-v4-flash")
for _namn in ("LEADS_DRAFT_MODEL", "LEADS_HUMANIZER_MODEL"):
    os.environ.pop(_namn, None)
if not os.environ.get("DEEPSEEK_API_KEY"):
    _fil = Path(os.environ.get("PROV_ENV_FIL") or ROT / ".env")
    for _rad in _fil.read_text(encoding="utf-8-sig").splitlines():
        if _rad.startswith("DEEPSEEK_API_KEY="):
            os.environ["DEEPSEEK_API_KEY"] = _rad.partition("=")[2].strip().strip('"')

from app.agent.leads_research_v2 import run_outreach_draft_v2  # noqa: E402
from app.agent.llm import get_llm_client  # noqa: E402
from app.config import get_settings  # noqa: E402
from app.leads import erbjudanden, stilkontroll  # noqa: E402
from app.leads.gissnings_gate import check_gissningar  # noqa: E402
from app.storage.memory import MemoryStorage  # noqa: E402
from app.textkvalitet import kontrollera  # noqa: E402

#: Säljarna: namn, produktbeskrivning (affärskontext), produkterna och
#: villkoren per erbjudande. Allt påhittat.
KUNDER = {
    "snajp": {
        "namn": "Snajp",
        "affarskontext": (
            "Snajp hyr ut AI-agenter till svenska småföretag. Iris hittar bolag som passar "
            "kundens målgrupp och skriver ett personligt första mejl till varje bolag, som "
            "kunden granskar innan det skickas. Supportagenten svarar på kundmejl grundat i "
            "kundens egen kunskapsbas och lämnar över till en människa när underlaget inte "
            "räcker. Kvittohanteraren plockar upp kvitton ur e-posten och lägger dem klara "
            "för bokföringen. Kunderna är små bolag med få anställda som inte har tid med "
            "administration. Skillnaden mot andra verktyg är att agenterna arbetar i kundens "
            "befintliga e-post och att inget skickas utan att kunden sagt ja."
        ),
        "produkter": [
            {"namn": "Iris", "nytta": "hittar nya kunder och skriver första mejlet till var och en"},
            {"namn": "Supportagent", "nytta": "svarar på kundmejlen utifrån er egen kunskapsbas"},
            {"namn": "Kvittohanterare", "nytta": "plockar upp kvittona ur e-posten och lägger dem klara för bokföringen"},
        ],
        "villkor": {
            "riskfri_start": "Första månaden utan kostnad. Ingen bindningstid, och ni avslutar när ni vill.",
            "se_det_forst": "Vi tar fram tio bolag som passar er med färdiga första mejl, utan kostnad och utan att det binder er till något.",
            "forsta_resultatet": "Har ni inte fått de första 20 granskade utkasten inom 14 dagar betalar ni ingenting för den första månaden, så länge ni har beskrivit er målgrupp i uppstarten.",
            "gjort_at_er": "Vi sätter upp agenten åt er. Ni svarar på några frågor under en halvtimme, sedan sköter vi resten.",
            "ratt_tid": "Före bokslutet vid årsskiftet: kvittona från hela året ligger klara i januari om ni börjar i november.",
            "tva_vagar": "Antingen får ni bara utkasten och skickar dem själva, eller så sköter agenten hela flödet åt er.",
        },
    },
    "webbyra": {
        "namn": "Kustlinje Webb",
        "affarskontext": (
            "Kustlinje Webb är en liten webbyrå i Halmstad som bygger och sköter webbplatser för "
            "lokala företag. Vi gör nya sajter som fungerar i mobilen, laddar snabbt och syns "
            "när någon söker på tjänsten i närområdet. Efter lanseringen sköter vi uppdateringar "
            "och texter så att kunden slipper. Kunderna är hantverkare, butiker och "
            "tjänsteföretag med en gammal eller ingen webbplats."
        ),
        "produkter": [
            {"namn": "Ny webbplats", "nytta": "en sajt som fungerar i mobilen och syns när kunder söker i närområdet"},
            {"namn": "Webbskötsel", "nytta": "uppdateringar och texter sköts åt er varje månad"},
        ],
        "villkor": {
            "riskfri_start": "Ni betalar först när ni har godkänt den färdiga sajten. Ingen handpenning.",
            "se_det_forst": "Vi gör en skiss på er nya startsida utan kostnad. Ni bestämmer sedan om ni vill gå vidare.",
            "forsta_resultatet": "Är sajten inte publicerad inom sex veckor från att vi fått era texter och bilder, sänker vi priset med 20 procent.",
            "gjort_at_er": "Vi skriver texterna och väljer bilderna. Ni behöver avsätta en timme till ett möte.",
            "ratt_tid": "Före vårsäsongen: beställer ni i februari är sajten klar till mars, när kunderna börjar söka.",
            "tva_vagar": "Antingen en enkel sajt på en sida, eller en hel webbplats med skötsel varje månad.",
        },
    },
    "redovisning": {
        "namn": "Siffergården Redovisning",
        "affarskontext": (
            "Siffergården Redovisning är en redovisningsbyrå i Örebro med sex konsulter. Vi sköter "
            "löpande bokföring, löner, moms och bokslut åt små aktiebolag och enskilda firmor. "
            "Kunden har en fast kontaktperson och får en månadsrapport som går att förstå utan "
            "ekonomiutbildning. Vi arbetar digitalt, så kvitton och fakturor skickas in med mobilen."
        ),
        "produkter": [
            {"namn": "Löpande redovisning", "nytta": "bokföring, moms och löner sköts åt er varje månad"},
            {"namn": "Bokslutspaketet", "nytta": "bokslut och årsredovisning klara i tid"},
        ],
        "villkor": {
            "riskfri_start": "De första två månaderna till halva priset. Ingen bindningstid efter det.",
            "se_det_forst": "Vi går igenom er senaste momsdeklaration utan kostnad och säger vad vi skulle göra annorlunda.",
            "forsta_resultatet": "Får ni en förseningsavgift från Skatteverket för något vi ansvarar för, betalar vi den, så länge underlaget kommit in i tid.",
            "gjort_at_er": "Vi flyttar över bokföringen från er nuvarande byrå åt er. Ni skickar bara en fullmakt.",
            "ratt_tid": "Bokslutet för räkenskapsåret som slutar 31 december: anlitar ni oss före 30 november hinner vi med det.",
            "tva_vagar": "Antingen bara bokslutet, eller hela den löpande redovisningen med fast kontaktperson.",
        },
    },
    "stad": {
        "namn": "Blankt Kontorsstäd",
        "affarskontext": (
            "Blankt Kontorsstäd städar kontor, butiker och mottagningar i Uppsala. Samma städare "
            "kommer varje gång, vi har nycklar och larmkoder i säkert förvar och städar efter "
            "stängning så att verksamheten inte störs. Kunderna är företag med 5 till 50 "
            "anställda som vill slippa tänka på städningen."
        ),
        "produkter": [
            {"namn": "Kontorsstädning", "nytta": "städning efter stängning med samma städare varje gång"},
            {"namn": "Storstädning", "nytta": "fönster, golv och kök en gång per kvartal"},
        ],
        "villkor": {
            "riskfri_start": "Första städningen utan kostnad. Ingen bindningstid, uppsägning med en månads varsel.",
            "se_det_forst": "Vi kommer och tittar på lokalen och lämnar ett fast pris samma vecka, utan kostnad.",
            "forsta_resultatet": "Är ni inte nöjda med en städning kommer vi tillbaka inom 24 timmar och gör om den utan kostnad.",
            "gjort_at_er": "Vi tar med allt material och alla maskiner. Ni lämnar bara en nyckel.",
            "ratt_tid": "Inför julen: bokar ni före 15 november ingår en storstädning i december.",
            "tva_vagar": "Antingen städning varannan vecka, eller varje vecka med storstädning varje kvartal.",
        },
    },
}

#: Mottagarna: bolag, bransch, kontakt (eller None), research och belägg.
MOTTAGARE = [
    {
        "bolag": "Norrbergs Rör AB",
        "mottagare": {"namn": "Lena Norrberg", "roll": "VD"},
        "company_summary": "VVS-firma i Västerås med åtta montörer som gör badrumsrenoveringar och service åt privatpersoner och bostadsrättsföreningar.",
        "likely_pains": ["Offertförfrågningar kommer in via mejl och telefon under arbetsdagen"],
        "trigger_events": ["Söker två nya montörer enligt egen sajt"],
        "citat": ["Vi utför badrumsrenoveringar och VVS-service i hela Västerås", "Vi söker två montörer till vårt team"],
        "lagesbeskrivning": "Norrbergs Rör renoverar badrum och gör VVS-service i Västerås. Bolaget söker två nya montörer, vilket tyder på att efterfrågan växer.",
    },
    {
        "bolag": "Fyrvägens Tandvård AB",
        "mottagare": {"namn": None, "roll": None},
        "company_summary": "Tandvårdsklinik i Linköping med tre tandläkare och två tandhygienister.",
        "likely_pains": ["Patienter bokar och avbokar via telefon och mejl"],
        "trigger_events": ["Har öppnat en andra behandlingsavdelning i år"],
        "citat": ["Vi har öppnat en ny avdelning med två behandlingsrum", "Boka tid via telefon eller mejl"],
        "lagesbeskrivning": "Fyrvägens Tandvård är en klinik i Linköping som byggt ut med en andra avdelning. Bokningen sker via telefon och mejl.",
    },
    {
        "bolag": "Ekholms Maskinuthyrning AB",
        "mottagare": {"namn": "Jonas Ekholm", "roll": "ägare"},
        "company_summary": "Hyr ut grävmaskiner, hjullastare och liftar till byggföretag i Gävleborg.",
        "likely_pains": ["Bokningar och förfrågningar hanteras av ägaren själv"],
        "trigger_events": ["Har köpt in tre nya liftar"],
        "citat": ["Vi hyr ut grävmaskiner, hjullastare och liftar i hela Gävleborg", "Nu har vi tre nya liftar i parken"],
        "lagesbeskrivning": "Ekholms Maskinuthyrning hyr ut maskiner till byggföretag i Gävleborg och har nyligen utökat med tre liftar.",
    },
]

_DOMARPROMPT = (
    "Du är en noggrann svensk korrekturläsare och copywriter. Läs mejlet och svara med JSON:\n"
    '{"grammatikfel": [lista med varje grammatik-, stav- eller skiljeteckenfel, ORDAGRANT citerat ur '
    'mejlet, med rättningen efter " -> "; tom lista om inga], '
    '"betyg": heltal 1-5 där 5 = låter helt som en kunnig människa skrev det och 1 = uppenbart AI- eller robotskrivet, '
    '"robotaktig_mening": den mening som låter mest maskinskriven, ordagrant, eller null, '
    '"kommentar": en mening om vad som drar ner intrycket}.\n'
    "Räkna bara verkliga fel. Ett stilval är inget grammatikfel, och produkt- och "
    "företagsnamn skrivs med flit som säljaren skriver dem (\"Vår Supportagent\", "
    "\"Kvittohanteraren\")."
)


async def _omdome(amne: str, brodtext: str) -> dict:
    settings = get_settings()
    svar = await get_llm_client().chat.completions.create(
        model=settings.model,
        response_format={"type": "json_object"},
        temperature=0.1,
        messages=[
            {"role": "system", "content": _DOMARPROMPT},
            {"role": "user", "content": f"Ämne: {amne}\n\n{brodtext}"},
        ],
    )
    try:
        data = json.loads(svar.choices[0].message.content or "{}")
    except ValueError:
        return {"grammatikfel": [], "betyg": None, "robotaktig_mening": None, "kommentar": "omdömet gick inte att läsa"}
    return data if isinstance(data, dict) else {}


async def _ett_utkast(kund_id: str, nyckel: str, mottagare: dict) -> dict:
    kund = KUNDER[kund_id]
    tenant = f"prov-{kund_id}"
    storage = MemoryStorage()
    await storage.save_context_doc(tenant, kind="product_marketing", content=kund["affarskontext"], source="prov")
    await storage.set_agent_settings(
        tenant,
        agent_type="leads",
        settings={"erbjudanden": {"aktiva": [{"nyckel": nyckel, "vikt": 1}], "villkor": {nyckel: kund["villkor"][nyckel]}}},
    )
    prospekt = await storage.create_prospect(tenant, company_name=mottagare["bolag"])
    trad = await storage.ensure_outreach_thread(tenant, prospect_id=prospekt["id"])
    # Produkten: den första som passar mottagarens vardag; för provet räcker
    # en rotation så att alla produkter förekommer.
    produkt = kund["produkter"][MOTTAGARE.index(mottagare) % len(kund["produkter"])]
    sammanfattning = json.dumps(
        {k: mottagare[k] for k in ("company_summary", "likely_pains", "trigger_events", "citat", "lagesbeskrivning", "mottagare")}
        | {"vald_produkt": produkt},
        ensure_ascii=False,
    )
    resultat = {"kund": kund_id, "nyckel": nyckel, "bolag": mottagare["bolag"], "villkor": kund["villkor"][nyckel]}
    try:
        utkast = await run_outreach_draft_v2(
            storage,
            tenant,
            thread_id=trad["id"],
            prospect_email="kontakt@example.se",
            tenant_name=kund["namn"],
            company_name=mottagare["bolag"],
            offer_summary=f"{produkt['namn']}: {produkt['nytta']}",
            context_pack=f"## Kontextpaket\n{kund['affarskontext']}",
            brief="",
            research_summary=sammanfattning,
            research_evidence=tuple(mottagare["citat"] + mottagare["likely_pains"] + mottagare["trigger_events"]),
            is_test=True,
        )
    except Exception as fel:  # noqa: BLE001 — provkörning: rapportera och gå vidare
        return resultat | {"fel": f"{type(fel).__name__}: {fel}"}
    meddelanden = storage.outreach_messages.get(tenant, [])
    if not utkast.get("queued") or not meddelanden:
        return resultat | {"fel": f"inte köat: {utkast.get('escalation_reason')}"}
    meddelande = meddelanden[-1]
    post = storage.send_queue[tenant][-1]
    resultat |= {
        "amne": meddelande.get("subject") or "",
        "brodtext": meddelande["body"],
        "held": (post.get("gate_checks") or {}).get("held"),
        "faktagrind": utkast.get("grounding"),
    }
    resultat["textkvalitet"] = [a.beskrivning for a in kontrollera(meddelande["body"]).allvarliga]
    resultat["gissningar"] = list(check_gissningar(meddelande["body"]))
    resultat["stil"] = [a.beskrivning for a in stilkontroll.kontrollera(meddelande["body"]).anmarkningar]
    try:
        resultat["omdome"] = await _omdome(resultat["amne"], meddelande["body"])
    except Exception as fel:  # noqa: BLE001
        resultat["omdome"] = {"grammatikfel": [], "betyg": None, "kommentar": f"omdömet föll: {fel}"}
    return resultat


def _rapport(rader: list[dict]) -> str:
    ut = [
        f"# Erbjudandeprov {date.today().isoformat()}\n",
        f"Modell: {get_settings().llm_provider}:{get_settings().model}. Syntetiska säljare och mottagare, "
        "riktig utkastväg (run_outreach_draft_v2 mot MemoryStorage).\n",
    ]
    per_nyckel: dict[str, list[dict]] = defaultdict(list)
    per_kund: dict[str, list[dict]] = defaultdict(list)
    for r in rader:
        per_nyckel[r["nyckel"]].append(r)
        per_kund[r["kund"]].append(r)

    def summa(grupp: list[dict]) -> str:
        klara = [r for r in grupp if "brodtext" in r]
        betyg = [r["omdome"].get("betyg") for r in klara if isinstance(r["omdome"].get("betyg"), int)]
        gram = sum(len(r["omdome"].get("grammatikfel") or []) for r in klara)
        stil = sum(len(r["stil"]) + len(r.get("batch") or []) for r in klara)
        gissn = sum(len(r["gissningar"]) for r in klara)
        medel = f"{sum(betyg) / len(betyg):.2f}" if betyg else "–"
        return f"| {len(klara)} | {len(grupp) - len(klara)} | {gram} | {stil} | {gissn} | {medel} |"

    huvud = "| | utkast | ej köade | grammatikfel | stilfynd | gissningar | medelbetyg |\n|---|---|---|---|---|---|---|"
    ut.append("## Per erbjudande\n\n" + huvud)
    ut += [f"| {n} {summa(g)}" for n, g in per_nyckel.items()]
    ut.append("\n## Per kund\n\n" + huvud)
    ut += [f"| {KUNDER[k]['namn']} {summa(g)}" for k, g in per_kund.items()]

    stilkoder: dict[str, int] = defaultdict(int)
    for r in rader:
        for s in r.get("stil", []) + r.get("batch", []):
            stilkoder[s.split(":")[1].strip() if ":" in s else s] += 1
    ut.append("\n## Stilfynd efter sort\n")
    ut += [f"- {antal} × {sort}" for sort, antal in sorted(stilkoder.items(), key=lambda x: -x[1])] or ["- inga"]

    # Återkommande formuleringar över hela provet: det en läsare av tio mejl
    # från samma avsändare känner igen som mall.
    texter = [r["brodtext"] for r in rader if "brodtext" in r]
    fragor = Counter(
        next((m for m in stilkontroll._meningar(stilkontroll._brodtext(t)) if m.endswith("?")), "") for t in texter
    )
    uppmaningar = Counter(stilkontroll.uppmaning(t) for t in texter)
    ut.append(f"\n## Återkommande formuleringar ({len(texter)} utkast)\n")
    ut.append(f"- Börjar med \"Hej\": {sum(1 for t in texter if t.lstrip().startswith('Hej'))}")
    ut.append(f"- Har PS: {sum(1 for t in texter if re.search(r'(?m)^PS', t))}")
    ut.append(f"- \"lägga tiden på\": {sum(1 for t in texter if 'lägga tiden på' in t)}")
    ut += [f"- Första frågan {n} ×: {f}" for f, n in fragor.most_common(3) if f]
    ut += [f"- Uppmaningen {n} ×: {u}" for u, n in uppmaningar.most_common(3) if u]

    ut.append("\n## Utkasten\n")
    for r in rader:
        ut.append(f"### {KUNDER[r['kund']]['namn']} · {r['nyckel']} · {r['bolag']}\n")
        ut.append(f"*Villkor:* {r['villkor']}\n")
        if "brodtext" not in r:
            ut.append(f"**EJ KÖAT:** {r.get('fel')}\n")
            continue
        o = r["omdome"]
        ut.append(f"Ämne: {r['amne']}\n\n```\n{r['brodtext']}\n```\n")
        ut.append(f"- Betyg: {o.get('betyg')} · robotaktigast: {o.get('robotaktig_mening')!r} · {o.get('kommentar')}")
        ut.append(f"- Grammatik/stavning: {o.get('grammatikfel') or 'inga'}")
        ut.append(f"- Stil: {r['stil'] + r.get('batch', []) or 'inga'}")
        ut.append(f"- Gissningar: {r['gissningar'] or 'inga'} · Textkvalitet: {r['textkvalitet'] or 'ok'}")
        ut.append(f"- Faktagrind: fired={r['faktagrind'].get('fired')} repaired={r['faktagrind'].get('repaired')} · held: {r['held'] or '–'}\n")
    return "\n".join(ut)


async def main() -> None:
    settings = get_settings()
    if settings.database_url or os.environ.get("SUPABASE_DB_URL"):
        print("AVBRYTER: en databas-URL är satt. Provet körs bara mot MemoryStorage.")
        sys.exit(2)
    if settings.is_simulation():
        print("AVBRYTER: ingen DeepSeek-nyckel hittades.")
        sys.exit(2)
    kunder = [k for k in (os.environ.get("PROV_KUNDER") or ",".join(KUNDER)).split(",") if k]
    nycklar = [n for n in (os.environ.get("PROV_ERBJUDANDEN") or ",".join(erbjudanden.katalog())).split(",") if n]
    grind = asyncio.Semaphore(int(os.environ.get("PROV_SAMTIDIGA", "6")))

    async def med_grind(kund_id, nyckel, mottagare):
        async with grind:
            r = await _ett_utkast(kund_id, nyckel, mottagare)
            print(f"{'ok ' if 'brodtext' in r else 'FEL'} {kund_id:12} {nyckel:18} {mottagare['bolag']}", flush=True)
            return r

    jobb = [med_grind(k, n, m) for k in kunder for n in nycklar for m in MOTTAGARE]
    print(f"Live mot {settings.llm_provider}:{settings.model}, {len(jobb)} utkast.")
    rader = list(await asyncio.gather(*jobb))

    # Batchkontrollen: varje säljares utkast till ANDRA bolag är körningen
    # (samma bolag får sex mejl här bara för att provet täcker alla erbjudanden).
    klara = [r for r in rader if "brodtext" in r]
    for r in klara:
        andra = [a["brodtext"] for a in klara if a["kund"] == r["kund"] and a["bolag"] != r["bolag"]]
        r["batch"] = [a.beskrivning for a in stilkontroll.mot_andra(r["brodtext"], andra)]

    ut = REPO / "var" / f"erbjudandeprov-{date.today().isoformat()}{os.environ.get('PROV_SUFFIX', '')}.md"
    ut.parent.mkdir(exist_ok=True)
    ut.write_bytes(_rapport(rader).encode("utf-8"))
    print(f"Rapport: {ut}")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    asyncio.run(main())
