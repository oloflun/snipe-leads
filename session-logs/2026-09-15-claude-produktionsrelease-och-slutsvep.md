# Session 2026-09-11 → 2026-09-15: CRM-demon, main-releasen och produktionssvepet

**Agent:** Claude (huvudsessionen) · **Gren:** development · **Slutläge:** Alla kontroller gröna, båda miljöerna; alla tre agenter liveverifierade i produktionen.

## Levererat

1. **CRM-demon** (`/demo/crm`, c1c3c0c + omarbetning): CSV-import av kundens
   CRM-lista (klientside, localStorage), master–detalj-layout, simulerade
   signaler märkta som sådana, isolerad Email studio per kund. 18-stegs
   E2E-svit (`scratchpad/testkor_crm.mjs`, tar bas-URL) — 18/18 mot localhost,
   development OCH produktionen.
2. **Main-releasen** (§8.1-ordningen, Antons godkännande): merge av
   railway-main (ffda526), migrationer 043–064 mot main-DB, fast-forward,
   PR #11 mergad av oloflun, **deploytriggrarna omlagda till grenen `main`**
   — tvåstegsfällan släckt. DEPLOY.md/CLAUDE.md/railway_provision.py/
   INV-DEPLOY-002 uppdaterade (0306119, dfce76e).
3. **Hotfix-PR #12** (Vertex-prefixet): produktionens agenter föll med 400 —
   liveupptäckt via /chat/snajp, fix fanns på development, mergad, verifierad.
4. **065_workspaces_admin_grant** (6b9c069): 064 lade RLS-policyn utan
   tabellgrant → härledda paket + tracebacks var 30:e sekund. Körd mot båda
   DB:erna (main av Sebbe), verifierad som snajp_app.
5. **--flytta-fran i link_admin_workspace** (09912ae): main-adminens workspace
   pekade på migration 061:s autogenererade tenant → 409 på alla
   arbetsyteflikar. Omkopplad till snajp.
6. **Miljöåterställningen efter Railway-stoppet**: plan + trigger med
   commitSha-fällan dokumenterad, mailvägarna (Resend) till main-api,
   IMAP till main (poller 300 s) med dev som konfigurerad-men-tyst
   (INBOX_POLL_SECONDS=0), enligt Sebbes beslut att main äger inkorgen.

## Produktionssvepet (allt liveverifierat)

- Support: chatt (korrekt produktsvar, 29,7k tokens i Körningar),
  Testmail → ärende + utkast, IMAP-pollern aktiv.
- Leads: målgrupp ifylld (bransch/stad/roller), 2 research-körningar med
  V2-packet (13,7k + 9,2k tokens) → PitchPoint AB + SafeTeam i Sverige AB.
- Bokföring: Trio aktiverat (Sebbe, Admin-vyn krävs — bytPlan spärrar demo-vy),
  fiktivt Circle K-kvitto (PDF) → korrekt avläsning (823,50 kr, moms 25 %)
  och exakt uträkning (658,80 + 164,70).
- qa_vyer: tre roller gröna (kundkontot finns med rätta inte i prod).
- verify_railway: alla kontroller gröna, noll degraderade tjänster.

## Öppet vid sessionens slut

- e6 äger release-PR:en development→main (12 commits före) + handoff till
  Anton; 065 följer med (main-DB:n har den redan).
- bd-trackern trasig lokalt (Dolt saknar repo_state.json) — inga ärenden
  kunde skrivas.
- Klassificerarens hårda stopp för agenten: secret-writes, IaC-skapande,
  PR-admin-merge, rå produktions-SQL, paketbyte (faktureringsyta) — allt
  löst via användarens hand eller sanktionerade skript.
- STATUS.md ej uppdaterad av mig (formatet ägs av carl-hooken).
