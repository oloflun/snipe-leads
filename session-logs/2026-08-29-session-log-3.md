# Session Log — 2026-08-29 (3)

## Session Summary

Hela sjufasplanen plus den nya Redis-arkitekturen planerades, byggdes,
verifierades och pushades till `development` (tre commits, `cb05da0`/`f25e91b`/
`0512ab3`). Kärnan: chattkörningar överlever nu en deploy (Redis Streams +
idempotent återtag, INV-JOB-001), en tenant-skopad semantisk svarscache med
mörkstartsläge (INV-CACHE-001), rullande samtalsminne (INV-MEM-002), och
Fas 1–6-ytorna (skarp Email-studio, testisolering, befordran, studion i
leaden, Testchatt-fliken, model-kolumnen). 101 nya tester; 1586+362 gröna,
tsc rent, migration 054+055 applicerade före push, `qa_vyer` GRÖNT mot live
dev. Utförlig handoff till Sebbe: `HANDOFF-2026-08-29-REDIS-OCH-FASERNA.md`.
Arbetet dirigerades till nio Sonnet-delagenter; varje leverans lästes och
flera fel fångades bara i egen granskning/liveverifiering (viktigast:
RediSearch TAG-escapningen som sviten aldrig kunnat se).

## What Changed

Fullständig fil-för-fil-karta med motiveringar: se handoffen §1. Kort:

### Files Created (urval)
- `snajp-support/app/jobs/stream.py`, `app/cache/{svarscache,embeddingcache,versioner}.py`, `app/minne/arbetsminne.py`, `app/leads/befordran.py` — Redis-lagret + befordransvalideringen.
- `supabase/migrations/054_prospect_origin_test.sql`, `055_agent_runs_model.sql` — applicerade i development före push.
- `scripts/redis_kontroll.py`, `redis_tls_pa.py`, `redis_provisionera.py`, `gemini_web_konfig.py` — GDPR-grinden + de tre kommandon klassificeraren kräver Antons hand för.
- `plans/2026-08-29-redis-agentarkitektur.md`, `docs/REDIS_IRIS_EVAL.md`, `HANDOFF-2026-08-29-REDIS-OCH-FASERNA.md`.
- `app/api/snajp-support/testchatt/*`, `components/snajp/SupportWorkspaceTabs.tsx` — Testchatt-fliken.
- 12 nya testfiler inkl. fyra invariantfiler (INV-JOB-001, INV-CACHE-001, INV-MEM-002 via test_arbetsminne, INV-SEC-012).

### Files Modified (urval)
- `snajp-support/app/agent/support_agent.py` — cachegrind (härdad mot påhopp), arbetsminne i _render_conversation, aterta/vid_arende, is_test, run_id.
- `snajp-support/app/api/{chat,leads,kb,schemas,admin_profil,bookkeeping}.py`, `app/main.py`, `app/config.py`, `app/jobs/store.py`, storage-tripletten.
- `components/leads/{Bolagssida,Bolagsregister,LeadsRunForm,LeadsControls}.tsx`, `components/snajp/SupportChat.tsx` (544→1250 rader), `components/email/EmailStudioEditor.tsx`, `components/admin/Testkorningar.tsx`, `lib/routes.ts`.
- `DEPLOY.md`, `CLAUDE.md`, `.github/workflows/` (två döda borttagna, verify.yml-triggern), `EMAIL_STUDIO.md`, `docs/JURIDIK_ATGARDER.md` P1.2, `docs/registerforteckning.md`, `lib/bolag.ts`, `GOALS.md`, `snipe-leads.md`, båda planfilerna.

## Decisions Made

- **Iris-strategi A (självbyggt + gates):** managed Agent Memory/LangCache är preview och skickar sessionsinnehåll till en extraktions-LLM — mönstren byggdes självt på egen EU-Redis; åtta adoptionsgates i `docs/REDIS_IRIS_EVAL.md`. Godkänd av Anton via planen.
- **Postgres förblir system of record; Redis bär bara TTL:at/rekonstruerbart** — kö, cache, arbetsminne. KB-vektorerna flyttas INTE (retrieval är inte flaskhalsen; RLS finns bara i Postgres).
- **Ingen redigeringspersistens från studion till outreach_messages:** fria redigeringar EFTER grundningsgrinden hade försvagat grinden. Medvetet val, står i handoffen §7.
- **CNAME:n applicerades INTE:** Railway-hosten svarar 404 utan domänregistrering på tjänsten, och registreringen är main-skrivande (spärrad). CNAME+registrering = ETT cutover-steg (snipe-qu2-not).
- **Klassificerarstoppen respekterades tre gånger** (Redis Cloud-PUT, Railway-hemlighet, tidigare mönster): allt paketerades som körbara skript åt Anton i stället för kringgående.
- **Evals-flaken rotorsakades i stället för att tystas:** dev-maskinens DNS (15+ s färsk uppslagning) mot connect-timeout 5 s, plus openai-versionsdrift lokalt (2.53 mot pin >=3.3). Varje golden-fall grönt i ≥2 av 4 varv; ingen kodregression.

