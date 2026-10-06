# Handoff 2026-10-06 (kväll): bara leads som uppfyller kraven, insyn, kundens yta, dubblettspärr

Plan: `plans/2026-10-06-iris-sanning-malgrupp-instruktioner.md` (fas 0–9, nu med fas 1b och mätresultat inskrivna).
Föregående handoff: `HANDOFF-2026-10-06-IRIS-SANNING-INSTRUKTIONER.md`. Logg: `session-logs/2026-10-06-session-log-4.md`.

## 1. Läget, verifierat

- **Git:** allt pushat till `development` (se sista commit i loggen). Tre sammanslagningar med Sebbe/annan session
  under dagen; vid konflikt vann vårt arbete, inget av hans är struket. `support_agent.py` lagras som **CRLF**
  i git; Sebbes editor gör om den till LF varje gång (lös med trevägssammanslagning på normaliserade kopior,
  se 4. Fällor).
- **Sviten:** backend 2 771 gröna, 4 skippade; rotinvarianter 450 gröna; `tsc` rent (bortsett från kända
  `.next/dev/types/validator.ts`).
- **development (Railway):** migration 099 körd. Koden med fas 1b, 7, 8, 9 och dubblettspärren deployar
  automatiskt efter pushen. **Migration 101 (prompt_lager) och 102 (kundonskemal) är INTE körda någonstans**
  — utan 101 sparas körningar utan lagertexter (loggas, fäller inget); utan 102 faller sparning av kundens
  önskemål på check-constrainten.
- **main:** opåverkad. 096–099 (+ Sebbes 100) väntar på Antons ja; 101–102 tillkommer.
- **Antons ocommittade filer, orörda:** `docs/utkast-*`, `next-env.d.ts`, `package.json`, `strategies.md`,
  `gsap.js`, `smooth-scroll.js`, `session-logs/2026-09-30-session-log.md`.

## 2. Vad som byggdes i dag (efter förra handoffen)

