# Datamängder, åtkomst och lagringstid

Datum: 2026-11-18. Skrivet av Claude (agent) på Antons uppdrag. Status: utkast.
**Lagringstiderna är obeslutade.** Kolumnen "Förslag" är ett förslag som Anton beslutar;
ingen tid här är beslutad. Underlag för GDPR LBT-1 (art. 30), ISO 27001 A.5.33 och
ISO 42001 A.4.3 (`score-plan-2026-11-18.md`). Kompletterar registerförteckningen
(`docs/registerforteckning.md`), vars behandlingar (A1–A3, B1–B3) anges per datamängd.

Allt är härlett ur migrationskedjan (`db/migrations/*.sql` i filnamnsordning, plus
`railway/000_auth_compat.sql`) och koden som anges. "Migration 119" betyder filen i
`db/migrations/` med det numret. Det som inte går att belägga i repot står som "inte belagt".

**Avgränsning.** Rättigheterna nedan är de som kedjan ger en databas som reses från noll.
Driftens databaser är inte avlästa (ingen databasanslutning gjordes). Produktionens tabeller
skapades ursprungligen i Supabase, så de faktiska rättigheterna i `main` kan avvika; det
kontrolleras med en läsning av `information_schema.role_table_grants` och `pg_policies` i
`main`, vilket inte är gjort.

---

## 1. Läsanvisning: roller, skopning och människor

### Databasrollerna

| Roll | Vem använder den | Grundrättigheter | RLS |
|---|---|---|---|
| `snajp_app` | api-backenden (`snajp-support/`) | `select, insert, update` på de 18 `ss_*`-tabellerna i migration 009, och samma tre på **varje tabell som skapas efter 009** genom `alter default privileges` (`009_snajp_app_role.sql:24-51`). `delete` bara där den uttryckligen ges. Tabeller skapade före 009 (`000_base_schema.sql`, `workspace_invites`) har ingen grant om inget annat sägs | `nobypassrls`. Skopas med `app.tenant_id` per transaktion |
| `snajp_web` | Next-appen | Sedan migration 126 (2026-11-18) bara det webbens SQL gör: 13 tabeller, flera av dem bara på vissa kolumner (`20261118160000_126_snajp_web_minsta_rattighet.sql`), och ingen rättighet på nya tabeller. Listan prövas i CI (`snajp-support/tests/db/test_snajp_web_rattigheter.py`). Före 126: LIUR på alla tabeller i `public`, nu och framöver (030) | `nobypassrls`. Sätter bara `app.user_id`, aldrig `app.tenant_id` (`lib/db.ts:86-89`). Policyerna avgör allt |
| `synk_las` | Synken main → development (`scripts/railway_synk.py`) | Bara `select` på 31 namngivna tabeller (migration 122) | `bypassrls`, skrivskyddad per transaktion. Skapas utan inloggning; ägaren slår på den i `main` |
| `postgres` (ägare, superanvändare) | Migrationerna (`.github/workflows/migrera.yml`) och skripten: `gdpr_radera.py`, `gallra.py`, `admin_cleanup.py`, `railway_synk.py`, `railway_seed_dev.py` m.fl. ansluter som `postgres` (`scripts/gdpr_verktyg.py:89`) via den publika TCP-proxyn (`drift-och-tillgangar.md` avsnitt 1) | Allt | Kringgår RLS |

`anon`, `authenticated` och `service_role` finns bara för att äldre grant-satser ska ha
något att peka på; ingen ansluter som dem (`railway/000_auth_compat.sql`, avsnitt 1).

**RLS på varje tabell.** Event-triggern `ensure_rls` (`0000_rls_auto_enable.sql`) slår på
radnivåsäkerhet för varje ny tabell i `public`. En roll utan grant når inte tabellen; en roll
med grant men utan tillämplig policy ser noll rader. Tre tabeller har ingen policy alls och
nås därför bara av ägaren och säkerhetsdefinierade funktioner: `platform_admin_bootstrap`,
`workspace_tenant_keys`, `synk_raderingar`.

### Förkortningar i tabellerna

- Rättigheter: **L** läsa, **I** infoga, **U** uppdatera, **R** radera. **–** ingen grant.
- **kund**: policyn släpper bara rader där `tenant_id` är transaktionens `app.tenant_id`.
- **oskopad**: policyn släpper dessutom alla kunders rader när `app.tenant_id` inte är satt.
  Det är plattformsadminens väg; skyddet ligger i API-lagret (`require_master_key`), inte i
  RLS (`snajp-support/app/storage/postgres.py`, kommentaren över `spegel_info`). Migration
  029, 053, 064 och 074.
- **arbetsyta**: policyn släpper rader där `workspace_id = current_workspace_id()`, härlett ur
  `app.user_id` via `profiles` (`000_base_schema.sql`).
- **alla**: policyn är `using (true)` för rollen.
- **snajp_web**: kolumnen anger vad rollen har och ser efter migration 126. "– (126)" betyder
  att rollen saknar rättighet på tabellen; före 126 hade den LIUR på alla tabeller, och
  policyerna avgjorde vad den såg.

