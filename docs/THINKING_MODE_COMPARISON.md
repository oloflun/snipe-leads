# Thinking mode: PÅ vs AV — support (skarp körning)

**Körning:** 2026-08-07 · `deepseek-v4-flash` · Nordlys Handel (seedad KB) ·
5 scenarier × 2 lägen × 6–7 skill-steg = **66 skarpa LLM-anrop**
**Rådata:** `docs/live-tests/support-20260807-200723.{json,md}`

> **Denna rapports slutsatser gäller bara support.**
> Leads-körningen 2026-08-08 var ogiltig (§6); grundorsaken är åtgärdad
> 2026-08-09 (§7) och den giltiga leads-jämförelsen ligger i
> [`LEADS_THINKING_COMPARISON.md`](LEADS_THINKING_COMPARISON.md).

---

## 1. Kostnad — entydig

| Scenario | out-tok AV | out-tok PÅ | reasoning-tok | latens AV | latens PÅ |
| --- | --- | --- | --- | --- | --- |
| S1 neutral fråga | 866 | 9 883 | 9 052 | 16 s | 130 s |
| S2 irriterad leverans | 1 153 | 17 379 | 16 239 | 23 s | 209 s |
| S3 arg + återbetalning | 1 501 | 17 462 | 15 658 | 24 s | 197 s |
| S4 uppsägning/ultimatum | 1 337 | 16 084 | 14 604 | 39 s | 172 s |
| S5 GDPR-radering | 1 119 | 5 988 | 4 989 | 26 s | 75 s |
| **Summa** | **5 976** | **66 796** | **60 542** | **128 s** | **783 s** |

**Thinking kostar ~11× fler output-tokens och ~6× längre latens.**
90 % av output-tokens i PÅ-läget är reasoning som aldrig når kunden.

Vid $0,28/M output-tokens är skillnaden liten i absoluta tal (~$0,017 mot
~$0,0017 för fem ärenden). **Latensen är det verkliga problemet:** 130–209
sekunder per ärende är oanvändbart i en livechatt.

---

## 2. Kvalitet — marginell skillnad, och inte konsekvent till thinkings fördel

Båda lägena klassificerade alla fem ärendena **identiskt** (samma kategori,
samma eskaleringsbeslut). Skill-kedjan kördes i samma ordning i båda.

Skillnaderna som fanns:

**S1 — thinking AV producerade ett vilseledande tillägg.** AV-svaret la till
*"återbetalning sker alltid till samma betalsätt"* — hämtat ur en
retur-artikel som var irrelevant för frågan. PÅ-svaret höll sig kort och
ärligt: *"Du ser alla alternativ i kassan när du beställer."*

**S3 — thinking AV läckte en mallrest.** AV-svaret slutade med den
bokstavliga texten `[Your name]`. PÅ-svaret signerade korrekt.

**S4 — BÅDA läckte mallrester** (`[Kundtjänst]` respektive `[Your name]`).

Slutsats: thinking var marginellt bättre i två av fem fall, men **fixade
inte** grundproblemet i S4. Det går alltså inte att köpa sig ur
formateringsfelen med reasoning.

---

## 3. Två buggar som körningen avslöjade

### 3.1 Mallrester nådde kundsvaret — ÅTGÄRDAD

3 av 10 svar innehöll `[Your name]` eller `[Kundtjänst]` i signaturen. Det
hade skickats till en riktig kund.

`strip_markdown` tog bort `[text](url)`-länkar men lämnade nakna
`[platshållare]`. Åtgärdat med `strip_placeholders` i
`app/agent/tools.py` — en kodgrind, eftersom felet uppträder i båda
thinking-lägena och därför inte är ett modellproblem.
Regressionstest: `tests/agent/test_placeholder_gate.py`.

### 3.2 KB-återvinningen är trasig — DIAGNOS KORRIGERAD 2026-08-07 (efter Gemini-nyckeln)

Ursprunglig hypotes var fel. Vi trodde `GEMINI_API_KEY` saknades → inga
embeddings → fulltext-fallback missar synonymer. **Gemini-nyckeln sattes,
samma sanity-check kördes om, samma sorts fel kvarstod** (nu dessutom en
extra irrelevant träff: *Inloggningsproblem och återställning av lösenord*
för en betalningsfråga).