| Commit(s) | Vad | Antons krav / skäl | Verifiering |
|---|---|---|---|
| `30cd4de` | **Fas 1b.** Ett nej på vilket kriterium som helst eller ett ostyrkt måste-krav ger nivå C; ett bolag som faller på leverbarheten sparas som C; `GET /api/leads/prospects` returnerar aldrig C; självmotsägande motivering ("uppfyller inte …") ersätts; Jevs jämförelseklassning körs bara för kvalificerade. Tabellen sorterar nyaste först (`created_at`). | "Leads som uttryckligen inte uppfyller kriterierna ska vara absolut förbjudna", "nyaste alltid överst" | `bedomning.demo()`, `test_inv_leads_exist_001.py` (listan returnerar aldrig C) |
| `1b81517` | **Fas 9:** omindexering av KB-artiklar utan vektor: `POST /api/admin/kb/badda-in` + `scripts/badda_in_kb.py` (torrkörning som standard). Hybridsökningen (RRF) **fanns redan** sedan 2026-08-26 — planen rättad. | Inbäddningarna var trasiga 09-12–10-06 | `tests/api/test_admin_kb_inbaddning.py` |
| `cfe86e0` | **Fas 9:** Iris kalibreras av kundens egna utslag (manuella statusbyten i statusloggen), tre mest lika via inbäddning, i researchens användarmeddelande som opålitligt innehåll. **Inte till Jev** (tredje part, Antons beslut 2026-09-30). | Iris lär sig av dina godkännanden/avvisningar | `tests/leads/test_utslag.py` |
| `07b9fd4`, `c84bca9`, `e351d60` | **Fas 8:** Iris › Inställningar får Produkter och målgrupp (produkter, rangordnade segment, offentlig sektor) och "Era önskemål till Iris"; Inställningar › Regler samma ruta för supportagenten. Önskemål bakas in (förhandsgranskning, historik, Återställ, max 10 sparningar/dygn/agent), läses i användarposition bredvid SOUL även i mejlinkorgen. Migration 102. Förhandsvisning `/forhandsvisning/kundinstallningar`. A11y-granskning: sex HIGH rättade (fokus, ångra, tomt formulär efter fel, kapad feedback). | Fas 8 | INV-SEC-009-test (önskemål aldrig i systemprompten), `test_kundonskemal_api.py`, Playwright 1280/375, fokus mätt 7/7 |
| `cf0ef75` | **Fas 7 (Opus-agent, granskad):** `bygg_systemprompt` → segment teckenidentiska med prompten; spårets 8 000-teckenstak borta, systemlager per hash i `prompt_lager` (migration 101); anrop utanför stegmotorn loggas (bolagssökning med källadresser, Jev, profil, webbrevision); grindutslag i spåret; Admin › Kund › **Underlag och flöde** (flödeskarta ur playbookerna, lagerstapel, källmatris, körningsväljare, KB-prov); spårvyn visar lagerstapeln. | Insynskravet | `tests/agentcore/test_insyn.py` (12), admin-API-test |
| `d3a9907` | **Skillmätningen** (`scripts/mat_skillvarianter.py`, 5 syntetiska fixtures × 3, Vertex gemini-2.5-flash, ~5 kr): noll påhittade case i alla; (a) och (b) gav varsitt påhittat förnamn, (c) inget → **(c) står kvar**. Två grindluckor rättade: hälsningen sätts i kod till VD:ns förnamn eller "Hej," (`app/leads/tilltal.py`), faktagrinden fäller oifyllda mallfält `[..]`/`{..}` (`placeholder`, gäller även supporten). | Fas 4.4 | `test_utkastunderlag.py` |
| `85e9a0c`-serien | **Dubblettspärr Iris ↔ listor:** uteslutningsmängden läses om precis före varje Iris-prospekt (tratten: steg "dubblett") och före listans rader; samma bolag två gånger i en lista stryks. Test simulerar Iris som tar ett bolag mitt under ett listbygge. Fixtures fick unika orgnr (`tests/orgnr_fixtur.py`). | "Se till att det inte slinker igenom dubletter ändå" | `test_upptagna_bolag.py` (12) |
| | `scripts/radera_prospekt.py` (development, en kund, namngivna id:n, torrkörning som standard, en transaktion) | "Ta bort de 9 bolagen" | torrkört: exakt de 9 hittade |

## 3. Kvar, i prioritetsordning

**Antons handgrepp (agenten nekades eller får inte):**
1. **Radera de 9 bolagen i development** — klassificeraren nekade agenten. Kommandot (torrkört, träffar exakt de 9):
   ```
   python scripts/radera_prospekt.py --kund snajp --apply --id d9a3f7a3-4b13-4b25-a218-79d039f26427 --id bb20abe4-4d27-4149-b2d1-2ecc28865ae5 --id de14461a-1a2e-44f1-b860-39046acaa041 --id ceb08116-4d87-4beb-a4c5-ab61f447aa17 --id 0c28ef7e-a9f3-447c-bb23-050ab9fd7f9d --id 32f3098b-29f4-41e2-afab-bde5e0c46712 --id ccde38d1-9d03-4bf1-a331-3a047f427057 --id 58aaa52e-0993-42c8-aaf5-9e1605807032 --id 16a533bc-528f-4f04-9df3-8778fa2a117f
   ```
   (Intermezzon, Yrkeshögskolan Umeå Kommun, IHM Business School, MBD Bygg, BA Bygg i Väst AB, AF Bygg Väst AB,
   Byggmästarna i Göteborg AB, Detaljhandel Design AB, Exempel E-handel AB.) Main gick inte att inventera
   (endpointen finns inte där än).
2. **Återställ development-instruktionerna** (klassificeraren nekade): Admin › Agentinstruktioner › Gemensamt,
   spara en tom version → agenterna läser `agent-core/AGENTS.md` igen. Mallens fem rader gäller fortfarande där.
3. **Migration 101 och 102 mot development:** `python scripts/railway_migrate.py --env development --apply`
   (torrkör först utan `--apply`).