### Människorna och ytorna

- **Kundens användare** ser sin kunds data i Next. Next läser arbetsytans egna tabeller som
  `snajp_web` och allt under `ss_*`, leads och bokföring genom api:t med kundens nyckel
  (`app/api/snajp-support/_lib.ts`), alltså som `snajp_app` skopad till kunden.
- **Plattformsadmin** (personerna i `platform_admins`; vilka det är i drift är inte avläst)
  ser alla kunders data två vägar: adminytan över master-nyckeln (`/api/admin/*`,
  `snajp-support/app/api/admin*.py`, oskopad `snajp_app`) och kundbesök, där admin får
  kundens nyckel och ser det kunden ser (`lib/actions/vy.ts`, migration 042). Båda loggas i
  `audit_logs` sedan migration 123.
- **Den som har `.env.deploy` eller repots Actions-hemligheter** når allt som `postgres`.
  Vilka personer det är är inte belagt i repot.
- **Webbplatsbedömningen** (`webbrevision`, `webbniva`, webbpoolen) får bara visas för
  plattformsadmin och kunderna Umeå Webdesign och Alunix (`CLAUDE.md`, beslut 2026-10-08).
  Det är en regel i koden, inte en databasrättighet.

---

## 2. Gallring i dag

| Mekanism | Vad den gör | Läge |
|---|---|---|
| `gallra_tenant` / `gallra_alla` (migration 119), schemalagd i api:t (`snajp-support/app/jobs/gallring.py`, startas i `main.py:370-377`) | Raderar eller anonymiserar en kunds data äldre än kundens period i `ss_gallringspolicy`, räknat från senaste aktivitet. Täckningen står i 119:s filhuvud och per tabell nedan | **Av.** `GALLRING_AKTIV` är avslagen i drift (`drift-och-tillgangar.md` avsnitt 5). En kund utan rad i `ss_gallringspolicy` gallras aldrig; att någon policy är satt i `main` är inte belagt |
| `scripts/gallra.py` | Samma funktion för hand, torrkörning som standard, sätter policyn per kund | Aldrig körd skarpt enligt `underlag/beslut/d-gallringsperiod.md` |
| `logga_adminatkomst` (migration 123) | Raderar åtkomstloggens rader (`kanal` satt) äldre än 365 dagar vid varje skrivning | **På**, oberoende av `GALLRING_AKTIV`. Äldre radtyper i `audit_logs` (`kanal` null) omfattas inte |
| `platform_rate_events` | Rader äldre än ett dygn raderas vid varje skrivning (`snajp-support/app/storage/postgres.py:4646`) | På |
| `password_reset_tokens` | En ny begäran raderar kontots tidigare token (`lib/actions/auth.ts:272`) | På, men använda och utgångna tokens ligger kvar tills kontot begär en ny |
| `inloggningsforsok` (migration 125) | Spärren mot upprepade inloggningsförsök: HMAC av e-postadress eller IP, antal försök, spärrtid. Ingen adress eller IP i klartext | – | – (bara via security definer-funktionerna `inloggningsforsok_*`) | Ja: rader utan aktiv spärr och utan försök på ett dygn tas bort vid nästa registrering | Som i dag (ett dygn). Skäl: spärren behöver bara minnas den senaste tiden |
| `scripts/gdpr_radera.py` | Radering per registrerad på begäran (art. 17), som `postgres` | För hand |
| Redis | TTL i koden: jobbposter 1 timme (`jobs/store.py:16`), arbetsminne 72 timmar (`minne/arbetsminne.py:71`), svarscache 21 dagar (`cache/svarscache.py:88`), embeddingcache 30 dagar (`cache/embeddingcache.py:32`), sökvägar under `snajp-support/app/` | På |

Integritetspolicyn säger 24 månader för alla kategorier (`app/integritetspolicy/IntegritetspolicySida.tsx:104`).
Beslutsunderlaget `underlag/beslut/d-gallringsperiod.md` föreslår samma tid men är osignerat.
I dag gallras alltså ingen kunddata i drift. Förslagen nedan utgår från 24 månader där inget
annat skäl finns, för att stämma med det policyn redan lovar.

---

## 3. Förteckningen

### D1. Konton, arbetsytor och åtkomst (A1)

Registrerade: kundens användare och plattformsadmin.