**Verklig orsak: testharnesset körde mot `MemoryStorage`, vars `search_kb`
tar emot `embedding`-parametern men ALDRIG använder den** — den gör ren
tokenöverlappning (`_tokenize`) oavsett om embeddings finns. "Vilka
betalsätt" och artikeltiteln "Betalningsmetoder vi accepterar" delar noll
gemensamma tokens (olika svenska ordformer) — därför missar sökningen,
100 % oberoende av Gemini-nyckeln.

**Konsekvens för den här rapporten:** kostnads-/latensjämförelsen (avsnitt 1)
står kvar — samma trasiga retrieval drabbade båda thinking-lägena lika, så
den relativa skillnaden är fortfarande giltig. Men **kvalitetsslutsatsen
("grundningsregeln fungerar korrekt") är overifierad mot produktionens
faktiska sökväg** — `PostgresStorage` med riktig pgvector-cosine-likhet är
aldrig testad, eftersom `DATABASE_URL` inte är satt lokalt.

**Nästa steg (uppdaterat):** sätt `DATABASE_URL` (Supabase-anslutning, se
HANDOFF.md om `snajp_app`-rollen), kör samma sanity-check mot
`PostgresStorage`, och jämför `kb_sources`. Det är DÄR embeddings faktiskt
kan göra skillnad — inte i testharnesset som det står idag.

---

## 4. Skill-integritet — grön

Varje skill injicerades i sitt **kompletta** skick i samtliga 66 anrop
(`injected_chars` per steg = `load_full_skill()`-längden):

| Skill | Tecken | Komplett |
| --- | --- | --- |
| `cs:ticket-triage` | 11 234 | JA |
| `cs:customer-research` | 10 206 | JA |
| `cs:draft-response` | 14 543 | JA |
| `cs:customer-escalation` | 11 165 | JA |
| `cs:kb-article` | 12 130 | JA |
| `snajp:retention-conversation` | 12 976 (SKILL.md 7 422 + objektionsbibliotek 5 554) | JA |
| `snajp:humanizer-svenska` | 27 081 | JA |

`snajp:retention-conversation` triggades korrekt i S2, S3, S4 och S5
(7 steg) men inte i S1 (6 steg) — den villkorade klassificeraren fungerar.

---

## 5. Rekommendation (preliminär — support enbart)

**Kör thinking AV i supportflödet tills vidare.** Motivering: identiska
klassificerings- och eskaleringsbeslut, 11× lägre tokenkostnad, 6× lägre
latens, och de kvalitetsfördelar som fanns var små och inkonsekventa.
130–209 sekunder per ärende är dessutom diskvalificerande för livechatt.

**Detta är preliminärt av två skäl:**

1. Jämförelsen gjordes med trasig KB-återvinning. Med fungerande embeddings
   kan bilden ändras — särskilt för `cs:customer-research`, där thinking
   rimligen hjälper mest när det finns riktigt underlag att väga.
2. Ett rimligt slutläge är **per steg**, inte per flöde: thinking PÅ för
   `cs:ticket-triage` och `cs:customer-escalation` (bedömningssteg), AV för
   `snajp:humanizer-svenska` (ren omskrivning). `step_runner` läser i dag
   ett globalt `THINKING_MODE` — att göra det till ett fält på `PlaybookStep`
   är en liten ändring och bör utvärderas.

**Leads-flödet är fortfarande inte utvärderat** — en körning gjordes
2026-08-08 men gav ogiltig data, se §6. Research är det steg där thinking
teoretiskt gör mest nytta (väga källor, dra slutsatser om ett bolag), så
det förblir den intressantaste öppna frågan.

---

## 6. Leads: körningen 2026-08-08 var OGILTIG — ÅTGÄRDAD 2026-08-09

> **Status 2026-08-09:** grundorsaken nedan är rättad. `leads_agent.py` kör
> per-steg via `step_runner.run_step`, och en ny, giltig jämförelse finns i
> [`LEADS_THINKING_COMPARISON.md`](LEADS_THINKING_COMPARISON.md). Avsnittet
> nedan står kvar oförändrat som beskrivning av felet och hur det upptäcktes
> — se §7 för vad som faktiskt ändrades.