4. **Ja till migrationerna 096–102 mot main**, sedan merge av PR #31. Annars pausar nattspeglingen (schemat skiljer).
5. **Beslut: gallringsperiod för spårets fulltext.** Fas 7 sparar hela användarmeddelandet (kundmejl, bolagsmaterial)
   utan tak. Förslag 30 dagar. Dataskyddsfråga — inget gallras förrän du sagt ett tal.
6. **`snajp_malgrupp.py --env development --apply`** och **`badda_in_kb.py --env development --apply`** — båda
   skriver mot spegeln; kör eller säg till agenten.

**Agentens nästa steg:**
7. Visuell kontroll av fas 7-vyn (Underlag och flöde, spårvyn) i 1440/375 + a11y-audit. Kräver inloggad admin;
   lokalt saknas Postgres, så gör en förhandsvisning med syntetiska svar som för fas 8, eller kontrollera på
   development utan kunddata i bild.
8. Skarpt Iris-prov N=5 som Snajp utan filter på development efter 1–3 (kräver ScrapeGraph-kredit, som är slut;
   21 leads föll utan bedömning vid ombedömningen — kör `scripts/ombedom_leads.py --utan-underlag` efter påfyllning).
9. Husets a11y-skuld: fältkanten `border-ink/15` mäter 1,37:1 mot krav 3:1 i 17 filer — eget pass.
10. `benchmark_leads_kedja.py --modell gemini` är trasig (`gemini-3.6-flash` finns inte på Vertex).

## 4. Fällor

- **`support_agent.py` CRLF/LF:** git-versionen är CRLF; Sebbes commits gör den LF och ger en konflikt över hela
  filen. Lös: normalisera bas/vår/deras till LF, `git merge-file`, skriv tillbaka som CRLF. `sed -i` i Git Bash
  stryker CR — använd Edit.
- **UI-filer får bara skrivas med Write/Edit** (design-gate-hooken nekar sed/heredoc).
- **Migrationsnummer krockar mellan parallella sessioner** — kolla `ls supabase/migrations | tail` före ny fil.
- **Testfixtures med samma orgnr** blir dubbletter för spärren; använd `tests/orgnr_fixtur.orgnr_for`.
- **Browserpanelen ritar inte alltid** — fall tillbaka på Playwright → PNG → Read (skripten i sessionens scratchpad).
- **DeepSeek lokalt bara mot syntetisk data;** mätningar mot riktiga bolag går via Vertex (`LLM_PROVIDER=gemini`).

## 5. Antons instruktioner ordagrant (denna session)

> Läs in dig på nuvarande status av planen. Vad som tillkommit: Leadsagenten genererar leads som den uttryckligen säger inte uppfyller kriterierna på ett eller annat sätt, detta behöver vara absolut förbjudet, både för onödig tokenkonsumption men även hur det ser ut mot kund, presentera endast de leads som uppfyller kraven. Genererade leads hamnar även längre ned eller i mitten av listan, se till att de nyaste alltid hamnar överst. Se till att planen uppdateras med detta, samt agenten ska merga ihop med Sebbes commit, vad som eventuellt tillkommit och se till att våra ändringar prioriteras vid en eventuell konflikt, men bevara så mycket av hans som möjligt, stryk det inte.

> /goal Gör klart återstående faserna från planen från förra sessionen, med tilläggen från denna, fortsätt tills allt är klart och verifierat end to end.

> Du har inte nämnt något om de kvarstående faserna, jag vill att du läser in dig om dessa och bekräftar att du har det fullständiga kontextet från förra sessionsplanen innan du fortsätter: [fas 7, fas 8, rest av fas 9, skillmätningen, inventeringen]

> Ta bort de 9 bolagen, säkerställ även att leadslistor inte genererar samma bolag som Iris, de ska ju få fram olika resultat oavsett, men se till att det inte slinker igenom dubletter ändå

> Börja knyt ihop allt som du gjort det som återstår i en utförlig handofff, pusha allt och kör /conclude