| Tabell | Innehåll, personuppgifter | snajp_app | snajp_web | Gallras i dag | Förslag |
|---|---|---|---|---|---|
| `auth.users` (schemat `auth`, inte `public`) | E-post, lösenordshash, namn i `raw_user_meta_data` | L (se fynd 3.1) | L; I och U bara på kolumnerna i 126; ingen RLS | Nej. Konton raderas för hand (`scripts/admin_cleanup.py`) | Kontots livstid; raderas 3 månader efter avslutat avtal. Skäl: efterfrågor och fakturering kort efter avslut |
| `profiles` | Namn, roll, arbetsyta | L, oskopad (074) | arbetsyta (L) | Nej (119 lämnar den) | Som `auth.users` |
| `workspaces` | Arbetsytans namn, paket, provperiod. Ingen person | L, oskopad (064, 065) | arbetsyta (L) (126). U på `is_demo` återtagen i 127: demon märks genom `markera_demoarbetsyta()` | Nej | Avtalets löptid + 3 månader |
| `workspace_invites` | Inbjuden e-post, inbjudare | – | arbetsyta (L, I och R för ägaren, migration 032) | Nej. Raderas när en inbjudan dras tillbaka (`lib/actions/team.ts:165`) | Accepterade: radera vid acceptans. Oaccepterade: 30 dagar. Skäl: behövs bara tills inbjudan används |
| `workspace_tenant_keys` | Kundens api-nyckel i klartext, ingen person | LIU-grant, ingen policy (0 rader) | – (126) | Nej | Så länge arbetsytan finns |
| `password_reset_tokens` | Konto-id, tokenhash | LIU-grant, ingen policy (0 rader) | alla (LIR; U bara `used_at`, 126) | Delvis, se avsnitt 2 | 24 timmar efter `expires_at`. Skäl: tokenen är värdelös efter giltighetstiden |
| `notification_preferences` | Konto-id, notisval | LIU-grant; L alla rader (043) | egen rad via `app.user_id` (LIU) | Nej | Kontots livstid |
| `platform_admins` | Konto-id, vem som gav rätten | LIU-grant, policy bara på egen rad (0 rader utan `app.user_id`) | egen rad (L) | Nej | Så länge personen är admin; raden raderas när rätten dras in (`admin_cleanup.py:247`) |
| `platform_admin_bootstrap` | E-post till blivande plattformsadmin | LIU-grant, ingen policy (0 rader) | – (126) | Nej | Radera när kontot skapats och rätten getts. Skäl: raden har inget syfte efter det |
| `trial_paminnelser` | Mottagaradress för provperiodspåminnelse | LIU, oskopad (074) | – (126) | Nej | 24 månader |
| `billing_payment_methods` | Kortmärke, fyra sista siffror, giltighet | LIU-grant, policy arbetsyta (0 rader utan `app.user_id`) | – (126) | Nej | Ingen kod läser eller skriver tabellen sedan Stripe togs bort (migration 076). Förslag: töm och ta bort tabellen |
| `ss_tenants` | Kundens namn, slug, status. Ingen person | LIU, kund + oskopad (003, 029) | L på `id, slug, name`, alla rader (126) | Nej | Avtalets löptid + 3 månader |
| `ss_api_keys` | Nyckelns prefix och hash, kundnamn | LIU, kund + L oskopad (`api_key_lookup`) | – (126) | Nej | Aktiva nycklar så länge de gäller; inaktiva 12 månader. Skäl: spårbarhet vid missbruk |

### D2. Snajps kundregister (A1, A3)

Registrerade: kontaktpersoner hos Snajps kunder.

| Tabell | Innehåll, personuppgifter | snajp_app | snajp_web | Gallras i dag | Förslag |
|---|---|---|---|---|---|
| `ss_customer_details` | Orgnr, faktura- och företagsadress, faktureringsmejl, telefon, avtalsdatum | LIUR, oskopad (053) + L kund (073) | – (126) | Nej (119: "gallras när kundrelationen avslutas", ingen mekanism finns) | Avtalets löptid + 12 månader. Fakturor som byggts på uppgifterna bevaras 7 år i bokföringen (BFL 7 kap. 2 §), inte här |
| `ss_customer_contacts` | Namn, roll, mejl, telefon | LIUR, oskopad (053) | – (126) | Nej | Avtalets löptid + 12 månader, eller när personen slutar vara kontakt |

Ytor: adminfliken Kunder och data (`snajp-support/app/api/admin_kunddata.py`).

### D3. Plattformens egna förfrågningar och webbpoolen (A2, A2b)

Registrerade: personer som bokar demo; för webbpoolen bolag (bolagsnivå).

| Tabell | Innehåll, personuppgifter | snajp_app | snajp_web | Gallras i dag | Förslag |
|---|---|---|---|---|---|
| `demo_requests` | Namn, företag, e-post, meddelande | LIU-grant, ingen policy för rollen (0 rader) | Bara I (migration 050) | Nej. Migrationens kommentar hänvisar till 048, men varken 048 eller 119 gallrar den | 12 månader efter förfrågan. Skäl: en demoförfrågan som inte lett till kund på ett år har inget syfte |
| `webbpool` | Domän, bolagsnamn, orgnr, ort, län, webbnivå och webbrevision. Bolagsnivå; enskilda firmor ska aldrig vara källa (`CLAUDE.md` regel 20) | LIU, alla (108) | – (126) | Nej | 12 månader efter senaste observation (`sedd_at`), som registerförteckningen A2b föreslår |
| `webbpool_fordelad` | Domän, mottagande kund, lista | LIU, alla (108) | – (126) | Nej | Som `webbpool` |

Ytor: plattformsadmin och de två webbyråkunderna (regeln om webbplatsbedömningen ovan).

### D4. Supportagenten: kundens kunder (B1)