**Kört 2026-08-08:** 3 prospekt × 2 tenants × 2 lägen = 12 körningar,
samtliga tekniskt lyckade (`research=OK draft=OK`). Rådata:
`docs/live-tests/leads-20260807-225625.json`.

**Slutsatsen som INTE går att dra:** något om thinking mode.

Första signalen var att latenserna var i praktiken identiska mellan lägena,
och i hälften av fallen *lägre* med thinking PÅ:

| Tenant/prospekt | disabled | enabled |
| --- | --- | --- |
| snajp/Gina Tricot (research) | 48.5 s | 46.4 s |
| snajp/Gina Tricot (draft) | 40.0 s | 28.8 s |
| kunder/Blomsterlandet (research) | 81.4 s | 73.7 s |

I supportflödet var thinking PÅ 6× långsammare. Att skillnaden försvinner
helt är inte ett resultat — det är ett symptom.

**Orsak, verifierad i koden:** `app/agent/leads_agent.py` kör
`Runner.run(...)` (OpenAI Agents SDK:s egen loop) på tre ställen, och rör
aldrig `app/agent/step_runner.run_step`. Därmed:

- `thinking_kwargs()` anropas aldrig → `THINKING_MODE` har **noll effekt**
  på leads-flödet. Båda "lägena" körde identisk konfiguration.
- Inget `step_log`, inga `reasoning_tokens`, inget `thinking_mode`-fält —
  utdatan innehåller bara `scraped_sources`, `skills_used`, `final_output`.
- Ingen `agent_runs`-loggning (G10) för leads.
- Inget utdatakontrakt per steg (Del C p.4).

**Detta är samma arkitekturfel som supportagenten hade före omskrivningen:**
alla skills hopklistrade i en enda agentloop. `skills_used` listar vad som
deklarerats, inte vad modellen faktiskt läste — precis den overifierbarhet
som per-steg-vägen byggdes för att lösa.

**Konsekvens för användarens krav.** Begäran var att "bevaka hur skillsen
anropas" och jämföra "VARJE delmoment". Det är **inte möjligt** med
leads-agentens nuvarande arkitektur. Migrering till `step_runner` är ett
förkrav för en meningsfull leads-jämförelse, inte en förbättring att göra
efteråt.

**Nästa steg (ersätter det tidigare "kör leads-jämförelsen"):**
1. Migrera `leads_agent.py`:s tre `Runner.run`-anrop till per-steg-körning
   via `step_runner.run_step`, precis som `support_agent.py`. Playbookarna
   (`app/leads/*_playbook.py`) finns redan och deklarerar stegen.
2. Verifiera med `--skill-audit` + `step_log.injected_chars` att varje skill
   injiceras komplett per steg.
3. Kör OM jämförelsen. Först då säger den något.

Rådatafilen behålls som bevis för att körningen skedde, men får **inte**
citeras som en thinking-jämförelse.

---

## 7. Migreringen (2026-08-09) — vad som ändrades

`app/agent/leads_agent.py` skrevs om från tre `Runner.run`-anrop till
per-steg-körning, samma arkitektur som `support_agent.py`.

| | Före | Efter |
| --- | --- | --- |
| Fas B research | 1 agentloop, 8 skills i en systemprompt | 8 LLM-anrop, ett per skill |
| Fas C outreach | 1 agentloop, 4 skills i en systemprompt | 4 LLM-anrop, ett per skill |
| `THINKING_MODE` | nådde aldrig API-anropet | `extra_body` per steg, loggat i `step_log.thinking_mode` |
| `agent_runs` (G10) | skrevs aldrig för leads | skrivs per körning, `leads_research` / `leads_outreach` |
| Utdatakontrakt | fanns inte | per steg, ett omförsök, sedan eskalering |
| Skrapning | modellverktyg (`scrape_registered_source`) | **i kod, före steg 1** |
| Köning av utkast | modellverktyg | **i kod**, efter språk- och tidsgrind |

### Skrapningen flyttades till kod — varför

Allowlisten är oförändrad (`_scrape_registered_source_impl` vägrar
fortfarande en URL som inte ligger i `prospect_sources` för just det
prospektet). Skillnaden är att hämtningen nu **alltid** sker. Tidigare
berodde den på att modellen kom ihåg att anropa verktyget — G4 var ett hopp,
inte en kodväg. Samma princip som support: modellen resonerar, koden agerar.

