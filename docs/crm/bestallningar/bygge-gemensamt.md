# Gemensamt för alla backendbyggare i Snajp CRM (läs först)

Arbetskatalog: `C:\Users\Anton L\snipe-leads\.claude\worktrees\snajp-crm-dd0d83` (git-worktree, gren
`claude/snajp-crm-dd0d83`). Backend är FastAPI under `snajp-support/`. Skriv all kod, alla kommentarer och
alla testnamn på svenska, i samma stil som filerna du läser. Inga tankstreck (—) i text du skriver.

## Gränser

- Du arbetar i `snajp-support/`, `db/migrations/`, `scripts/` (bara där beställningen säger), `docs/crm/API.md`
  och `docs/crm/openapi.json`. **Rör aldrig** `components/`, `app/` (Next), `lib/`, `docs/BESLUT.md`,
  `docs/crm/STATUS-MIGRERING.md`, `docs/crm/PARITET.md`, `docs/crm/DESIGN-CRM.md` eller `AGENTS.md`:
  orkestratören bygger gränssnittet där samtidigt som du arbetar.
- **Pusha aldrig.** Skapa inga grenar, inga worktrees, ingen rebase, ingen reset, ingen stash.
- **Commit:** när dina tester är gröna committar du BARA dina egna filer, med sökvägarna utskrivna:
  `git add <dina nya filer>` och sedan `git commit -m "<meddelande>" -- <alla dina filer>`. Aldrig `git add -A`,
  aldrig `git commit -a`, aldrig ett naket `git commit` utan sökvägar: orkestratören kan ha egna filer i
  indexet. Faller git på `index.lock`: vänta fem sekunder och försök igen. Avsluta meddelandet med raden
  `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`. Skriv meddelandet i en fil med Write och använd
  `git commit -F <fil> -- <sökvägar>` (heredoc fungerar inte här).
- Supabase är borttaget. DeepSeek får aldrig se kunddata. Webbplatsbedömningen (`webbrevision`, `webbniva`,
  `lan` och det som härleds ur dem) är hemlig och får aldrig följa med i ett CRM-svar.
- Migrationer är additiva och idempotenta (`create table if not exists`, `add column if not exists`,
  `drop constraint if exists` följt av `add constraint`), med radskydd, grants och `force row level security`
  exakt som i `db/migrations/20261126090000_160_crm_grund.sql` och `…130000_164_crm_affarer_uppgifter.sql`.
  Nästa lediga nummer står i din beställning.
- Varje fråga bär `tenant_id` uttryckligen. Kundisolering visas i tester med TVÅ kunder.
- Loggar och händelser bär fältens namn, aldrig värden. Skriv aldrig ut hemligheter.

## Koden du bygger i (läs det din beställning pekar på, hela filerna)

- `snajp-support/app/crm/lagring.py`: lagringen (`TABELLER`, `_STANDARD`, `_in`, `_upp`, `_hamta`, `_valj`,
  `lista_poster`), Postgres via `storage._scoped(tenant_id)` (radskydd), en dict på `MemoryStorage` i testerna.
- `snajp-support/app/crm/synk.py` (skrivvägar för bolag och personer), `objekt.py` (affärer, uppgifter,
  anteckningar, aktiviteter, bilagor), `handelser.py` (händelseloggen), `webhooks.py`, `falt.py` (svenska
  format), `utfall.py`, `tidslinje.py`, `tillgang.py`.
- `snajp-support/app/api/crm_v1.py` (publikt API: `kraev(omfang)`, `fel(status, kod, en, sv)`, `_avtal`,
  `_ursprung`, `_idempotent`, `_Kropp`, fältkartorna, `specifikation()`), `crm_v1_objekt.py`,
  `crm_v1_tidslinje.py` (mönstret `koppla(v1)` för en egen fil vars rutter läggs till med
  `router.routes.extend(...)`; `include_router` bryter spec-testet i FastAPI 0.139).
- Tester: `snajp-support/tests/crm/` (`conftest.py` har `buddy`, `annan`, `storage`; `buddy.klient()` är en
  integrationsnyckel med omfång, och kundens egen nyckel skapas med `storage.create_api_key`).
- `docs/crm/API.md`: guidens ton. Testet `test_varje_felkod_i_koden_ar_stabil_och_dokumenterad` kräver att
  varje `fel(status, "kod", …)` står i felkodstabellen. Nya API-filer ska in i det testets fillista.

## Körning och kontroll (namngivna kontroller som ska vara gröna innan du committar)

1. Från `snajp-support/`: `python -m pytest tests/crm -q -p no:cacheprovider` (207 går i dag och ska fortsätta gå).
2. Från repo-roten: `python -m pytest tests/invariants tests/test_rls_nullif_vakt.py tests/test_gdpr_radera.py tests/test_tillagg_synk.py -q -p no:cacheprovider`.
3. Från repo-roten: `python scripts/crm_openapi.py` (skriver `docs/crm/openapi.json`), och kör sedan kontroll 1 igen.
4. Databasvägen mot riktig Postgres-SQL (PGlite, Postgres 17). Starta servern i bakgrunden:
   `node D:/snajp-crm-forlaga/pglite/server.mjs 54329`, och kör sedan från repo-roten
   `python "C:/Users/ANTONL~1/AppData/Local/Temp/claude/05d8e7d92420aa22/4b7c04f9-a411-45fa-addb-72e117ec542a/scratchpad/db_forbered.py" 160 161 162 163 164 165 <dina nummer>`
   (kör förspel och varje migration TVÅ gånger) och
   `python "C:/Users/ANTONL~1/AppData/Local/Temp/claude/05d8e7d92420aa22/4b7c04f9-a411-45fa-addb-72e117ec542a/scratchpad/kor_dbtest.py"`
   (kör `snajp-support/tests/db/test_crm_lagring.py` genom en psycopg2-brygga). Läs de två skripten först så
   att du vet vad de gör; lägg dina egna databastester i `tests/db/test_crm_lagring.py`. Stäng PGlite-servern
   när du är klar (döda processen på port 54329). I en enda testtransaktion står Postgres `now()` still.
   asyncpg kräver typade parametrar (`$1::text::uuid`, `::text::timestamptz`): läs varje SQL-sats du skriver
   en gång till mot hur `lagring.py` gör.

Använd `python`, inte `python -I`. Skriv aldrig ändringsskript som heredoc i skalet: använd Edit/Write, eller
skriv ett skript som fil med Write och kör det. Python på Windows: `write_bytes(text.encode("utf-8"))`, aldrig
`write_text`. Maskinen har 16 GB minne och C: har under 2 GB ledigt: starta ingen Next-server, kör ingen
`tsc`, installera ingenting, och skriv inga stora filer.

## Rapporten

Svara med: vad du byggde (filer), API:ts nya former (ändpunkter, fält, felkoder, händelsetyper) så exakt att
gränssnittet kan byggas mot dem, vilka kontroller du körde och deras utfall i siffror, commitens hash, och
allt du INTE gjorde eller inte kunde verifiera. Säg det rakt: en lucka du redovisar är bättre än en du döljer.