Registrerade: kundens kunder (de som chattar eller mejlar kundens support).
Hela datamängden läses av `synk_las` utom `ss_chat_state`, `ss_channel_contacts` och
`ss_channel_inbound_seen`.

| Tabell | Innehåll, personuppgifter | snajp_app | snajp_web | Gallras i dag (om på) | Förslag |
|---|---|---|---|---|---|
| `ss_customers` | Namn | LIU, kund | – (126) | 119: radera | Kundens period i `ss_gallringspolicy`; standard 24 månader efter senaste behandling. Vid avtalets slut: radera eller återlämna enligt biträdesavtalet (tiden i avtalet är inte kontrollerad här) |
| `ss_customer_identifiers` | E-post eller telefon | LIU, kund | – (126) | 119: kaskad från `ss_customers` | Som `ss_customers` |
| `ss_tickets` | Ämne, kategori, eskaleringsskäl | LIU, kund + L oskopad (029) | – (126) | 119: radera | Som `ss_customers` |
| `ss_conversations` | Kanal per ärende | LIU, kund | – (126) | 119: kaskad från ärendet | Som `ss_customers` |
| `ss_messages` | Meddelandetext i båda riktningar | LIU, kund | – (126) | 119: kaskad | Som `ss_customers` |
| `ss_chat_state` | Chattläge, språk, överlämning | LIU, kund | – (126) | 119: kaskad från `ss_customers` | Som `ss_customers` |
| `customer_memory` | Fakta om kundens kund i fritext | LIU, kund | – (126) | 119: radera | Som `ss_customers`; överväg kortare (t.ex. 12 månader), eftersom fritexten samlar uppgifter över tid |
| `ss_channel_contacts` | Extern användare, adress (t.ex. telefonnummer), visningsnamn | LIUR, kund | – (126) | 119: kaskad från `ss_customers` | Som `ss_customers` |
| `ss_channel_inbound_seen` | Externt meddelande-id (dubblettspärr) | LIUR, kund | – (126) | 119: radera | 30 dagar. Skäl: behövs bara för att känna igen en omleverans |
| `ss_agent_metrics` | Mätvärden per ärende. Ingen person efter att ärendet raderats (`ticket_id` nollas) | LIU, kund | – (126) | Nej (kopplingen nollas) | 24 månader |

Ytor: kundens inkorg, ärenden och chattar i Next; plattformsadmin via adminytan och kundbesök.

### D5. Supportagenten: inkorgen och mejlflödet (B1)

Registrerade: kundens kunder (avsändare), i löptexten även tredje personer.

| Tabell | Innehåll, personuppgifter | snajp_app | snajp_web | Gallras i dag (om på) | Förslag |
|---|---|---|---|---|---|
| `ss_emails` | Avsändarens adress och namn, ämne, brödtext | LIUR, kund + L oskopad (029) | – (126) | 119: radera | Som D4 |
| `ss_email_attachments` | Bilagans innehåll som data-URL i databasen | LIU, kund | – (126) | 119: kaskad från mejlet | Som D4; överväg 90 dagar för själva innehållet. Skäl: bilagor kan bära känsliga uppgifter och behövs sällan efter att ärendet stängts |
| `ss_classifications` | Kategori, sentiment, motivering | LIU, kund | – (126) | 119: kaskad | Som D4 |
| `ss_drafts` | Utkast till svar | LIU, kund | – (126) | 119: kaskad | Som D4 |
| `ss_human_reviews` | Redigerad text, anteckning | LIU, kund | – (126) | 119: kaskad | Som D4 |
| `ss_decision_log` | Beslut per mejl; rader utan mejl bär bl.a. gallringens bevis | LIU, kund | – (126) | 119: kaskad för rader med `email_id`; övriga nej | Rader med mejl: som D4. Övriga: 3 år, som gallringsloggen |
| `ss_mailboxes` | Brevlådans adress, krypterat lösenord | LIUR, kund | – (126) | Nej | Så länge kopplingen är aktiv; radera när kunden kopplar bort den |
| `ss_category_rules` | Regler per kategori. Ingen person | LIU, kund | – (126) | Nej | Avtalets löptid |

### D6. Kundens konfiguration och kunskapsbas (B1, B2)

Registrerade: i regel inga; kunskapsbas och kontextdokument kan nämna kundens anställda.

| Tabell | Innehåll, personuppgifter | snajp_app | snajp_web | Gallras i dag | Förslag |
|---|---|---|---|---|---|
| `ss_knowledge_base` | Artiklar, källa | LIUR, kund | – (126) | Nej | Avtalets löptid |
| `ss_kb_skanningar` | Skanning av kundens webbplats, vem som startade | LIU, kund | – (126) | Nej | 12 månader |
| `ss_kb_forslag` | Föreslagna artiklar ur skanningen | LIU, kund | – (126) | Nej | Avvisade: 12 månader. Godkända blir artiklar |
| `ss_channel_configs` | Ton och längd per kanal | LIU, kund + globala rader | – (126) | Nej | Avtalets löptid |
| `ss_channel_connections` | Kanalkoppling, krypterade hemligheter | LIUR, kund | – (126) | Nej | Så länge kopplingen är aktiv |
| `ss_integrations` | Integration, krypterade hemligheter | LIUR, kund | – (126) | Nej | Så länge integrationen är aktiv |
| `ss_sending_domains` | Avsändardomän, avsändarnamn, svarsadress | LIU, kund (061, 068) | – (126) | Nej | Avtalets löptid |
| `agent_configs` | Agentinstruktioner per kund | LIU, kund | – (126) | Nej | Avtalets löptid |
| `agent_context_docs` | Kundens kontextdokument | LIU, kund | – (126) | Nej | Avtalets löptid |

