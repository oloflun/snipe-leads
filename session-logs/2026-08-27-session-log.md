# Session Log — 2026-08-27 (natt, Sebbe/Claude)

## Session Summary

Full go/no-go-lanseringsgranskning av hela Snajp (sju parallella delgranskningar:
inventering, dataisolering, demodata, agentflöden, admin, fakturering, teknisk
produktionskontroll) plus live-verifiering mot Railway dev. Ursprungligt beslut
NO-GO med tolv villkor — sedan landade Antons 304-filersmerge (agentbackend-
audit) mitt i passet och löste sex av dem, så listan ombaserades. Därefter:
Antons handoff genomgången, tre av hans fem öppna trådar stängda, hans enda
röda test lagat, fem egna fixar byggda, allt pushat till `development`
(= live på Railway dev enligt den omlagda deploy-kedjan) och verifierat med
`verify_railway.py` (deployad commit f081e11, alla kontroller gröna).

Full rapport: `HANDOFF-2026-08-27-GRANSKNING.md`. `main` är INTE rörd.

## Verifierat (inte antaget)

- **Isolering GODKÄND mot körande DB:** Railway dev ansluter som
  `snajp_web`/`snajp_app`, båda `bypassrls=false`, ej tabellägare; RLS PÅ på
  64/64 publika tabeller (4 med tomma policyer = deny-all, avsiktligt utom
  möjligen `ss_gallringspolicy`). Supabase-preview: 63/63.
- **RRF-fusionen (snipe-lt9): stängd.** search_kb som snajp_app mot dev —
  fulltext, hybrid (dim=1536) och nonsens, inga fel.
- **Chat-E2E grön hela HTTP-vägen:** 202 → jobb → completed, svaret ordagrant
  KB-grundat. **Svar-E2E: Gemini-429 två gånger** (chatten gick igenom —
  troligen annan kvotpott per modell). Uppföljningssvep: 422, snajp-tenanten
  i dev saknar product_marketing-kontext.
- **larande-vyerna (kund + admin) inloggat:** 200, rätt tomläge, noll fel.
- Testsviter: backend 1450 gröna (var 1444 + 1 röd), rot 335 gröna, tsc rent.

## Commits (c5336e7..f081e11, alla på development)

1. `fix: agent_feedback listades äldst först vid lika tidsstämpel` — Antons
   röda test; Windows-klockan + stabil sort; reversera före sortering.
2. `fix: triage var enda LLM-vägen utan timtak` — enforce + bokföring som
   chatten, två tester.
3. `feat: startvakt vägrar dev-masternyckeln i databasmiljö` — samma mönster
   som dataskyddsspärren; verifierade först (bool-only) att båda Railway-
   miljöerna har riktiga nycklar.
4. `fix: frontend-robusthet` — error.tsx/global-error.tsx, 429-texter
   (detail+error), EjAktiverad i supportinkorgen (kvarglömd vy), fyra
   catch-lösa hämtvägar, 404-copy.
5. `docs:` handoffen.

## Lärdomar

- **En "tom tabell" i ett ad-hoc-skript är ofta RLS som fungerar.** Mitt
  första verifieringsskript läste ss_knowledge_base oskopat som snajp_app och
  fick noll rader ur en full tabell. Skopa med `storage._scoped()`.
- Deploy-kedjan lades om MITT UNDER passet (Antons handoff): `development`
  deployar Railway direkt, `railway-development` är övergiven spegel.
  Minnesfilen `snajp-vilken-stack-deployar` är uppdaterad.
- FastAPI:s HTTPException (`detail`) och husets kvotfel (`error`) är två
  429-former; frontend måste läsa båda.

## Öppna trådar → nästa session

- Gemini-kvoten på svar-vägen (blockerar svar-E2E happy path + bokföringens
  kvalitetskontroll).
- Main-blockerarna i handoffens §4: SMTP-attrappen, fakturering, Snajps orgnr
  `000000-0000`, kvoterna 150/300, Redis, chat-IP-taket (kräver
  klient-IP-forwarding genom Next-proxyn).
- Dev-städ: två testprospekt "E2E Verifiering AB" i snajp-tenanten; seeda
  product_marketing-kontext för snajp i dev.

## Protokollavvikelser

Kanoniska minneskatalogen (`~/OneDrive/Dokument/Obsidian/Knowledge Base/memory/`)
och `sessions.db` finns inte på den här maskinen — hot memory/sessions-raden
kunde inte skrivas. Auto-memory (`~/.claude/projects/.../memory/`) är
uppdaterad i stället: `snajp-vilken-stack-deployar` (omskriven) och
`snajp-granskningslage-2026-08-27` (ny). Ingen ny skill skapad — inget i
passet var repeterbart nog att motivera en.
