# Handoff till Anton — 2026-09-02: agenterna drar färre anrop, samma kvalitet

**Från:** Claude/Sebbe · **Commit:** `ef9a1af` på `development`, deployad och
liveverifierad · **Migration:** 059 körd mot development FÖRE pushen.

Beställningen (Sebbe): minska agenternas credits/anrop utan kvalitetstapp,
nischa leadssökningen mot kundens val, kräv kontaktperson per lead, låt
supporten svara i stället för att eskalera, ge bokföringsagenten riktlinjer
(bokföring + GDPR), lista vart kunddata skickas, och bygg leads-snabbsöket
("Sök Leads") till höger om testkörningarna.

## 1. Vad som ändrades, per agent

### Leads-agenten — 9 anrop blev 3 för fel bolag, och sökningen nischar

* **Grind efter ICP-steget** (`run_research_step`): ett prospekt som inte
  kvalificerar mot kundens ICP, eller som saknar varje kontaktväg efter
  kontaktuppgraderingen, stoppar efter steg 2. Sex analyssteg
  (konto/konkurrenter/erbjudande) körs aldrig för ett bolag som ändå inte ska
  kontaktas. Kunskapsfångsten körs ÄVEN för stoppade varv — ett
  diskvalificerat prospekt lär mest om var ICP:n går fel. `stopped_early`
  (`ej_kvalificerad`/`kontakt_saknas`) står i jobbresultatet.
* **Utkastfasen grindas på samma villkor**: research_and_draft skrev tidigare
  utkast (4–7 anrop) även åt okvalificerade prospekt. Nu draft_note i stället.
* **Bedömningen persisteras**: `icp_fit`, `qualified`, `disqualifiers` skrivs
  nu på prospektraden (migration 024 skrevs för exakt det här; ingen kodväg
  gjorde det). Prospekten går att sortera på fit i efterhand.
* **Sökprompten bär hela målgruppen**: `_icp_som_text` renderade aldrig
  SNI-koder, regioner (`geo`) eller `exclude_domains` — en kund med ENBART
  SNI-koder fick starta en körning vars sökprompt sa "(ingen malgrupp
  ifylld)" och Gemini letade fritt. Nu nischar sökningen på allt kunden valt.
* **Kontaktkravet**: kontaktväg = nivå i fallbacktrappan ELLER
  contact_email/contact_name/contact_form_url på raden (en rad kunden själv
  kompletterat räknas, PATCH sätter aldrig nivå). Utan kontaktväg: inget
  fortsatt varv, ingen draft, tydlig `contact_missing_reason`. "Processa om"
  efter komplettering passerar grinden.

**Räkneexempel per 10-batch där 4 bolag faller på ICP/kontakt:**
förut 9×10 = 90 researchanrop (+ ev. 4–7×10 utkast), nu 9×6 + 3×4 = 66
(−27 %), och utkastanropen för de fyra försvinner helt.

### Leads-snabbsöket ("Sök Leads") — nytt

* **Backend**: `scope="sok"` på `POST /api/leads/runs/batch` — EN
  Gemini-sökning, bolagen sparas i registret, INGA researchjobb köas. Svar:
  `fase="klar"` med `prospects[]` (bara träffar MED kontaktväg) och
  `utan_kontakt` (räknas, listas inte som leads).