### D7. Leads och utskick (B2; A2 för Snajps egen försäljning)

Registrerade: prospekt och kontaktpersoner hos bolag. `orgnr` kan för en enskild firma
vara ett personnummer. `synk_las` läser `prospects`, `prospect_sources`,
`prospect_status_logg`, `outreach_threads`, `outreach_messages`, `send_queue`, `lead_lists`,
`lead_list_items`, `lead_samtal`, `lead_anteckningar`, `lead_uppgifter`, `leads_job_ledger`.

| Tabell | Innehåll, personuppgifter | snajp_app | snajp_web | Gallras i dag (om på) | Förslag |
|---|---|---|---|---|---|
| `prospects` | Bolag, kontaktnamn, mejl, telefon, roll, motivering, signaler, webbrevision | LIUR, kund + L oskopad (029, 107) | – (126) | 119: radera | 24 månader efter senaste behandling |
| `prospect_sources` | Källans adress, rättslig grund | LIU, kund | – (126) | 119: kaskad | Som `prospects` |
| `prospect_status_logg` | Statusbyten | LIU, kund | – (126) | 119: kaskad | Som `prospects` |
| `lead_anteckningar` | Säljarens anteckningar | LIU, kund | – (126) | 119: kaskad | Som `prospects` |
| `lead_uppgifter` | Uppgifter per prospekt | LIU, kund | – (126) | 119: kaskad | Som `prospects` |
| `lead_samtal` | Samtalsutfall, anteckning | LIU, kund | – (126) | 119: kaskad | Som `prospects` |
| `outreach_threads` | Tråd per prospekt, svarsklass | LIU, kund + L oskopad | – (126) | 119: kaskad | Som `prospects` |
| `outreach_messages` | Utskick och svar, ämne, text, leveransutfall | LIU, kund + L oskopad | – (126) | 119: kaskad | Som `prospects` |
| `send_queue` | Schemalagda utskick | LIU, kund + L oskopad | – (126) | 119: kaskad | Som `prospects` |
| `ss_demolankar` | Demolänk per tråd | LIU, kund | – (126) | 119: kaskad | Som `prospects` |
| `ss_demolank_handelser` | Klick och besök, user agent | LIU, kund (policyn släpper bara L) | – (126) | 119: kaskad | 12 månader. Skäl: beteendedata om en enskild mottagare behövs bara för uppföljningen |
| `ss_avregistreringslankar` | Token och e-post | LIU, kund | – (126) | 119: radera när adressen inte finns kvar i prospekt eller listrad | Som 119 |
| `lead_lists` | Listans beställning och filter | LIUR, kund | – (126) | 119: radera tomma | Som `prospects` |
| `lead_list_items` | Bolag, kontaktnamn, roll, mejl, telefon, utkast, webbrevision | LIUR, kund | – (126) | 119: radera | Som `prospects` |
| `leads_job_ledger` | Jobbstatus, körningens indata, fel | LIUR, kund | – (126) | 119: radera avslutade | 90 dagar efter avslut. Skäl: teknisk liggare, inget behov därefter |
| `leads_sidcache` | Hämtade webbsidor (kan nämna personer) | LIU, kund | – (126) | 119: radera. Koden skriver över gamla rader men raderar dem inte (`storage/postgres.py:3102-3111`) | 30 dagar, i linje med kodens egna livslängder (7–30 dagar, kommentaren i migration 093) |
| `lead_vyer` | Sparade filter. Ingen person | LIUR, kund | – (126) | Nej | Avtalets löptid |
| `offers`, `ab_variants`, `ab_results` | Erbjudanden och A/B-varianter. Ingen person | LIU, kund | – (126) | Nej | Avtalets löptid |
| `saljlista` (före migration 103 `snajp_saljlista`) | Bolag, kontaktperson, nummer, mejl, anteckningar | LIU-grant (default), ingen policy för rollen (0 rader) | arbetsyta (LIUR) | 119: radera | Som `prospects` |
| `dev_flytt_ko` | Kvitto per flyttad rad (typ, id) | LIU, kund | – (126) | Nej | 90 dagar |

Ytor: kundens Leads, listor och samtal i Next; plattformsadmin via adminytan
(`admin_listor.py`, `admin.py` `/prospects/{id}/kedja`, `/leads-underlag`).

### D8. Spärrlistan

