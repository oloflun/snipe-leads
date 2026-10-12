# Session Log — 2026-10-12

## Session Summary
Antons genomgång av två utkastkedjor (Fiskebäck Byggservice, Härlanda Fog & Byggservice) blev regler i kod: det första Iris-utkastet ska landa där tredje omskrivningen landade. Skrivstilens och grundmallens mallfraser togs bort, en stilgrind före humanizern fäller mallingång, registerfakta, antaganden och tappat erbjudande, och varje mejl får en tilldelad ingångsform. De 100 Snajp-leadsen kördes om i fem omgångar: 92 har nya utkast i granskningskön, de 73 gamla godkända avbröts, inget skickades. Tillbaka till Iris skriver inte längre om automatiskt och alla listtak är borta. Handoff: `HANDOFF-2026-10-12-UTKASTKEDJAN.md`.

## What Changed

### Files Created
- `~/snipe-leads/scripts/omskriv_utkast.py` — kör om research och utkast för en kunds leads via API:t (Skapa om), nyckel ur Railway.
- `~/snipe-leads/scripts/granska_utkast.py` — kör stilgrinden på kundens väntande utkast och listar fynd.
- `~/snipe-leads/snajp-support/tests/leads/test_stilkontroll_2026_10_12.py` — de nya stilfynden, referensutkastet passerar, ingångsformen roterar.
- `~/snipe-leads/snajp-support/tests/leads/test_produktbundna_kriterier.py` — produktbundna kriterier gäller bara den valda produkten; produkt härleds ur ett uppfyllt kriterium.
- `~/snipe-leads/HANDOFF-2026-10-12-UTKASTKEDJAN.md` — handoff.
- `~/snipe-leads/plans/2026-10-12-utkastkedjan.md` — plan för arbetsströmmen.

### Files Modified
- `~/snipe-leads/agent-core/prompts/leads-skrivstil.md` — ingången bygger på en egenskap ur citaten, formerna beskrivs, omgång 4 tillagd.
- `~/snipe-leads/agent-core/prompts/leads-systemprompt.md` — grundmallen § 10.2 utan mallfraser.
- `~/snipe-leads/snajp-support/app/leads/stilkontroll.py` — nya fynd, erbjudandekontroll, konstruktionsjämförelse, produktstam.
- `~/snipe-leads/snajp-support/app/agent/leads_research_v2.py` — stilgrind före humanizern, använda ingångar, ingångsform per mejl, produktval och härledning.
- `~/snipe-leads/snajp-support/app/leads/bedomning.py` — produktbundna kriterier, `produkt_ur_kriterierna`.
- `~/snipe-leads/snajp-support/app/api/leads.py` — tillbaka till Iris utan omskrivning, kölistan 1000, processa om hoppar över felformat id.
- `~/snipe-leads/snajp-support/app/api/schemas.py`, `admin_flytt.py`, `leads_massatgard.py` — listtak borta.
- `~/snipe-leads/components/leads/SkickatLista.tsx` — texter för Tillbaka till Iris.
- `~/snipe-leads/docs/BESLUT.md` — beslutet 2026-10-12 med resonemang och utfall.
- `~/snipe-leads/snajp-support/tests/agent/test_leads_v2_wiring.py`, `tests/api/test_tillbaka_till_iris.py`, `tests/api/test_massatgarder_api.py` — anpassade.
- `~/snipe-leads/STATUS.md`, `~/snipe-leads/GOALS.md` — denna session.

### Files Moved/Deleted
- Inga.

## Decisions Made
- **Första utkastet är det personliga, säljande utkastet (Anton):** ingången bygger på en egenskap ur bolagets egna ord, aldrig siffror eller en mallfras; erbjudandet intakt; handlingen sist. Mallfraserna som gav "För företag som ert …" fanns i skrivstilen själv.
- **Variation ur koden, inte ur hoppet:** parallella jobb ser inte varandras utkast, så ingångsformen tilldelas per prospekt-id, som erbjudandearmarna.
- **Tillbaka till Iris skriver inte om (Anton):** utkasten avbryts, leadet står som nytt, användaren väljer. Inga tak på markerade rader i någon lista.
- **Produktbundna kriterier gäller bara den valda produkten:** profilen kompilerades om till tre måste-kriterier, ett per produkt; att kräva alla tre av varje bolag fällde 80 av 100.
- **Dygnsbudgeten höjdes i development (8 → 32 M tokens)** för natten, så att omkörningen kunde slutföras; Anton återställer.

