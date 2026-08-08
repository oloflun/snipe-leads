# Thinking mode: PÅ vs AV — support (skarp körning)

**Körning:** 2026-08-07 · `deepseek-v4-flash` · Nordlys Handel (seedad KB) ·
5 scenarier × 2 lägen × 6–7 skill-steg = **66 skarpa LLM-anrop**
**Rådata:** `docs/live-tests/support-20260807-200723.{json,md}`

> **Leads (research + outreach): körd 2026-08-08, men RESULTATET ÄR OGILTIGT.**
> Se §6 nedan. Denna rapports slutsatser gäller bara support.

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

## 6. Leads: körningen är OGILTIG — leads-agenten kör inte per-steg-vägen

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