| Tabell | Innehåll, personuppgifter | snajp_app | snajp_web | Gallras i dag | Förslag |
|---|---|---|---|---|---|
| `suppressions` | E-post, skäl, koppling till kontakt | LI, kund (030, 109) | – (126) | Aldrig, med flit (119; `gdpr_radera.py` behåller raden) | Så länge kunden (eller Snajp) gör utskick; raderas vid avtalets slut för kundens rader. Skäl: raden är skyddet mot att personen kontaktas igen (art. 21.3) |

`synk_las` läser tabellen.

### D9. Den äldre kampanjmodellen (`000_base_schema.sql`)

Registrerade: kontaktpersoner (prospekt). Arbetsytans tabeller; `snajp_app` har ingen grant
på någon av dem. Koden läser i dag bara `generated_emails` och `contacts` med SQL
(`lib/data/emails.ts:290-371`), och sedan migration 126 har `snajp_web` bara det: L på
`contacts`, L och U på `subject, body, status` i `generated_emails`, och LIU på
`business_contexts` (`lib/data/business-context.ts`). Övriga tabeller i D9: ingen rättighet.

| Tabell | Innehåll, personuppgifter | Gallras i dag (om på) | Förslag |
|---|---|---|---|
| `contacts` | Namn, roll, e-post, LinkedIn | 119: radera (kopplingen i `suppressions` nollas först) | 24 månader efter senaste behandling |
| `generated_emails` | Genererade säljmejl, ämne, text | 119: radera | Som `contacts` |
| `email_events` | Händelser per mejl, metadata | 119: kaskad | Som `contacts` |
| `meetings` | Bokade möten per kontakt | Nej | Som `contacts` |
| `companies` | Bolag. Ingen person | Nej | Avtalets löptid |
| `company_insights` | Analys per bolag | Nej | Ingen kod refererar tabellen. Förslag: ta bort |
| `lead_signals` | Signaler per bolag | Nej | Ingen kod refererar tabellen. Förslag: ta bort |
| `campaigns`, `sequences` | Kampanjer och sekvenser. Ingen person | Nej | Avtalets löptid |
| `sequence_steps` | Steg i sekvens. Ingen person | Nej | Ingen kod refererar tabellen. Förslag: ta bort |
| `business_contexts` | Kundens produkt, målgrupp, erbjudande. Ingen person | Nej | Avtalets löptid |

### D10. Bokföringen (B3)

Registrerade: motparter på kvitton och avsändare av kvittomejl. Originalfilen lagras inte;
bara hash och avlästa fält (`045_bookkeeping.sql`, punkt 1).

| Tabell | Innehåll, personuppgifter | snajp_app | snajp_web | Gallras i dag | Förslag |
|---|---|---|---|---|---|
| `bk_underlag` | Motpart, belopp, avsändare och ämne för kvittomejl | LIUR, kund | – (126) | Aldrig, med flit (119) | Se nedan |
| `bk_verifikat` | Verifikationer | LIUR, kund | – (126) | Aldrig | Se nedan |
| `bk_verifikat_rad` | Konteringsrader | LIUR, kund | – (126) | Aldrig | Se nedan |
| `kvitto_mejl_lasta` | Fingeravtryck av lästa mejl | LIUR, kund | – (126) | Aldrig | 24 månader. Skäl: dubblettspärr, inte räkenskapsinformation |

Förslag för `bk_*`: avtalets löptid, därefter export till kunden och radering. Sju år (BFL
7 kap. 2 §) gäller den som bokför, alltså kunden; `gdpr_radera.py` och 119 behandlar ändå
tabellerna som bokföringsunderlag med sju år. Om Snajp ska vara kundens arkiv är det ett
avtalsbeslut, och då gäller sju år.

### D11. AI-körningar och agentstyrning (ISO 42001)

Registrerade: alla ovan, genom promptar och svar.

| Tabell | Innehåll, personuppgifter | snajp_app | snajp_web | Gallras i dag (om på) | Förslag |
|---|---|---|---|---|---|
| `agent_runs` | Hela indata, utdata, steglogg och grundning per körning; modell, tokens, kostnad | LIU, kund + L oskopad (029) | – (126) | 119: texterna och kopplingarna nollas, raden står kvar | Texterna: 24 månader (som 119). Siffrorna: så länge kostnadsredovisningen kräver. Överväg kortare för texterna, se fynd 2 |
| `agent_feedback` | Kommentar och rättad text | LIU, kund | – (126) | 119: anonymisera | Som `agent_runs` |
| `agent_evals` | Eval-fall med indata och godkänd utdata | LIU, kund | – (126) | 119: radera | Som `agent_runs` |
| `agent_suggestions` | Förslag till kunden | LIU, kund | – (126) | 119: radera | Som `agent_runs` |
| `prompt_lager` | Promptlagrens text per hash; kan bära kunddata | LI, alla (U och R återtagna, migration 101) | – (126) | Nej | Radera lager som ingen kvarvarande `agent_runs`-rad pekar på. Skäl: annars överlever texten anonymiseringen av körningen |
| `agent_global_instructions` | Plattformens instruktioner, vem som ändrade (konto-id) | LIU, alla | – (126) | Nej | Versionshistorik så länge agenten finns |
| `agent_skill_packs` | Versionsmanifest. Ingen person | L, alla (I och U återtagna) | – (126) | Nej | Så länge versionen kan behöva spåras |
| `agent_skill_files` | Kunskapsfiler, publicerad av (namn) | L, alla (IUR återtagna) | – (126) | Nej | Som `agent_skill_packs` |