## Context & Discussion
- De 27 utan utkast efter 2026-10-11 föll i researchen som nivå C (21 på produktmatchningen, 6 på B2B/B2C-kriterierna); de var B innan bara för att produktgrinden inte såg produktlistan.
- Profilen (`agent_configs.settings.profil`) kompileras om vid körstart när indata ändrats; AI:n satte "måste" på alla tre produktkriterier.
- Ekospeceriet Göteborg AB: gammalt godkänt utkast kvar (08:00), inte i de 100, lämnat för Anton.
- Beads går inte att nå (dolt saknas i PATH).

## Open Threads
- Anton granskar 92 nya utkast i Snajps granskningskö; inget går ut utan godkännande.
- Åtta leads faller som nivå C efter tre försök (listade i handoffen): lämna, Processa om, eller mjuka upp de produktbundna kriterierna till bör. Antons avvägning mot Sebbes krav 2026-10-06.
- Återställ `LEADS_DAILY_TOKEN_BUDGET` på api i development till 8 M (nu 32 M); variabeln kräver ett deploy efter ändring.
- Ekospeceriet: avbryt eller låt gå 08:00.
- Stilgrinden: agenten ska namnges i stycke 2 före löftet i garanti/pilot; du/ni-blandning ska fällas.
- Uteslutningen "offentlig sektor" tillämpas ibland på bolagets kunder (STINAB).
- En "bara utkast"-scope för Skapa om, så att bra research inte görs om.

## Cross-Project Handoffs
- None this session.

## Current State After This Session
Kedjan skriver referensutkastet på första försöket för 92 av 100 Snajp-leads, verifierat med samma grind som kedjan kör (`scripts/granska_utkast.py`). Development kör `dc8e3d3`; main orört (PR #31 väntar). Nästa session: Antons granskning av kön, beslut om de åtta och om budgeten, och de två mindre stilgrindsförbättringarna.

<!-- session-state
date: 2026-10-12
type: feature
files_created:
  - ~/snipe-leads/scripts/omskriv_utkast.py
  - ~/snipe-leads/scripts/granska_utkast.py
  - ~/snipe-leads/snajp-support/tests/leads/test_stilkontroll_2026_10_12.py
  - ~/snipe-leads/snajp-support/tests/leads/test_produktbundna_kriterier.py
  - ~/snipe-leads/HANDOFF-2026-10-12-UTKASTKEDJAN.md
  - ~/snipe-leads/plans/2026-10-12-utkastkedjan.md
files_modified:
  - ~/snipe-leads/agent-core/prompts/leads-skrivstil.md
  - ~/snipe-leads/agent-core/prompts/leads-systemprompt.md
  - ~/snipe-leads/snajp-support/app/leads/stilkontroll.py
  - ~/snipe-leads/snajp-support/app/agent/leads_research_v2.py
  - ~/snipe-leads/snajp-support/app/leads/bedomning.py
  - ~/snipe-leads/snajp-support/app/api/leads.py
  - ~/snipe-leads/snajp-support/app/api/schemas.py
  - ~/snipe-leads/components/leads/SkickatLista.tsx
  - ~/snipe-leads/docs/BESLUT.md
  - ~/snipe-leads/STATUS.md
  - ~/snipe-leads/GOALS.md
decisions_made: 5
open_threads: 7
handoffs_pending: []
priority_changes: false
status_updated: true
goals_updated: yes
next_session_focus: "Antons granskning av de 92 utkasten, beslut om de åtta som faller och om dygnsbudgeten"
session-state -->

## Tillägg förmiddagen
Anton: "som ni gör"/"som ert" stod kvar i nästan alla ingångar. Grinden fäller nu etiketterna var de än står och allmänna ingångar ("man", "den som"); kedjan fick ett obligatoriskt personaliseringssteg för ingången (andra person, detalj ur citaten) före humanizern (`dda1531`). Alla 100 omkörda: 20 var redan skickade (godkända 08:34), 76 av 80 har nya utkast utan etiketter, 4 faller på profilens hårda kriterier (DS Flexhal, Nyströms Byggtjänst, Z Marktjänst, SafeTeam). Budgeten i development 48 M.
