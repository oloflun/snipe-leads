# Leads-reglerna, Jev i inkorgen och release-PR #30 (2026-10-04)

Fortsättning på `plans/2026-10-03-snajp-suite-struktur.md` och
`plans/2026-10-03-appytor-design.md`. Full bakgrund:
`HANDOFF-2026-10-04-SUITE-JEV-MERINFO.md`.

## Scope
- Jev i inkorgen (Provsortera, `INKORG_JEV`) och dataskyddet kring den.
- Antons leadsregler 2026-10-04: registret som filter, Jev först, bara VD,
  Iris via webbplatsen, listor bara med VD-styrkt kontakt.
- Release av development till main (PR #30, Sebbe) och det som ska göras före
  och efter mergen.

## Completed
- [x] Provsortera + `POST /api/inbox/sortera` (`ab4bfa2`).
- [x] `INKORG_JEV` off/prov/auto, PII bort ur Jev-anropet, frikopplad från `IRIS_JEV` (`ab4bfa2`, `dd2b165`).
- [x] `INKORG_JEV=auto` i development (driftsatt) och main (skip-deploys); Jev-nyckeln kopierad till main.
- [x] merinfo: målgruppsmening blir ingen bransch (`dd2b165`); bolagssidan som researchkälla (`72db2cf`); saknad sajt = träff vid `utan_webbplats` (`d65de7f`).
- [x] Skickat-kopian följer brevlådans syfte — krock med Sebbes `fb85da9` (`72db2cf`).
- [x] Leadsreglerna i kod och i `CLAUDE.md`/`AGENTS.md` (`02babb8`).
- [x] Granskning av Sebbes 17 commits; isoleringsprov med `git merge-tree` (5 av 15 krockar).
- [x] Tre skarpa prov på Alunix i development.

## In Progress
- [ ] Inget pågående; sessionen avslutad.

## Remaining
- [ ] Migration 090 + 091 mot main (Antons ord krävs).
- [ ] "Ej relaterat"-vy + "Flytta till support" i inkorgen, eller `INKORG_JEV=prov` i main tills den finns (Antons val).
- [ ] Merge av PR #30 (Anton).
- [ ] Efter merge: `scripts/satt_mejlsignatur.py` per kund i main; `flytt_nycklar.py --check`; verifiera nattspegeln.
- [ ] Leadsvolymen: `PROV_PER_LEAD`, info@-fallback för Iris (regelfråga), branscher i Alunix-profilen, byt namn "Alunix workspace" → "Alunix".
- [ ] Branschmatchningen (VVS, el) i `valj_branscher`.
- [ ] Svenska-only felmeddelanden i `lib/actions/auth.ts` (Sebbes, INV-COPY-001 ser dem inte).

## Deferred
- Jev som klassare av svar från leads (förslag, ej beslutat).
- Twenty-vybarens ⋮-meny; listrader som leads direkt (fråga 2 i IA-planen).

## Blockers
- ScrapeGraph-krediten slut (Anton fyller på).
- Disken C: ~1 GB ledigt.

## Next Steps
1. Fråga Anton om 090/091 och om Ej relaterat-vyn; bygg vyn om han väljer den.
2. Efter Antons merge: signatur, flyttkontroll, spegeln.
3. Volymbesluten i Remaining.