### Fas A (onboarding) migrerades INTE

`run_onboarding_turn` kör fortfarande `Runner.run`. Det är ett
flerturssamtal med kunden, inte en kedja av envägssteg, och per-steg-
kontrakt passar inte den formen. **Konsekvens: Fas A saknar fortfarande
thinking-kontroll, `step_log` och `agent_runs`-loggning.** Det är ett
medvetet val, inte ett förbiseende — men det är en kvarvarande lucka och
ska inte beskrivas som klart.

### En bugg som migreringen avslöjade — ÅTGÄRDAD

ScrapeGraphAI returnerar `results['markdown']['data']` som en **lista** av
sidsegment, inte som en sträng. Koden behandlade den som en sträng, vilket
gav två fel samtidigt:

1. `len(markdown)` blev **1** i stället för ~4 000 → `scraped_sources`
   rapporterade att en (1) tecken hämtats.
2. Innehållet injicerades i prompten som en **Python-listrepr** med literala
   `\n` i stället för radbrytningar — modellen fick hela webbsidan som en
   enda oformaterad rad.

Fixat med `_as_markdown()` i `app/agent/research_tools.py`.
Regressionstest: `tests/agent/test_research_tools.py::
test_markdown_returned_as_a_list_is_joined_not_stringified`.

**Varför testerna inte fångade det:** testmocken (`_fake_scrape_result`)
modellerade fältet som en sträng. Mocken var fel, inte koden — samma
felklass som `MemoryStorage.search_kb` (§3.2). En mock som gissar
API-formatet bevisar bara att koden är konsekvent med gissningen.

### Regressionstestet för själva grundfelet

`tests/agent/test_leads_agent_wiring.py::test_thinking_mode_reaches_the_api_call`
inspekterar de kwargs LLM-klienten **faktiskt fick**, inte vad koden påstår:

- `THINKING_MODE=disabled` → `extra_body={"thinking": {"type": "disabled"}}`
  på alla 8 research-anrop
- `THINKING_MODE=enabled` → inget `extra_body` alls
- `agent_runs.step_log[*].thinking_mode` matchar i båda fallen

Det testet hade fällt hela 2026-08-08-körningen innan den kostade 50 minuter
och 12 meningslösa körningar.

---

## 8. Leads: den GILTIGA jämförelsen (2026-08-09)

**Körning:** Snajps egen tenant × 3 svenska e-handlare (Gina Tricot,
Blomsterlandet, Sportamore) × 2 lägen = 6 fulla pipelinekörningar,
12 skill-steg vardera = **72 skarpa LLM-anrop.**
Fullt rådata, varje stegs kompletta utdata:
[`LEADS_THINKING_COMPARISON.md`](LEADS_THINKING_COMPARISON.md) ·
[`live-tests/leads-20260809-140940.json`](live-tests/leads-20260809-140940.json)

### 8.1 Kostnad

| | AV | PÅ | Faktor |
| --- | --- | --- | --- |
| in-tokens | 466 586 | 397 782 | **0,85×** |
| ut-tokens | 24 108 | 210 395 | **8,7×** |
| reasoning-tokens | 0 | 182 637 | — |
| latens totalt | 303 s | 2 143 s | **7,1×** |
| latens per prospekt | 101 s | 714 s | 1,7 min → 11,9 min |
| omförsök (brutet utdatakontrakt) | **6** | **0** | — |

Två saker är kontraintuitiva och värda att notera:

**PÅ använde FÄRRE input-tokens.** Inte trots utan på grund av kontraktet:
AV bröt utdatakontraktet 6 gånger (`mk:offers` ×2, `sa:draft-outreach` ×2,
`mk:prospecting`, `mk:sales-enablement`) och varje omförsök skickar hela
meddelandekedjan igen — inklusive den fullt injicerade skillen, som för
`mk:offers` är 69 574 tecken. PÅ bröt kontraktet **noll** gånger.

**`reasoning_tokens = 0` i AV-läget** är beviset att toggeln faktiskt biter.
Det var precis det som saknades 2026-08-08.

### 8.2 Kvalitet — lägena fattar OLIKA BESLUT