Ytor: plattformsadminens körningsvy och spårvy (`admin.py` `/runs`, `/runs/{run_id}`).

### D12. Loggar, gallring och synk

| Tabell | Innehåll, personuppgifter | snajp_app | snajp_web | Gallras i dag | Förslag |
|---|---|---|---|---|---|
| `audit_logs` | Plattformsadminens åtkomst: admin-id, kund, rutt, request-id. Äldre radtyper: aktör, metadata | – (IUR återtagna, 123); skrivs bara av två säkerhetsdefinierade funktioner | – (126) | 365 dagar för rader med `kanal` (123); äldre radtyper nej | 365 dagar för alla rader. Skäl: samma säkerhetslogg, samma behov |
| `platform_events` | Fel och händelser, fritext och detalj (kan bära kunddata) | LIUR, alla (026) | – (126) | 119: radera per kunds period | 12 månader |
| `platform_rate_events` | Omfång: kund, konto-id eller IP-adress | LIUR, alla (019) | – (126) | 1 dygn | 1 dygn (oförändrat) |
| `ss_gallringspolicy` | Kundens period, vem som beslutade (namn) | L (IUR återtagna, 119) | – (126) | Nej | Avtalets löptid + 3 år. Skäl: visar vilken period som gällde |
| `ss_gallringslogg` | Antal per tabell och körning. Ingen person | L (IUR återtagna) | – (126) | Nej | 3 år. Skäl: bevis för att gallringen skett |
| `ss_gallringskorning` | Dygnsspärr. Ingen person | L (IUR återtagna) | – (126) | Nej | 3 år |
| `synk_raderingar` | Tabell och primärnyckel för raderade rader | LIU-grant, ingen policy (0 rader); skrivs av trigger (111) | – (126) | Nej | 90 dagar. Skäl: behövs bara tills nästa synk fört raderingen vidare |
| `behandlingsbegransningar` (migration 124, **läggs till i samma PR**) | Begränsning av behandling (art. 18) för en registrerad. Global, inte per kund | L | – (126) | – (ny) | Så länge begränsningen gäller plus tid för att visa att begäran hanterats; tiden obeslutad. Bara ägarrollen skriver, via `scripts/gdpr_radera.py` |
| `mirror_meta` (bara i development, skapas av `scripts/railway_seed_dev.py`, ingen migration) | Spegelmarkören. Ingen person | L, alla (095) | – (126) | – | Så länge spegeln finns |

---

## 4. Kopior utanför tabellerna

| Kopia | Vad den innehåller | Gallring och radering |
|---|---|---|
| Development-databasen (Railway `development`) | En spegel av produktionen med riktiga kunders ärenden, mejladresser och kunskapsbaser (`DEPLOY.md`, avsnittet om spegeln). Rest från `railway_seed_dev.py` (truncate och copy); synken för därefter över de 28 tabellerna i `railway_synk.SYNK` | En radering i `main` förs över vid nästa synk bara för `SYNK`-tabellerna (`synk_raderingar`). Allt annat måste raderas separat (`gdpr_radera.py`, `KOPIOR_SOM_INTE_NAS`). `gallra.py --apply` vägrar köra i en spegel. Samma åtkomstkrets som produktionen ska gälla (`DEPLOY.md`); att den gör det är inte belagt |
| Scheman `synk_kopia_<tid>` i `main` och development | Kopia av varje synkad tabell före första synken (`scripts/railway_synk.py:49`, `:716`) | Nås inte av `gdpr_radera.py` eller gallringen. Ingen rutin raderar dem. Förslag: radera när första synken är verifierad |
| Redis (`Redis-main` i main, `Redis` i development) | Jobbposter, arbetsminne per kundens kund, svarscache, embeddingcache | TTL enligt avsnitt 2. `gdpr_radera.py` når inte Redis |
| Redis Cloud (avvecklas) | Kvarvarande cache och arbetsminne (`docs/registerforteckning.md`, leverantörstabellen) | Raderas med databasen; att det skett är inte belagt |
| Supabase (avvecklad) | Den gamla produktionsdatabasen, historiska uppgifter | Skrivs aldrig till (`CLAUDE.md`). Radering kräver ett eget beslut (`KOPIOR_SOM_INTE_NAS`) |
| Render, Vercel (avvecklade) | Inte avläst vad som ligger kvar | Avvecklade men inte raderade (`drift-och-tillgangar.md` avsnitt 2) |
| Railways loggar | Tjänsternas loggrader | 3–30 dagar beroende på plan; exakt plan inte belagd (`drift-och-tillgangar.md` avsnitt 5) |
| Säkerhetskopior | Inga på någon volym (`bevis/railway-backuper-2026-11-17.txt`) | – |