* **Frontend**: `components/leads/LeadsSnabbsok.tsx`, placerad till höger om
  leads-formuläret på `/admin/testkorningar` (ytan stod tom). En rad ("vilka
  kunder, till vilken produkt"), knappen **Sök Leads**, limit 12. Raden läggs
  som `must_have`-override OVANPÅ arbetsytans sparade ICP — ersätter aldrig
  målgruppen. Kostnad per tryck: 1 Gemini-anrop.

### Supportagenten — 6 anrop blev 5 på lyckliga flödet, två motfrågor före eskalering

* **Eskaleringssteget villkorat** (`cs:customer-escalation`, kedjans enda
  thinking-steg): körs bara vid kunskapslucka, säkerhetssignal (påhopp,
  uppsägningsrisk, triageflagga, lågt sentiment, `_KANSLIGT`) eller när
  kunden uttryckligen ber om en människa (ny kodregex `_BER_OM_MANNISKA` —
  den signalen bar tidigare BARA modellsteget). Kodbeslutet OR:ar redan de
  oberoende villkoren; på lyckliga flödet röstade steget alltid "nej".
* **Två motfrågor i stället för en** (`turn_count <= 2`): en kb-lucka på
  varv två ställer EN förtydligande fråga till innan tomheten eskalerar.
  Loopspärren finns kvar på varv tre.
* **Hot/svordomar — verifierat, inte ändrat**: påhoppsgrinden
  (`app/moderation/abuse_gate.py`) är nivåbaserad — frustration och
  svordomar om SITUATIONEN eskalerar aldrig i sig; riktade påhopp får en
  lugn markering + svar; bara `allvarlig` (hot, hat, självskada) avbryter
  och eskalerar. Golden-evals täcker båda riktningarna
  (`hot-avbryter-samtalet`, `irriterad-leverans-ar-inte-uppsagning`).
* **Lärandet (befintligt, oförändrat)**: varje kb-lucka blir ett förslag i
  `agent_suggestions`; ditt godkännande i `/dashboard/larande` skapar
  artikeln och breddar agentens ordförråd — agenten skriver aldrig själv
  (INV-LEARN-001). Ju fler förslag som godkänns, desto färre eskaleringar.

### Bokföringsagenten — instruktionslager + GDPR

* **Chattagenten läser nu det globala instruktionslagret** — den var enda
  LLM-ytan i produkten där en policyändring via admin inte fick någon effekt
  (avläsningen och poleringen läste lagret, chatten körde bara den
  hårdkodade prompten). Kundlagret kräver migration (agent_configs check
  tillåter bara support/leads) — medvetet inte gjort nu.
* **Dataskyddsavsnitt i systemprompten**: andras företags data är
  konfidentiell, andra kunders bokföring syns/bekräftas aldrig, personnummer
  återges aldrig i svar, GDPR-rättigheter hänvisas till människa, radering
  inom arkiveringstiden är förbjuden enligt bokföringslagen.
* **Nytt kunskapsämne** `gdpr_och_bokforing` i `kunskap.py` (7-årsregeln vs
  radering, dataminimering, gallring) — nås via `sla_upp_kunskap`, samma
  versionerade dataväg som momssatserna.
* Bokföringsreglerna i övrigt fanns redan som data (momssatser, K1–K3,
  representation, verifikationskrav, bokföringslagen) och pengarna räknas av
  kod, aldrig av modellen (INV-BOOK-001/002) — oförändrat.

## 2. Vart kunddata skickas — hela listan (verifierad i kod 2026-09-02)

Aktiva mottagare i drift (development/main):

1. **Google Gemini** (`generativelanguage.googleapis.com`) — allt agenterna
   läser/skriver: kundmejl, KB-artiklar, affärskontext, kvittotexter och
   -bilder (vision), embeddings, samt leads-sökningen (som även når **Google
   Search** via grounding med kundens ICP). ⚠️ Fortfarande GRATISNIVÅ med
   delad nyckel — villkoren tillåter Google att använda innehållet;
   `snipe-a1c`/P0.1c står öppen.
2. **ScrapeGraphAI** (`v2-api.scrapegraphai.com`) — prospektens publika
   webbsidor hämtas, tillbaka kommer namn/titlar/arbetsmejl. ⚠️ Stod inte i
   underleverantörslistan förrän nu (tillagd i `lib/bolag.ts` denna commit);
   region och DPA obekräftade — ditt bord.
3. **Resend** (eu-west-1, medvetet EU) — utgående mejl: mottagare + brödtext.
   DPA återstår.
4. **Redis Cloud** (europe-west1, EU-verifierad) — jobbkö/cache/arbetsminne
   med kundmejl och svar, TTL. ⚠️ TLS är AV (`redis://`) —
   `scripts/redis_tls_pa.py --apply` väntar på dig.
5. **Railway Postgres** — själva databasen (region obekräftad i registret).
6. **Gmail SMTP (internlarm)** — eskaleringsnotiser till oss själva:
   tenant + orsak, medvetet ALDRIG ärendetexten.

Konfigurerat men INTE aktivt: OpenAI (ingen nyckel i drift), Supabase (dött
på Railway; lokala dev-miljöer har nycklar kvar), Skatteverket (testbas, inga
nycklar), Cal.com (osatt), Stripe (ingen integration alls — bara testkortens
nummer valideras lokalt). **DeepSeek är hårdspärrad** där riktig kunddata
finns (`llm_provider_fault`, fäller uppstarten). Frontenden har NOLL
klientsides-tredjeparter (fonter självhostade, ingen analytics).

Två upptäckter till ditt bord (ej åtgärdade i kod):
* **Agents-SDK-tracing**: `set_tracing_disabled(True)` körs bara i
  live-grenen av uppstarten; bokföringschatten saknar simuleringsvakt — i
  ett simuleringsläge kunde SDK:ns default-exporter nå OpenAI. Lågt men
  reellt; värt en rad i uppstarten som alltid stänger av tracing.
* **`lib/agent/llm.ts` defaultar till deepseek** utan miljövakt — dess enda
  konsument är en död serveraction, men den borde städas eller vaktas.

## 3. Verifierat

* **1717 backendtester + 386 rotvakter gröna, tsc rent** — inklusive nya
  tester: grinden (okvalificerad stoppar på 3 anrop), persistensen
  (icp_fit på raden), scope=sok (inga researchjobb, kontaktlösa räknas
  separat), villkorad eskalering (människo-begäran väcker steget), två
  motfrågor före eskalering.
* **Live mot deployad development** (`ef9a1af`, auto-deployen fungerar
  igen): se STATUS-posten för smoke-utfallen.
* Kvalitetsargumentet, kort: grindarna tar bort anrop för utfall som ändå
  kasserades (okvalificerade bolag fick aldrig utskick; eskaleringssteget
  röstade alltid nej på lyckliga flödet). Lyckliga flödets kedjor är
  ORÖRDA — samma steg, samma prompts, samma grindar efteråt.

## 4. Parallellspåret (snipe-leads-28) — i samma push

Systersessionen levererade i samma träd (grönt, medcommittat):
INV-JOB-002-jobbliggaren (migration 059 — KÖRD mot development före pushen),
tokenbudget (`app/leads/budget.py`), RESEARCH_V2/OUTREACH_V2-playbooks bakom
env-flagga samt ICP-etiketter i UI. **Körvägen `leads_research_v2.py` var
mitt i skrivning och kommer i deras egen push** — playbookerna refereras
tills dess bara i kommentarer, inget importerar filen.

## 5. Kvar till dig

1. ScrapeGraphAI: DPA/region, PUB-bilagan och registerförteckningen
   (`docs/registerforteckning.md` har den inte heller).
2. Redis-TLS (`redis_tls_pa.py --apply`) och Redis-DPA — oförändrat öppna.
3. Gemini-fakturering/nyckel per miljö (P0.1c, `snipe-a1c`) — oförändrat P0.
4. Bokföringschattens FORBEHALL-text är fortfarande inte människogranskad.
5. Beslut: ska snabbsökpanelen även till kundens `/dashboard/leads`
   (Discovery-sektionen)? Byggd delbar, en rad att montera.