Detta är den avgörande skillnaden mot supportflödet, där båda lägena
klassificerade alla fem ärendena identiskt.

| Prospekt | icp_fit AV | icp_fit PÅ | Kvalificerad AV | Kvalificerad PÅ |
| --- | --- | --- | --- | --- |
| Gina Tricot | 0,7 | 0,3 | **JA** | **NEJ** |
| Blomsterlandet | 0,85 | 0,5 | **JA** | **NEJ** |
| Sportamore | 0,85 | 0,3 | **JA** | **NEJ** |

Kvalificeringsbeslutet kastades om för **samtliga tre**.

**Det mest talande fyndet ligger i AV-lägets egen motivering.** Om Gina
Tricot skrev AV-läget, ordagrant:

> "De är ett medelstort bolag, inte ett litet SMB, **men fortfarande inom
> målgruppen** 'svenska små och medelstora bolag'. […] Inga tydliga
> disqualifiers hittades."

Det såg alltså avvikelsen mot ICP:t och resonerade sig förbi den i samma
mening. PÅ-läget såg samma faktum och drog motsatt slutsats:

> "dels är de sannolikt en större kedja snarare än ett små- eller medelstort
> bolag, dels är de ett B2C-företag. Snajps produkter är positionerade för
> svenska SMB-bolag och B2B-leads, så Gina Tricot hamnar utanför målgruppen."

Samma mönster i `mk:ab-testing`: AV svarade `offer_confidence = 0,55` för
**alla tre** bolagen — ett rimligt mittenvärde som inte skiljer på fallen.
PÅ differentierade (0,3 / 0,4 / 0,55).

### 8.3 VIKTIG BEGRÄNSNING — datan kan inte skilja träffsäkerhet från pessimism

Alla tre testprospekten är stora B2C-e-handlare, och PÅ underkände alla tre.
Det är konsekvent, men **inget prospekt i testet BORDE ha kvalificerat sig**.
Därför går det inte att avgöra om PÅ är mer träffsäkert eller bara mer
negativt. En modell som säger nej till allt har inte omdöme, den har bias.

**Nödvändigt nästa test innan beslutet låses:** kör om med minst ett prospekt
som otvetydigt matchar Snajps ICP — ett litet/medelstort svenskt bolag med
kundtjänst, gärna ett B2B-bolag. Säger PÅ nej även där är slutsatsen i 8.2
värdelös. Säger PÅ ja är den bekräftad.

### 8.4 Två kundvända fynd som körningen avslöjade

**1. Påhittad statistik nådde ett utkast — INTE åtgärdat i modellen.**
Utkastet till Sportamore (thinking AV) innehöll:

> "En liknande kund har minskat sina återkommande frågor med **30 procent
> inom 30 dagar**."

Snajps kontextpaket innehåller **noll** procentsiffror — verifierat
programmatiskt. Siffran är påhittad, och den hade gått ut i Snajps namn till
en riktig mottagare. 1 av 6 utkast, bara i AV-läget. Ingen kodgrind fångar
detta i dag: `strip_placeholders` tar mallrester, inte ogrundade påståenden.
**Detta är den starkaste enskilda kvalitetsinvändningen mot AV i leadsflödet**
— ett kallt mejl är första intrycket i en kundrelation, och grundningsregeln
är själva säljargumentet.

**2. Hängande signatur i 5 av 6 utkast — ÅTGÄRDAT.**
Utkasten slutade `"Med vänliga hälsningar,"` utan avsändare. Orsaken var inte
en bugg utan en grind som gjorde sitt jobb: modellen skrev `[Signatur]`,
`strip_placeholders` tog bort platshållaren (rätt) och lämnade hälsningen
hängande. Drabbade BÅDA lägena → kodfel, inte modellfel.
Fixat med `sign_off()` i `app/agent/leads_agent.py`, regressionstester i
`tests/agent/test_leads_agent_wiring.py`.

### 8.5 BESLUT 2026-08-10: thinking AV i hela leadsflödet

**Beslutat av användaren efter genomläsning av rådatan** (hela materialet
för Gina Tricot samt samtliga sex färdiga mejlutkast).