---

## 5. Fynd som drar åt andra hållet

1. **Ingen kunddata gallras i drift.** `GALLRING_AKTIV` är av, ingen kundpolicy är belagd, och
   `gallra.py` är aldrig körd skarpt. Allt i D4, D5, D7, D9 och D11 ligger alltså kvar utan
   tidsgräns, trots att integritetspolicyn lovar 24 månader.
2. **Tabeller med personuppgifter som 119 inte omfattar ens när gallringen är på:**
   `auth.users`, `profiles`, `workspace_invites`, `trial_paminnelser`,
   `platform_admin_bootstrap`, `password_reset_tokens` (utgångna), `ss_customer_details`,
   `ss_customer_contacts`, `demo_requests`, `webbpool`, `webbpool_fordelad`, `ss_mailboxes`,
   `ss_sending_domains`, `meetings`, `prompt_lager`, `ss_kb_forslag`, `ss_knowledge_base`,
   `agent_context_docs`, `kvitto_mejl_lasta`, `audit_logs` (äldre radtyper) och
   `synk_raderingar`. `prompt_lager` är den viktigaste: när `agent_runs` anonymiseras står
   promptlagrens text kvar och går att nå via hashen.
3. **Rättigheter som verkar för breda:**
   1. ~~`auth.users` är läsbar för `PUBLIC`~~ **Åtgärdat i migration 126 (2026-11-18):**
      `PUBLIC` har ingen rättighet; `snajp_web` läser (inloggningen), `snajp_app` läser bara
      `id` och `email` (påminnelsen om provperioden). `synk_las` och övriga roller når inte
      tabellen. Prövas i CI (`test_snajp_web_rattigheter.py`).
   2. ~~`snajp_web` har LIUR på alla tabeller (030)~~ **Åtgärdat i migration 126:** rollen
      har bara det webbens 67 SQL-satser behöver (13 tabeller, se rolltabellen), och ingen
      rättighet på nya tabeller. En Next-fråga som satte `app.tenant_id` når inte längre
      kundens support- och leadsdata: rollen saknar rättighet på de tabellerna.
   3. `ss_api_keys` (`api_key_lookup`) och `ss_tenants` (`tenant_lookup`) släpper alla rader
      när `app.tenant_id` saknas, för `PUBLIC`. **Sedan 126** saknar `snajp_web` rättighet på
      `ss_api_keys` och läser bara `id, slug, name` i `ss_tenants`. Policyerna är kvar för
      `snajp_app` (adminvägen, punkt 5).
   4. `password_reset_tokens` är `using (true)` för `snajp_web`: alla kontons tokenhashar.
   5. Oskopad `snajp_app` läser alla kunders `agent_runs`, `ss_emails`, `ss_tickets`,
      `prospects` och utskick. Det är adminvägen, och skyddet ligger i API-lagret
      (`require_master_key`), inte i databasen.
   6. `alter default privileges` (009) ger `snajp_app` LIU på varje ny tabell automatiskt.
      Det är RLS utan policy som skyddar tills någon lägger en policy; en policy till
      `PUBLIC` öppnar då tabellen för båda approllerna.
   7. Skripten, däribland `gdpr_radera.py` och `gallra.py`, kör som superanvändaren
      `postgres` över den publika TCP-proxyn (`scripts/gdpr_verktyg.py:89`).
4. **Fyra tabeller används inte av någon kod** (`company_insights`, `lead_signals`,
   `sequence_steps`, `billing_payment_methods`; ingen träff i `snajp-support/app`, `lib`,
   `app`, `components` eller `scripts`). De bär ingen eller lite data, men en tabell som
   ingen använder är också en tabell som ingen gallrar.
5. **Development är en fullständig kopia av personuppgifterna** och får main:s raderingar
   bara för 28 tabeller. En radering enligt art. 17 är inte klar förrän den gjorts även där.

---

## Det Anton beslutar

- Lagringstiden per datamängd ovan, och om standardtiden för kunddata (D4, D5, D7, D9, D11)
  ska vara integritetspolicyns 24 månader. Beslutsunderlaget finns i
  `underlag/beslut/d-gallringsperiod.md` (osignerat).
- Om bokföringstabellerna (D10) ska sparas i sju år hos Snajp eller lämnas till kunden vid
  avtalets slut.
- Lagringstiden för `behandlingsbegransningar` efter att en begränsning hävts.
- Om `GALLRING_AKTIV` ska slås på i `main`, och vilken period som skrivs i
  `ss_gallringspolicy` för varje befintlig kund.
- Vem som ska ha åtkomst: vilka personer som är plattformsadmin, vem som får `.env.deploy`
  och repots hemligheter. (Läsrätten för `PUBLIC` på `auth.users` och `snajp_web`-rollens
  breda rättigheter är smalnade av i migration 126 på Antons uppdrag 2026-11-18, fynd 3.)
- Om de oanvända tabellerna (`company_insights`, `lead_signals`, `sequence_steps`,
  `billing_payment_methods`) och kopiorna `synk_kopia_<tid>` ska tas bort.