## Context & Discussion

- **Antons stående instruktion denna session:** frågor ställs ALLTID i klartext tills AskUserQuestion-verktyget bevisat stabilt (verktyget kraschade med internal error). Sparad i agentminnet.
- **B1 är värre än "okopplat projekt", nu med mätdata:** nya Gemini-nyckeln (…Idfg) svarar ~170 s/anrop (strypt kö), och Railway kör fortfarande gamla …A2Mw i BÅDA miljöerna. Fas 6:s Gemini-rundor och liveagentens svar är kvotgrindade tills Antons konsolsteg. Live-beviset: chatt-E2E:t på dev gick hela strömkedjan och föll exakt på 429 dygnskvot i triagesteget.
- **Redis Cloud-databasen:** EU (europe-west1) verifierad via konto-API, TLS AV — `redis_tls_pa.py --apply` är Antons kommando. Redis Cloud + Resend står nu som underbiträden i juridikkedjan.
- Sebbes handoffs (granskningen + Kunder & Data) lästes i sin helhet; hans två "E2E Verifiering AB"-prospekt syns i registret och är nu städbara via befordra/filter.
- En parallell Sonnet-session (05:56) loggade det då-okommitterade arbetet som "okänt Redis-arkitekturarbete" och lämnade diffen åt Antons bekräftelse — Antons /goal var den bekräftelsen; ingen konflikt.

## Open Threads

- **Antons kommandon (allt förberett):** `python scripts/redis_tls_pa.py --apply` (TLS + rediss), `python scripts/gemini_web_konfig.py --apply` (Fas 1.2), Redis DPA i kontot, B1-konsolsteget + ommätning + nyckelutrullning, rotera EMAIL_STUDIO-testkontot (snipe-8wy).
- **Mörkstarten mäter:** `SEMANTIC_CACHE=shadow` satt på development/api — läs träffkvoten i Händelser (source `cache:svarscache`) efter några dagars trafik innan `on` övervägs.
- **Fas 6 Gemini-halvan** väntar på B1 (snipe-nm4-not); **R5** (mains Redis, plan 21437 à 10 USD/mån) och **Fas 7-deploydelen** är spärrade enligt §8.1a tills Anton säger cutover; **R6-sandboxen** väntar på kontostegen i `docs/REDIS_IRIS_EVAL.md` §2.
- **KB-wrap-luckan** (KB-text saknar wrap_untrusted_content; positionen bevisad säker av INV-SEC-012) ligger som bakgrunds-chip.
- Kvarlämnat på dev: en misslyckad chattkörning (429) för public-demo-tenanten — kosmetiskt, försvinner med kvoten.

## Mekaniska avslutet (conclude-finalize)

7/8 ok på 19 s: vault-backup (commit 14181e1, tre destinationer), validering
GRÖN ("projektets läge stämmer överallt"), chorus skickad till
codex/gemini/hermes, global STATUS, memory-mirror, sessions.db (rad 84).
FAIL: qmd `collection add` — namnkollision eftersom repot redan ÄR en
qmd-collection sedan tidigare; indexet finns, nya filer plockas upp av den
befintliga collectionens nästa uppdatering. `sync-configs`: CLAUDE.md →
AGENTS.md + GEMINI.md synkade. Upstream: inga globala agentstack-ändringar
denna session. Skill-eval: Redis-liveverifieringen bedömdes som engångs —
ingen ny skill skapad.

## Cross-Project Handoffs

None this session (handoffen till Sebbe är projektintern).

## Current State After This Session

`development` kör hela Redis-arkitekturen live (uppstartsloggen visar ström-
workers, cache-lagret och leadsströmmen aktiva) och alla sju faser är byggda;
det enda som skiljer development från planens slutmål är det som medvetet
kräver Antons hand (TLS-kommandot, Gemini-nyckelkedjan, cutover-paketet).
Nästa session: kör Antons kommandolista i handoffens §6, läs av mörkstartens
träffkvot, och när B1 är löst — Fas 6:s Gemini-rundor och `SEMANTIC_CACHE=on`.

<!-- session-state
date: 2026-08-29
type: implementation-full-stack
files_created:
  - snajp-support/app/jobs/stream.py
  - snajp-support/app/cache/svarscache.py
  - snajp-support/app/minne/arbetsminne.py
  - plans/2026-08-29-redis-agentarkitektur.md
  - HANDOFF-2026-08-29-REDIS-OCH-FASERNA.md
files_modified:
  - snajp-support/app/agent/support_agent.py
  - snajp-support/app/api/chat.py
  - components/snajp/SupportChat.tsx
  - DEPLOY.md
decisions_made: 6
open_threads: 5
handoffs_pending: []
priority_changes: true
status_updated: true
goals_updated: yes
next_session_focus: "Kör Antons kommandolista (handoff §6: TLS, gemini_web_konfig, DPA, B1-konsolen), läs mörkstartens träffkvot i Händelser, och efter B1: Fas 6 Gemini-rundor + SEMANTIC_CACHE=on"
session-state -->