**Min rekommendation i en tidigare version av det här avsnittet var PÅ. Den
var fel, och det är värt att skriva ut varför.** Jag drog slutsatsen ur
mätvärden — brutna utdatakontrakt, differentierade konfidenssiffror, en
mer skeptisk ICP-bedömning — och läste dem som kvalitet. Användaren läste
det som modellen faktiskt PRODUCERADE. Det är den enda mätning som räknas
i ett flöde vars output går till en människa.

**Vad genomläsningen visade:**

1. **Utkasten är bättre med AV.** Samtliga tre kändes mer personliga,
   mänskliga, med rätt ton och tillräcklig kontext. PÅ-utkasten blev
   kortfattade, hackiga och robotaktiga trots — eller på grund av — allt
   övertänkande. Exempel: PÅ skrev bara *"i drift hos Livrustning"* utan
   någon förklaring av vad det betyder eller varför det är relevant.
2. **AV hade RÄTT i ICP-bedömningen, inte fel.** B2C-e-handel passar
   supportprodukten mycket bra: hög volym privatkunder med enkla,
   återkommande ärenden är precis den belastning agenten avlastar. PÅ:s
   underkännande av alla tre var inte skärpa — det var det som §8.3
   varnade för, en modell som säger nej till allt.
3. **AV:s research var genuint bra.** Den undersökte om bolagen redan hade
   en chatbotlösning på sajten, och identifierade en öppning via Instagram
   där en stor del av deras kunder faktiskt befinner sig. Den förberedde
   rimliga invändningar och formulerade raka, användbara svar redan i
   researchsteget.

**Alltså: §8.2 ovan ska INTE läsas som att PÅ hade bättre omdöme.** Den
observationen (att AV "resonerade sig förbi" en ICP-avvikelse) står kvar som
beskrivning av vad som skrevs, men tolkningen var min och den var felaktig
— AV:s slutsats var den riktiga, och dess motivering var kortfattad snarare
än slarvig.

**Verkställt i kod, inte bara i det här dokumentet:** varje steg i
`leads/{onboarding,research,outreach}_playbook.py` sätter nu explicit
`thinking="disabled"` via `research_playbook.THINKING`. Det ärvs medvetet
INTE från `settings.thinking_mode` — supportbeslutet ger samma värde i dag,
och ett leadsbeslut som tyst hänger på ett supportbeslut är inget beslut.
Låst av `test_every_leads_step_pins_thinking_disabled` och
`test_leads_runs_thinking_off_even_if_the_global_default_is_on`.

### 8.6 Nästa spår: finjustering via TILLÄGGSINSTRUKTIONER

Riktningen framåt är inte thinking, utan bättre styrning av AV-flödet.

**HÅRD REGEL — vi går inte in och ändrar i skillsen.** Ska output justeras
görs det med tilläggsinstruktioner ovanpå skillen: playbookens `task` och
`case_context`, som är våra egna och fritt redigerbara. Undantag kräver att
det är absolut nödvändigt, och då ska `agent-core/build_manifest.py` köras
i samma commit så att baseline-bytet syns.

Regeln är sedan 2026-08-10 mekanisk, inte en förhoppning:
**INV-SKILL-005** (`tests/invariants/test_inv_skill_005.py`) jämför varje
fil under `agent-core/skills/` mot sitt sha256 i manifestet och fäller
builden på tyst redigering, tillagd fil eller borttagen fil. Verifierat att
grinden faktiskt fäller — en grind som inte kan fela är ingen grind.

**Att utvärdera i kommande tester:** var tilläggsinstruktionerna gör mest
nytta. Kandidater ur den här körningen:

- **`sa:draft-outreach` och `snajp:humanizer-svenska`** — det är här tonen
  avgörs, och det var här PÅ tappade mest. Vad i AV:s utkast som gjorde dem
  personliga bör göras till en explicit instruktion i stället för tur.
- **Grundningskrav på påståenden i utkast.** AV producerade den påhittade
  "30 procent"-siffran (§8.4). En tilläggsinstruktion som kräver att varje
  siffra och varje kundreferens går att peka ut i kontextpaketet är det
  billigaste motmedlet — och på sikt en kodgrind, som `strip_placeholders`.
- **`mk:prospecting`** — bevara AV:s bedömning men be den skriva ut sitt
  resonemang tydligare, så att en människa kan granska varför ett prospekt
  kvalificerades.
