# Underlag 01: leads-sidans datamodell och livscykel

Underlag till Snajp CRM, skrivet 2026-11-25 i worktree `snajp-crm-dd0d83`
(gren `claude/snajp-crm-dd0d83`, HEAD `9970d304`). Ingen befintlig fil är ändrad.

**Läsanvisning.** Allt som står med `fil:rad` har jag läst i koden. Det som är
en slutsats eller ett antagande är märkt **[antagande]** eller **[att verifiera]**.
Sökvägar är relativa till repots rot. Python-backenden ligger under
`snajp-support/app/`, migrationerna under `db/migrations/`.

---

## 0. Det viktigaste först (för den som ska bygga)

1. **Det finns ingen bolagstabell.** Ett "bolag" i leads lever på två ställen:
   som rad i `prospects` (Iris-leads, ringlistan, listornas bakgrundsprospekt) och
   som rad i `lead_list_items` (listor, inklusive kundens befintliga kunder som en
   lista med `lead_lists.kalla = 'crm'`). Identiteten är **inte** en databasnyckel.
   Den räknas i kod av `snajp-support/app/leads/upptagna.py`: orgnr när det finns,
   annars namnet utan bolagsform.
2. **Det finns inget unikt index på orgnr någonstans.** "Ett bolag, ett ställe"
   upprätthålls av ett advisory-lås plus en full läsning av kundens prospekt i
   `PostgresStorage.create_prospect` (`snajp-support/app/storage/postgres.py:2656-2669`).
3. **"Befintliga kunder" = en leadslista med `kalla='crm'`** (migration 098).
   Den laddas upp via `POST /api/leads/import` med `kalla: "crm"` och utesluts från
   Iris, listbygget, importer och listkopior genom `upptagna.hamta()` →
   `storage.lista_upptagna_bolag()` (`postgres.py:3641-3653`).
4. **orgnr normaliseras på minst sex olika sätt** (två i TypeScript, fyra i Python
   plus en genererad kolumn i SQL). De är inte överens om sekelprefix eller
   personnummer. Se avsnitt 5. CRM:et behöver en enda kanonisk nyckel.
5. **Namnen `companies` och `contacts` är upptagna** av gamla, workspace-skopade
   tabeller i `db/migrations/000_base_schema.sql:47-73`. De används inte av
   backenden (ingen träff på `from companies` i `snajp-support/app`) men finns i
   schemat. Nya CRM-tabeller måste heta något annat.
6. **Det finns redan CRM-ytor att bygga vidare på**: Leads Suite med tidslinje,
   anteckningar, uppgifter och sparade vyer (`snajp-support/app/api/leads_suite.py`,
   migration 086), samtalsloggen `lead_samtal` (107), konversationshändelserna
   `lead_handelser` (149), och envägssynk ut till HubSpot/Pipedrive
   (`snajp-support/app/leads/crm_synk.py`). Tvåvägssynk IN finns inte.

---

## 1. Tabellerna

Gemensamt mönster: varje leadstabell har `tenant_id uuid not null references
ss_tenants(id)`, RLS `enable` + `force`, och policyn `tenant_isolation` med
`tenant_id = nullif(current_setting('app.tenant_id', true), '')::uuid` för USING
och WITH CHECK. NULLIF-vakten lades på i efterhand av `028_rls_empty_string_guard.sql`
(dynamiskt över alla policyer som nämner `app.tenant_id`) och
`20260919100000_068_rls_nullif_vakt.sql:16-39`. Backenden skopar varje anrop med
`self._scoped(tenant_id)` i `postgres.py` (sätter `app.tenant_id`). API-nyckeln per
kund är headern `X-API-Key` (`snajp-support/app/api/deps.py:62-72`, `require_tenant`);
master-nyckeln får inte röra kunddata.

Alla tabeller nedan är också med i tvåvägssynken mellan development och main
(`20261010120000_111_tvavagssynk.sql:51-75`): kolumnen `synk_andrad_at`, triggern
`synk_markera` och raderingsloggen `synk_raderingar`. **En ny CRM-tabell som ska
speglas måste läggas till på samma sätt** (och i `scripts/railway_synk.py: SYNK`
enligt kommentaren i `20261122090000_149_iris_konversationer.sql:30-32`, och få
läsrätt för rollen `synk_las`, migration 122).

### 1.1 `prospects` (Iris-leads, ringlistan, listornas bakgrundsposter)

Skapad `010_agent_backend.sql:100-114`. RLS i loopen `010_agent_backend.sql:210-226`.

| Kolumn | Typ / villkor | Migration |
|---|---|---|
| `id` | uuid pk, `gen_random_uuid()` | 010 |
| `tenant_id` | uuid not null → `ss_tenants(id)` | 010 |
| `company_name` | text not null | 010 |
| `contact_name`, `contact_email` | text | 010 |
| `language_state` | text not null default `'sv'`, check `('sv','en_confirmed')` | 010 |
| `status` | text not null default `'new'`, check se avsnitt 4 | 010:109-110 |
| `created_at` | timestamptz default now() | 010 |
| `icp_fit` | numeric(3,2), 0–1 | `024_prospect_icp_fit.sql:12-14` |
| `qualified` | boolean | 024:16-17 |
| `disqualifiers` | text[] not null default `'{}'` | 024:19-20 |
| `orgnr`, `ort`, `postnr`, `sni`, `website` | text | `031_prospect_nischfalt.sql:28-33` |
| `anstallda` | integer | 031:34 |
| `omsattning` | bigint | 031:35 |
| `score_breakdown` | jsonb not null default `'[]'` | 031:40 |
| `score_total` | integer | 031:41 |
| `foretagsnyckel` | text **generated always stored** | 031:50-57 |
| `origin` | text not null default `'manual'`, check se avsnitt 4 | `039_prospect_origin.sql:23-25`, senast `20261008090000_107_crm_samtal.sql:29-31` |
| `contact_role`, `contact_level`, `contact_form_url` | text; `contact_level` check `('named_role_match','named_other','role_address','contact_form')` | `058_prospect_kontaktniva.sql:19-24` |
| `motivering` | text | `20260930100000_079_iris_bedomning.sql:15-19` |
| `niva` | text check `('A','B','C')` | 079 |
| `profil_version` | text | 079 |
| `jev` | jsonb | 079 |
| `contact_phone` | text | `20261001200000_081_kontakt_telefon.sql:9-10` |
| `lagesbeskrivning` | text | `20261003110000_083_iris_lagesbeskrivning.sql:12-14` |
| `signaler` | jsonb | 083 |
| `webbrevision` | jsonb (**hemlig**, avsnitt 6) | `20261005110000_094_prospekt_webbrevision.sql:8-9` |
| `arkiverad_at` | timestamptz | 107:27 |
| `lan` | text (**hemlig fördelning**, avsnitt 6) | `20261008150000_108_webbpool.sql:17` |
| `synk_andrad_at` | timestamptz not null default now() | 111 |
| `behandlad_at` | timestamptz | `20261119220000_142_varje_andring_ar_behandling.sql:70` (loop) **[att verifiera att prospects ingår i loopens lista]** |

`foretagsnyckel` (`031_prospect_nischfalt.sql:50-57`):

```sql
coalesce(
  nullif(regexp_replace(coalesce(orgnr, ''), '\D', '', 'g'), ''),
  nullif(lower(split_part(coalesce(contact_email, ''), '@', 2)), '')
)
```

Den är karensnyckeln för `send_guard` regel 5 och får inte skrivas av kod
(kommentaren 031:67-70). Observera: den tar **inte** bort sekelprefixet, så
`16556824-9022` och `556824-9022` ger olika nycklar.

Index: `prospects_tenant_idx (tenant_id)` 010:114; `prospects_qualified_idx
(tenant_id, qualified, icp_fit desc)` 024:24-25; `prospects_foretagsnyckel_idx
(tenant_id, foretagsnyckel)` 031:59-60; `prospects_postnr_idx (tenant_id,
left(postnr,3))` 031:63-64; `prospects_origin_idx (tenant_id, origin)` 039:35-36;
`prospects_niva_idx (tenant_id, niva)` 079:21; `prospects_kund_skapad_idx
(tenant_id, created_at desc, id)` `20261110090000_115_lasvagsindex.sql:34-35`.
**Inget unikt index** på orgnr, namn eller foretagsnyckel.

Grants: `snajp_app` har select/insert/update (default privileges, migration 009
enligt kommentar i 010:237-240) och `delete` sedan 107:57.

Skrivbara profilfält via `create_prospect(profil=...)` är en allowlist,
`_PROSPEKT_PROFILFALT` (`postgres.py:54-78`): `orgnr, ort, postnr, sni, website,
anstallda, omsattning, contact_role, contact_level, contact_form_url,
contact_phone, lan`. Läsbara kolumner i projektion: `_PROSPEKT_LASKOLUMNER`
(`postgres.py:82-90`). `update_prospect` (`postgres.py:2804-2840`) tar bara
`status, icp_fit, qualified, disqualifiers, origin, orgnr, website,
contact_email, contact_name, contact_role, contact_level, contact_form_url` och
skriver `prospect_status_logg` i samma transaktion när status ändras
(`postgres.py:2850-2858`).

### 1.2 Barntabeller till `prospects`

Alla har `prospect_id uuid not null references prospects(id) on delete cascade`,
tenant-kolumn och `tenant_isolation`-RLS.

| Tabell | Kolumner | Källa |
|---|---|---|
| `prospect_sources` | `id, tenant_id, prospect_id, source_url text not null, retrieved_at, source_type` check `('company_website','public_news','business_register','job_signal','manual_note','enrichment_adapter','linkedin','other')`, `lawful_basis text not null` | `010_agent_backend.sql:116-132` |
| `lead_anteckningar` | `id, tenant_id, prospect_id, text not null, created_at`; index `(tenant_id, prospect_id)` | `20261003140000_086_leads_suite.sql:22-30` |
| `lead_uppgifter` | `id, tenant_id, prospect_id, titel not null, forfaller date, klar boolean default false, klar_at, created_at` | 086:32-43 |
| `prospect_status_logg` | `id, tenant_id, prospect_id, fran text, till text not null, kalla` check `('kod','manuell','import')`, `created_at` | 086:45-55 |
| `lead_vyer` | `id, tenant_id, namn, filter jsonb, created_at` (ingen prospect_id) | 086:57-64 |
| `lead_samtal` | `id, tenant_id, prospect_id, utfall` check `('ej_svar','aterkom','ej_intresserad','kontakta_inte','mote')`, `aterkom_datum date, anteckning text, created_at`; index `(tenant_id, prospect_id, created_at)`; grant select, insert | `20261008090000_107_crm_samtal.sql:33-57` |
| `lead_handelser` | `id, tenant_id, prospect_id, thread_id → outreach_threads(id) on delete cascade, typ` check (14 värden, avsnitt 4), `kalla` check `('kod','manuell')`, `detalj jsonb, notis boolean, last_at, created_at`; tre index; grant select, insert, update | `20261122090000_149_iris_konversationer.sql:42-75` |
| `outreach_threads` / `outreach_messages` / `send_queue` | mejltrådarna; `outreach_threads.steg` check `('svarat','aterkom','mote','ej_intresserad','kontakta_inte')`, `aterkom_datum` (149:36-40); `outreach_messages.created_at`, `kasserad_at` (107:20-25) | 010 §7, 107, 149 |

`lead_list_items.prospect_id` pekar också på prospektet, men med
`on delete set null` (`20261010090000_110_listrader_i_listan.sql:13-14`).

### 1.3 `lead_lists`

Skapad `060_leadlists.sql:40-54`.

| Kolumn | Typ / villkor | Migration |
|---|---|---|
| `id` | uuid pk | 060 |
| `tenant_id` | uuid not null → ss_tenants on delete cascade | 060 |
| `titel` | text not null | 060 |
| `icp` | jsonb not null default `'{}'` (frusen beställning) | 060 |
| `antal` | integer not null check `between 1 and 200` | 060 |
| `status` | text not null default `'bestalld'`, check `('bestalld','byggs','klar','fel')` | 060:48-49 |
| `felorsak` | text | 060 |
| `is_test` | boolean not null default false | 060 |
| `created_at`, `completed_at` | timestamptz | 060 |
| `kalla` | text not null default `'sok'`; check i dag `('sok','kombinerad','import','crm','saljlista','webbpool')` | `20261003100000_082_listor_kombinerade.sql:14-16`, `20261008150000_108_webbpool.sql:24-27` |
| `kallistor` | uuid[] | 082:17 |
| `kontaktfilter` | text check `null` eller `('alla','telefon','mejl','bada')` | 082:18-19 |
| `processering` | jsonb (förlopp för Processa om / Skapa utkast) | 110:21-22 |
| `importinfo` | jsonb (importkvittot, högst 20 kB) | `20261123110000_152_import_avtalsslut_extra.sql:21-22` |
| `synk_andrad_at` | | 111 |

Index `lead_lists_tenant_idx (tenant_id, created_at desc)` 060:82-83. RLS 060:88-93,
NULLIF i 068:31-34. Grants select/insert/update/delete för `snajp_app` 060:102.

Observera `antal`-taket 200: importen och kombineringen skriver `min(len(rader), 200)`
och låter `item_count` bära det riktiga antalet (`leads_suite.py:497-499`,
`leads.py:4638-4640`).

### 1.4 `lead_list_items`

Skapad `060_leadlists.sql:56-80`.

| Kolumn | Typ / villkor | Migration |
|---|---|---|
| `id` | uuid pk | 060 |
| `list_id` | uuid not null → lead_lists on delete cascade | 060 |
| `tenant_id` | uuid not null → ss_tenants on delete cascade | 060 |
| `item_typ` | text not null default `'bolag'`, check `('bolag','privatperson')` (bara `bolag` skrivs) | 060:63 |
| `company_name` | text not null | 060 |
| `website, ort, contact_name, contact_role, contact_email` | text | 060 |
| `contact_level` | text, samma check som prospects | 060:70-72 |
| `source_name, source_url, signal, signal_detalj` | text (fri) | 060:75-78 |
| `created_at` | timestamptz | 060 |
| `contact_phone`, `orgnr` | text | 081:12-14 |
| `utkast` | jsonb | `20261007140000_106_listutkast.sql:15-16` |
| `lan`, `postnr`, `webbniva` | text (webbniva/lan **hemliga**) | 108:19-21 |
| `webbrevision` | jsonb (**hemlig**) | 108:22 |
| `prospect_id` | uuid → prospects on delete **set null** | 110:14 |
| `kallor` | jsonb not null default `'[]'` | 110:15 |
| `processad_at` | timestamptz | 110:16 |
| `behandlad_at` | timestamptz | `20261119210000_141_utkast_ar_behandling.sql:39` |
| `avtalsslut` | date | 152:18 |
| `extra` | jsonb (kundens omappade kolumner) | 152:19 |
| `synk_andrad_at` | | 111 |

Index: `lead_list_items_list_idx (list_id, created_at)` 060:84-85;
`lead_list_items_orgnr_idx (list_id, orgnr)` 082:22-23 (icke-unik);
`lead_list_items_tenant_idx (tenant_id)` 098:18-19 (för uteslutningen);
`lead_list_items_prospect_idx (tenant_id, prospect_id) where prospect_id is not null`
110:18-19. RLS 060:95-100, NULLIF 068:36-39.

Fält som `uppdatera_listrad` får skriva: `LISTRAD_UPPDATERBARA`
(`snajp-support/app/storage/base.py:102-107`): `website, contact_name,
contact_role, contact_email, contact_phone, contact_level, signal_detalj, orgnr,
webbniva, webbrevision, kallor, processad_at, prospect_id`. JSONB-kolumner:
`LISTRAD_JSONB = ("webbrevision", "kallor")` (`base.py:109`).

### 1.5 `leads_job_ledger` (körningar och jobb)

Skapad `059_leads_job_ledger.sql:34-48`: `job_id text pk, tenant_id, prospect_id uuid`
(null för batchens föräldrajobb), `scope text not null` (fri text med flit, 059:39-42),
`status` check `('queued','processing','completed','failed')`, `created_at,
completed_at`. Utökad i `20261001100000_080_korningar.sql:21-25`: `korning jsonb`
(Iris-motorns tillstånd), `error text`, `is_test boolean`, `updated_at`. Index
`leads_job_ledger_tenant_idx (tenant_id, created_at desc)` 059:60-61 och
`leads_job_ledger_korningar_idx (tenant_id, created_at desc) where scope in
('batch','lista')` 080:34-36. RLS 059:64-67, NULLIF 068:26-29.

### 1.6 Spärrlistan: `suppressions` och `behandlingsbegransningar`

- `suppressions` (`000_base_schema.sql:170-177`): `id, workspace_id → workspaces
  (nullbar sedan 049), contact_id → contacts, email text not null, reason text not
  null, created_at`. `tenant_id uuid → ss_tenants on delete cascade` tillagd i
  `030_suppressions_tenant_scope.sql:19-20` med backfill. Index
  `suppressions_tenant_email_idx (tenant_id, lower(email))` 030:36-37. Policy
  `suppressions_tenant_isolation ... for all to snajp_app` 030:43-47 (dashboarden
  läser på `workspace_id` via den äldre policyn i 000:292). Spärren är **per
  e-postadress**, inte per bolag eller orgnr.
- `behandlingsbegransningar` (`20261118140000_124_behandlingsbegransning.sql`):
  global (ingen tenant_id), `email, skal, begard_at, havd_at, havd_skal`, unikt
  index på `lower(email) where havd_at is null`; `snajp_app` får bara läsa; skrivs
  bara av `scripts/gdpr_radera.py`. Gäller alla kunder (GDPR art. 18).
- Läsning: `list_suppressions` (`postgres.py:1453-1458`) och `list_begransade`
  (`postgres.py:1460-1467`) ger båda en mängd casefoldade adresser.
- Bolagsnivåns spärr finns inte som tabell. Den motsvaras av
  `prospects.status = 'suppressed'` (Kontakta inte) och `arkiverad_at`, samt
  karensen per `foretagsnyckel` i `send_guard` regel 5 (031:42-49).

### 1.7 Webbpoolen (plattformsnivå, ingen tenant)

`webbpool` (pk `doman`, kolumner `website, company_name, orgnr, ort, postnr, lan,
sni, webbniva` check `('akut','dalig','bra','mycket_bra','okand','avvecklad')`,
`webbrevision, forsta_kalla_typ` check `('korning','lista'), bedomd_at, sedd_at`)
och `webbpool_fordelad (doman, mottagare → ss_tenants, list_id, fordelad_at)`,
`108_webbpool.sql:29-52`. Policy `using (true)` bara för `snajp_app`, aldrig
`snajp_web` (108:63-76). Får aldrig bära personfält (INV-SEC-008,
`webbpool.py:45-50`). Inte relevant för CRM-synken, men CRM-bolag får aldrig läcka
in i den.

### 1.8 Gamla tabeller som krockar i namn

`public.companies` och `public.contacts` (`000_base_schema.sql:47-73`), skopade
på `workspace_id`, med `lead_score`, `status 'researching'` m.m. Ingen backendkod
läser dem (sökt i `snajp-support/app`, `lib`, `app`, `components`). **[antagande]**
De är rester från mock-tiden. CRM:et bör inte återanvända dem och inte heller
namnen.

---

## 2. Hur ett bolag identifieras, och "ett bolag på ett ställe"

### 2.1 Nycklarna i `upptagna.py`

`snajp-support/app/leads/upptagna.py`:

- `nyckel(namn)` (rad 30-38): NFKC, casefold, `&` → ` och `, allt som inte är
  `\w` blir mellanslag. Bolagsformer i slutet stryks (`_BOLAGSFORMER`, rad 23-26:
  `ab, aktiebolag, publ, hb, handelsbolag, kb, kommanditbolag, ek, för,
  ekonomisk, förening, ef, enskild, firma, i, likvidation`), AB/Aktiebolag också
  först. "Byggarna Berggren AB" och "byggarna berggren" blir samma.
- `orgnr_nyckel(orgnr)` (rad 41-46): bara siffror; **tolv siffror → de två första
  stryks oavsett vilka de är**; giltig bara vid exakt tio siffror, annars `None`.
  Returnerar `"orgnr:5568249022"`. Ingen Luhn-kontroll.
- `nycklar(uteslut)` (rad 49-57): blandad mängd; poster som börjar med `orgnr:`
  står kvar, allt annat blir namnnycklar.
- `bolagsnycklar(rader)` (rad 60-69): för varje rad med `company_name`/`orgnr`
  läggs **både** namnnyckeln och orgnr-nyckeln i mängden.
- `upptagen(sedda, namn, orgnr)` (rad 72-74): sant om **namnnyckeln ELLER
  orgnr-nyckeln** finns i mängden.
- `samma_bolag(rad, namn, orgnr)` (rad 77-84): om båda sidor har ett giltigt
  orgnr avgör **bara orgnr**; annars namnnyckeln.
- `hamta(storage, tenant_id)` (rad 87-90): `bolagsnycklar(await
  storage.lista_upptagna_bolag(tenant_id))`.

Skillnaden är viktig: `samma_bolag` (dubblettgrinden) låter två bolag med samma
namn och olika orgnr vara två bolag, men `upptagen` (uteslutningen) fäller dem på
namnet. Ett CRM med många kunder kommer därför att utesluta fler bolag ur Iris
än de som faktiskt är kunder när namnen är vanliga. **[slutsats ur koden]**

Domän används inte som identitet i `upptagna.py`. Domänen används i
`foretagsnyckel` (fallback när orgnr saknas, 031:50-57), i `crm_synk._doman`
(`crm_synk.py:32-37`) och som primärnyckel i `webbpool`.

TypeScript-spegeln av namnnyckeln: `bolagsnyckel()` i `lib/leads/importrader.ts:57-67`
(samma bolagsformer, rad 47-50). Dubbletter inom en importfil slås ihop på
namnnyckel eller `orgnr:<siffror>` (bara när orgnr innehåller bindestreck, alltså
validerat svenskt nummer), och raden med mejl (vikt 2) eller telefon (vikt 1)
vinner (`importrader.ts:130-153`).

### 2.2 Dubblettgrinden i `create_prospect`

`PostgresStorage.create_prospect` (`postgres.py:2633-2719`):

1. Om `origin` inte är `'example'` eller `'test'`: `pg_advisory_xact_lock(hashtext('prospekt:' || tenant_id))`
   (rad 2662), sedan läses **alla** kundens prospekt utom example/test (rad
   2663-2667), och för varje rad anropas `upptagna.samma_bolag(rad, company_name,
   profil.get("orgnr"))` (rad 2668).
2. Träff → det befintliga prospektet returneras med `"fanns_redan": True` (rad
   2669). Inget skrivs, ingen fältsammanslagning.
3. Annars `insert into prospects (...) returning *` med profilfälten i samma sats
   (rad 2670-2685). Fallback utan `origin`-kolumnen om migration 039 saknas
   (rad 2686-2718).

Minneslagret speglar samma regel (`snajp-support/app/storage/memory.py:1878-1886`),
utan lås.

Kommentaren på `postgres.py:2660-2661` säger själv att en nyckelkolumn med unikt
index behövs när en kund har tiotusentals prospekt. Arkiverade prospekt
(`arkiverad_at`) räknas med i grinden; det är avsiktligt (107:9-10: "står kvar i
uteslutningsmängden").

### 2.3 Var bolaget "bor" (ett ställe)

- Iris-lead: `prospects`-rad med `origin` `'iris'`/`'manual'`/`'inkorg'`, syns i
  Iris-tabellen.
- Listans bolag: `lead_list_items`-rad. När raden får research eller utkast lyfts
  den till ett **bakgrundsprospekt** via `_befordra_listrad`
  (`snajp-support/app/api/leads.py:4801-4860`): `create_prospect` med
  `origin=_listans_origin(lista)` (`'test'`, `'import'` eller `'lista'`,
  `leads.py:4793-4798`), och `lead_list_items.prospect_id` sätts. Iris-tabellen
  döljer listkopplade prospekt (`storage.listkopplade_prospekt`,
  `postgres.py:3529-3535`, och `listvy.synliga` i `leads.py:654-660`), så bolaget
  syns på ett ställe: i listan. Ett befintligt Iris-lead kopplas inte till
  listraden (`leads.py:4830-4835`).
- Omprövning (Processa om) som flyttar en listrad till Iris eller ringlistan
  raderar inte raden utan sätter `signal = 'flyttad'` och lägger till
  `" → flyttad till Iris <datum>"` i `signal_detalj` (`markera_listrad_flyttad`,
  `postgres.py:3620-3628`; `omprova.py:31-47`). Flyttade rader döljs i listor
  (`postgres.py:3480`, `3592`) men räknas fortfarande i uteslutningen.
- Ringlistan: prospekt med `origin = 'ring'` (107:12-13), skapade i
  `_spara_listspar` (`leads.py:3476-3519`).

### 2.4 Andra dedupregler (inte samma som upptagna)

- Kombinera listor: `_dedupnyckel` (`leads.py:4544-4548`): `orgnr:<alla siffror>`
  utan prefixhantering, annars `namn:<casefold>` **utan** bolagsformsstrykning.
- `send_guard` regel 5: `prospects.foretagsnyckel` (siffror ur orgnr, annars
  e-postdomänen).
- `crm_synk` mot HubSpot/Pipedrive matchar bara på exakt bolagsnamn
  (`crm_synk.py:47-54`, `102-104`), inte orgnr.

---

## 3. "Befintliga kunder": lagring, uppladdning, uteslutning

### 3.1 Lagring

En rad i `lead_lists` med `kalla = 'crm'` (`20261006120000_098_listor_crm.sql:12-15`)
och dess rader i `lead_list_items`. Inga egna kolumner. Kolumnerna som kan fyllas
från filen: `company_name, orgnr, contact_name, contact_role, contact_email,
contact_phone, website, ort` (`_IMPORTFALT`, `leads_suite.py:351-353`) plus
`avtalsslut` och `extra` (152). Kolumnen `status` i importraden saknar plats och
slängs (`leads_suite.py:349-350`).

### 3.2 Uppladdning

Klient: `components/leads/CrmKundlista.tsx` renderar `<ImportLista kalla="crm" />`
(rad 65), som läser filen i webbläsaren (`lib/leads/importfil.ts: lasImportfil`,
CSV/XLSX/HTML/XML, max 15 MB, rad 34, 305), gissar kolumner
(`lib/leads/importmallar.ts: gissaKolumner`, rad 370, en aliaslista över
HubSpot/Pipedrive/Salesforce/Upsales m.fl., rad 1-15), tolkar värden
(`lib/leads/importvarden.ts`) och bygger rader (`lib/leads/importrader.ts:
tolkaRader`, rad 72). Anropet går genom Next-proxyn `app/api/snajp-support/[...path]`
till FastAPI.

Server: `POST /api/leads/import` (`leads_suite.py:412-511`), body `ImportRequest`
(rad 93-106): `titel`, `rader` (1–5000), `kalla: "import" | "crm"`, `list_id`
(fortsättning i delar), `importinfo`, `ta_med_leads`.

För `kalla = "crm"`:
- Ingen kontroll mot befintliga kunder, leads eller spärrade adresser (de körs bara
  när `kalla == "import"`, rad 453-455 och 467-472).
- Dubbletter inom filen och mot listans redan sparade rader slås ihop med
  `upptagna.upptagen(sedda, ...)` (rad 458, 473-474).
- `create_lead_list(kalla="crm", antal=min(n,200), importinfo=...)` (rad 492-502),
  `add_lead_list_item` per rad (rad 506-507), `status = 'klar'` (rad 508).
- **orgnr valideras inte på servern**: fältet är `str | None, max_length=200`
  (rad 70) och skrivs som det kom. Valideringen sker bara i webbläsaren
  (`tolkaOrgnr`).
- Förhandsgranskningen `POST /api/leads/import/granska` returnerar bara `null`-flaggor
  för en CRM-lista (rad 521-522).

En CRM-lista kan inte lyftas till Iris, kombineras eller få rader befordrade:
`_kraev_ej_crm` ger 409 (`leads.py:4577-4584`). Den kan tas bort med
`DELETE /api/leads/listor/{list_id}` (`leads_massatgard.py:96-113`); då blir
bolagen lediga för Iris igen.

Det finns **ingen API-väg för att uppdatera** en CRM-lista inkrementellt (ändra en
rad, ta bort en kund som slutat). Fortsättning med `list_id` lägger bara till.

### 3.3 Uteslutningen

Källan är `lista_upptagna_bolag` (`postgres.py:3641-3653`):

```sql
select company_name, orgnr, 'lead' as kalla, null::uuid as list_id
  from prospects where tenant_id = $1
union
select i.company_name, i.orgnr,
       case when l.kalla = 'crm' then 'crm' else 'lead' end, i.list_id
  from lead_list_items i join lead_lists l on l.id = i.list_id
 where i.tenant_id = $1
```

Alla prospekt (alla origin, även arkiverade och example/test) och alla listrader
(alla kallor, även flyttade). Kontrakt i `base.py:1254-1262`.

Anropen av `upptagna.hamta` / uteslutningen, ordagrant var:

| Var | Vad |
|---|---|
| `leads.py:2733-2737` | Batchens egna bolag: `uteslut_namn` till `discovery.hitta_bolag` |
| `leads.py:2748` | Sista kontrollen före `_skapa_prospekt_ur_kandidat` |
| `leads.py:3353-3361` | Iris-körningens sökrunda: `upptagna.hamta` plus tratten, listspåret, andra körningars bolag och nyligen bortvalda |
| `leads.py:3407-3412` | Sista kontrollen per kandidat, läses om precis före skrivningen; träff → tratt `steg: "dubblett"` |
| `leads.py:3496-3505` | `_spara_listspar` (ringlistan och Ej kvalificerade) |
| `leads.py:5232-5257`, `5306-5311` | Listbygget (`POST /api/leads/listor`) |
| `sources/merinfo.py:729-770` | Registersökningen (`sedda = upptagna.nycklar(uteslut)`, `upptagen(...)` per listrad) |
| `discovery.py:663-682`, `1524-1534`, `1728-1792` | Sök-federationen |
| `leads_suite.py:393-402`, `467-474`, `524-541` | Importen av `kalla='import'` (`redan_kund`, `redan_lead`) och granskningen |
| `admin_listor.py:72-80` | Plattformsadmins kopia/flytt av lista till annan kund |
| `admin_flytt.py:628-635` | Flytt till main |
| `webbpool.py:352-360` | Webbyråns veckolista |

Ordningen i importen (`leads_suite.py:465-476`): utan bolagsnamn → `redan_kund`
→ `sparrade` (mejl i suppressions eller begränsningar) → `redan_lead` (om inte
`ta_med_leads`) → `dubbletter`.

---

## 4. Statusvärden, ordagrant

### Prospekt
- `prospects.status` (010:109-110): `'new'`, `'researching'`, `'ready'`,
  `'contacted'`, `'replied'`, `'meeting'`, `'won'`, `'lost'`, `'suppressed'`.
  `researching` visas också härlett när ett `new`-prospekt har ett köat
  researchjobb (`leads.py:682-686`). PATCH tar fri sträng
  (`snajp-support/app/api/schemas.py:438-445`), databasens check fäller okända.
- Avslutade/klara: `follow_up_generator.py:149` `{"replied","meeting","won","lost","suppressed"}`;
  `samtal.py:38` `{"lost","suppressed","meeting","won"}`.
- Samtalsutfall → status: `samtal.AVSLUTANDE` (`samtal.py:33`):
  `ej_intresserad → lost`, `kontakta_inte → suppressed`, `mote → meeting`.
- Konversationssteg → status: `konversation.STATUS_FOR_STEG`
  (`konversation.py:43-49`): `svarat → replied`, `mote → meeting`,
  `aterkom → replied`, `ej_intresserad → lost`, `kontakta_inte → suppressed`.
- `prospects.origin` (107:30-31): `'manual'`, `'example'`, `'import'`, `'test'`,
  `'inkorg'`, `'lista'`, `'iris'`, `'ring'` (check `not valid`, äldre rader
  prövas inte).
- `prospects.niva`: `'A'`, `'B'`, `'C'` (079:17).
- `prospect_status_logg.kalla`: `'kod'`, `'manuell'`, `'import'` (086:51).
- `contact_level`: `'named_role_match'`, `'named_other'`, `'role_address'`,
  `'contact_form'` (058; `discovery.KONTAKTNIVAER`, `discovery.py:43`).
- `lead_samtal.utfall`: `'ej_svar'`, `'aterkom'`, `'ej_intresserad'`,
  `'kontakta_inte'`, `'mote'` (107:37).
- `outreach_threads.steg`: `'svarat'`, `'aterkom'`, `'mote'`,
  `'ej_intresserad'`, `'kontakta_inte'` (149:39-40).
- `lead_handelser.typ`: `'svar'`, `'klassad'`, `'utkast'`, `'utkast_ersatt'`,
  `'utkast_kasserat'`, `'utkast_aterstallt'`, `'utkast_redigerat'`,
  `'generering_startad'`, `'generering_fel'`, `'skickat'`, `'steg'`, `'mote'`,
  `'overlamnat'`, `'extern'` (149:46-50).

### Listor och listrader
- `lead_lists.status`: `'bestalld'`, `'byggs'`, `'klar'`, `'fel'` (060:48-49).
  `completed_at` sätts vid `klar`/`fel` (`postgres.py:3465`).
- `lead_lists.kalla`: `'sok'`, `'kombinerad'`, `'import'`, `'crm'`,
  `'saljlista'`, `'webbpool'` (108:27; minneslagret `memory.py:2449`).
- `lead_lists.kontaktfilter`: `'alla'`, `'telefon'`, `'mejl'`, `'bada'`.
- `lead_lists.processering` (jsonb, ingen check): `typ` t.ex. `"utkast"`,
  `status` `"pagar"` → `"klar"` eller `"fallen"` (`leads.py:4700-4718`).
- `lead_list_items` har **ingen statuskolumn**. Läget bärs av `signal` (fri text;
  värden i koden: `"listspar"`, `"ring"`, `"flyttad"`, `"rekryterar"`,
  `"bolagsnyhet"`, `"bransch"`), `signal_detalj`, `prospect_id`, `processad_at`
  och `utkast`. Det enda signalvärdet koden filtrerar på är `'flyttad'`.
- Fördelningsspår efter kontaktsökningen (`sources/merinfo.py:1108-1165`,
  `fordela`): `"iris"`, `"ring"`, `"prova_om"`, `"ej_kvalificerad"`; omprövningen
  lägger till `"redan_flyttad"` (`omprova.py:77-78`).

### Körningar
- `leads_job_ledger.status`: `'queued'`, `'processing'`, `'completed'`, `'failed'`
  (059:44-45).
- `leads_job_ledger.scope` (fri text) i bruk: `"batch"`, `"lista"`, `"research"`,
  `"research_and_draft"`, `"draft"`, `"utkast"` (grep i `leads.py`/`postgres.py`).
- `korning` jsonb (`snajp-support/app/leads/korning.py:89-106`): `mal, levererade,
  undersokta, pagaende, kandidater, rundor, tak, tratt, jobs, klar, slut_orsak,
  flaskhals, scope, overrides, is_test` plus senare nycklar (`listspar`,
  `fordelning`, `styrning`, `sammanfattning`, `webbpool_startad` m.fl.).
- `slut_orsak`: `"klar"`, `"avbruten"`, `"slut_pa_kandidater"`, `"inga_traffar"`,
  `"sokningen_foll"`, `"ingen_malgrupp"`, `"tak"` (`korning.py:243-264`,
  `leads.py:3319`, `3351`, `3444-3457`).
- `korning.styrning`: sätts via `set_korning_styrning` (`postgres.py:3383-3396`);
  `"paus"` och `"avbruten"` läses i `leads.py:3442-3444`.

---

## 5. orgnr: normalisering och validering i dag

| Var | Sekelprefix | Personnummer (3:e siffran 0/1) | Luhn | Utdata |
|---|---|---|---|---|
| `snajp-support/app/leads/orgnr.py:56-65` `normalisera` | stryker bara `16` | – | – | 10 siffror |
| `orgnr.py:82-101` `_strip_sekel` | stryker `19`/`20` | **accepteras** (enskild firma, beslut 2026-08-18) | – | |
| `orgnr.py:104-133` `validera_format` | `16`, sedan `19`/`20` | accepteras | ja, höjer `OgiltigtOrgnrError` | 10 siffror utan bindestreck |
| `orgnr.py:136-139` `formatera` | `16` | – | – | `NNNNNN-NNNN` |
| `upptagna.py:41-46` `orgnr_nyckel` | stryker **alla** 12-siffriga prefix | – | – | `orgnr:NNNNNNNNNN` |
| `031` `foretagsnyckel` (SQL) | **stryker inget** | – | – | alla siffror |
| `leads.py:4544-4548` `_dedupnyckel` | stryker inget | – | – | `orgnr:<siffror>` |
| `sources/merinfo.py:159-160` `_orgnr`, `allabolag.py:355-356` | – | allabolag: >10 siffror = enskild firma, orgnr blir `None` (rad 358-364) | – | `NNNNNN-NNNN` |
| `webbpool.py:175-181` `ar_enskild_firma` | tar sista tio siffrorna | 3:e siffran `0`/`1` = enskild | – | bool |
| `lib/orgnr.ts:23-39` `normaliseraOrgnr` | `16`, `19`, `20` | accepteras | `orgnrFel` rad 56-70 | speglar orgnr.py |
| `lib/leads/importvarden.ts:59-71` `tolkaOrgnr` (importen) | `16`, `18`, `19`, `20`; `SE…01` (momsnummer) | **avvisas** (`fel: "personnummer"`) | ja | `NNNNNN-NNNN`; 8–9 siffror (utländska) sparas som skrivna |

Var Python-valideringen används: befordran (`snajp-support/app/leads/befordran.py:23`,
`57`), `POST /api/leads/prospects/{id}/befordra` (`leads.py:911-914`) och
orgnr-uppslaget (`orgnr_uppslag.py:38`, `60`). **Inte** i importen, inte i
`create_prospect`, inte i `PATCH /api/leads/prospects/{id}` (där `orgnr` bara har
`max_length=20`, `schemas.py:443`).

Lagrat format i praktiken: `NNNNNN-NNNN` från register och import. **[antagande]**
Äldre rader och manuella PATCH kan ha andra format.

Fynd att känna till: `orgnr.py:100-101` är död kod efter `return` och refererar
till en odefinierad `_PERSONNUMMER_SVAR`. Ofarlig i dag, men visar att regeln om
personnummer ändrats utan att alla kopior följt med.

**Följd för CRM:et:** en kund som synkar `16556824-9022` får samma
`upptagna`-nyckel som `556824-9022`, men olika `foretagsnyckel` (send_guard), och
importens TS-tolkning hade avvisat ett personnummer som Python-valideringen
accepterar. CRM:et behöver EN kanonisk funktion (förslag: tio siffror, sekelprefix
16/19/20 bort, Luhn, enskild firma uttryckligen markerad) och bör lagra den
normaliserade nyckeln i en egen kolumn med unikt index per tenant.

---

## 6. Hemliga fält och var grinden sitter

Regeln (CLAUDE.md, Antons beslut 2026-10-08): webbplatsbedömningen och allt som
härleds ur den syns bara för plattformsadmin och kunderna Umeå Webdesign och
Alunix.

- Grinden: `webbpool.far_se(storage, tenant_id)` (`webbpool.py:108-116`): slug
  eller id i `synliga()` (`webbpool.py:101-105`) = `SYNLIGA = ("kund-ea08b974",
  "kund-362d9dc5")` (rad 97) eller env `WEBBBEDOMNING_SYNLIG`, plus
  `WEBBPOOL_MOTTAGARE` och `WEBBPOOL_INSPIRATION`. Fel → `False` ("hellre dold än
  läckt").
- Döljningen: `webbpool.dolj(rad)` tar bort `DOLDA_FALT = ("webbrevision",
  "webbniva")` (`webbpool.py:98`, `119-120`).
- Anropen:
  - `GET /api/leads/prospects` (`leads.py:630-673`),
  - `GET /api/leads/prospects/{id}` (`leads.py:749-752`),
  - alla skrivsvar via `_utan_dold_bedomning` (`leads.py:756-772`; används på 471,
    887, 950, 986, 989, 2545, 4790); testet `tests/api/test_webbbedomning_skrivsvar.py`
    håller räkningen enligt docstringen,
  - `GET /api/leads/listor/{id}` (`leads.py:4676-4680`),
  - research-prompten (`snajp-support/app/agent/leads_research_v2.py:435-437`),
  - listbygget räknar bara bedömningen för webbyråer (`leads.py:5086`, `5157-5165`).
- Kopior till andra kunder: `admin_listor.LISTRADSFALT` (`admin_listor.py:38-42`)
  saknar `webbrevision`, `webbniva`, `lan`, `avtalsslut` och `extra` med flit, och
  nollar `signal_detalj` för webbpoolrader (rad 108-110).
- Kundens egna CRM-kolumner `avtalsslut` och `extra` (152) lämnar aldrig kunden
  (`152_import_avtalsslut_extra.sql:11-13`).

**Att verifiera innan CRM:et visar fält:** `DOLDA_FALT` innehåller **inte** `lan`,
fast CLAUDE.md räknar "`lan`-fördelningen" som hemlig. `prospects.lan` och
`lead_list_items.lan` följer alltså med i svaren ovan för alla kunder. Det kan
vara avsiktligt (länet är också en vanlig bolagsuppgift) eller en lucka; fråga
Anton innan CRM:et exponerar `lan`. Webbpoollistors `signal_detalj` bär
bedömningen i klartext ("Akut · modernitet 3/10 · …", `admin_listor.py:109`) och
döljs inte av `dolj` för listans egen ägare. **[att verifiera]** att bara
webbyråerna någonsin äger `kalla='webbpool'`-listor.

Regel för CRM:et: varje CRM-endpoint, export, tidslinje och synk UT som bär en
prospekt- eller listrad ska gå genom `webbpool.dolj` när `far_se` är falsk, i
samma commit. Tvåvägs-API:t får aldrig returnera `webbrevision`/`webbniva`
(och troligen inte `lan`) till en kund utanför listan.

---

## 7. Var en CRM-koppling naturligt hakar i

### 7.1 Läsa (CRM-bolagets vy av leads)

| Behov | Funktion / endpoint |
|---|---|
| Finns bolaget redan som lead eller i en lista? | `upptagna.hamta` / `storage.lista_upptagna_bolag` (`postgres.py:3641`), med `upptagna.samma_bolag` för det exakta beslutet |
| Prospektet | `storage.get_prospect` / `get_prospects` (`postgres.py:2721-2735`), `GET /api/leads/prospects/{id}` |
| Listrader per bolag | Inget uppslag per orgnr i dag; index `lead_list_items_orgnr_idx` är `(list_id, orgnr)` och hjälper inte en sökning över alla listor. Behövs ny läsfunktion. |
| Tidslinje | `GET /api/leads/prospects/{prospect_id}/tidslinje` (`leads_suite.py:147-195`): skapad, statuslogg, mejl in/ut ur `outreach_messages`, `lead_samtal`, `lead_anteckningar`, `lead_uppgifter`. **Saknar** `lead_handelser` (149) och supportärenden. Komponeras i kod, ingen händelsetabell (086:4-6) |
| Konversationer | `snajp-support/app/api/leads_konversationer.py`, `konversation.py` (`lead_handelser`, `outreach_threads.steg`) |
| Samtal | `storage.list_lead_samtal`, `GET /api/leads/samtal` (`leads_suite.py:216-225`) |
| Uppföljningar | `snajp-support/app/api/leads_uppfoljningar.py`, `follow_up.py` **[ej läst i detalj]** |
| Spärrar | `storage.list_suppressions`, `storage.list_begransade` (`postgres.py:1453-1467`) |

### 7.2 Skriva (kundsynk IN, Buddy)

Den naturliga minsta vägen för "kundsynk IN via API" är att CRM:ets kunder blir
uteslutningens källa:

1. **Alternativ A, inget nytt i leads:** synken skriver till en `lead_lists`-rad
   med `kalla='crm'` per kund ("Kunder från Buddy") genom samma logik som
   `importera` (`leads_suite.py:412-511`). Fungerar direkt med all uteslutning
   ovan. Nackdelar: bara insert (ingen upsert/radering), `antal ≤ 200`-hacket, och
   orgnr valideras inte på servern.
2. **Alternativ B, rekommenderat [förslag]:** en egen CRM-bolagstabell med kanonisk
   orgnr-nyckel och unikt index per tenant, och `lista_upptagna_bolag` utökas med
   en tredje `union` som ger `kalla='crm'` för CRM-bolag med kundstatus. Då når
   uteslutningen alla anropare i tabellen i 3.3 utan att röras, eftersom de alla
   går genom `upptagna.hamta`. Glöm inte minneslagret (`memory.py:2637-2654`) och
   kontraktet i `base.py:1254-1262`.

Övriga skrivvägar en CRM-koppling måste respektera:

- **Skapa prospekt bara via `storage.create_prospect`** (dubblettgrinden). Hantera
  `fanns_redan`. Ett nytt `origin`-värde (t.ex. `'crm'`) kräver en migration som
  utökar `prospects_origin_check` (senast 107:29-31) och genomgång av alla
  ställen som läser origin: `listvy.synliga`, `discovery.SAJTENS_HARKOMSTER`
  (`discovery.py:989`, påverkar vilka adresser `mottagare()` godtar, rad 992-1015),
  `automation.py`, send_guardens spärr noll för `example`/`test`, `samtal._EJ_PROSPEKT`.
- **Statusbyten bara via `storage.update_prospect`**, så att `prospect_status_logg`
  skrivs i samma transaktion (`postgres.py:2850-2858`). Från API: `PATCH
  /api/leads/prospects/{id}` sätter `status_kalla='manuell'` och startar
  `crm_synk.synka_prospekt` (`leads.py:2527-2544`). En synk IN bör använda
  `kalla='import'` (finns redan i 086:51) och inte trigga synk UT tillbaka
  (loopfara).
- **Anteckningar**: `storage.add_lead_note` (anropas i `leads_suite.py:280`) med
  synk UT som fire-and-forget (rad 281-283).
- **Avregistreringar**: `storage.add_suppression(tenant_id, email=, reason=)`
  (`postgres.py:1469`). Det finns ingen bolagsspärr; "kontakta inte" på bolagsnivå
  är `prospects.status = 'suppressed'`.
- **Arkivera/radera**: `storage.arkivera_prospekt`, `storage.radera_prospekt`
  (`postgres.py:2757-2802`; radering vägras för kontaktade). API i
  `leads_massatgard.py:61-93`.
- **Utskick stoppas** av `scheduler.avbryt_utskick_for_prospekt` (används i
  `leads_massatgard.py:72` och `samtal.py`) och av send_guard när status är
  `lost`/`suppressed` (`scheduler.py:173-178`).

### 7.3 Utgående synk som redan finns

`crm_synk.synka_prospekt(storage, tenant_id, prospect, handelse=, text=)`
(`crm_synk.py:118-151`): läser `agent_settings(agent_type='leads').crm_synk =
{leverantor: 'hubspot'|'pipedrive', integration_id}`, dekrypterar `api_key` ur
integrationen (`..integrationer.lagring`), speglar bolaget (namn, domän, telefon)
och skriver en anteckning `"Snipra: <händelse>: <text>"`. Kastar aldrig. Anropas
vid statusbyte (`leads.py:2535-2544`) och ny anteckning (`leads_suite.py:281-283`).
Matchar på exakt namn, inte orgnr. "Snipra" är ett äldre produktnamn i strängen.

### 7.4 Livscykel i korthet (för tidslinjen)

```
register (allabolag/merinfo) ─┐
sökfederation (jobtech, rss) ─┼─> upptagna.hamta (uteslut) ─> förfilter ─> Jev-triage
                              │                                              │
                              │        merinfo.fordela: iris | ring | prova_om | ej_kvalificerad
                              │              │        │         │              │
                              │   create_prospect  create_prospect  (inget)   lead_list "Ej kvalificerade, Iris <datum>"
                              │   origin 'iris'    origin 'ring'
                              │        │
                              │   research → bedömning (niva A/B/C, motivering) → utkast
                              │        → granskning → send_queue → skickat (status 'contacted')
                              │        → svar (replied) → steg: mote/aterkom/ej_intresserad/kontakta_inte
                              │        → lead_samtal / lead_handelser / prospect_status_logg
listor (sök/import/kombinerad) ─> lead_list_items ─(befordra/omprova)─> bakgrundsprospekt (origin 'lista'/'import')
CRM-kundlista (kalla 'crm') ────> endast uteslutning
```

**[antagande]** att `status` går `new → researching → ready → contacted` i den
ordningen; jag har inte läst varje ställe som sätter `ready`/`contacted`.

---

## 8. Risker och öppna frågor för CRM-bygget

1. **Ingen unik bolagsnyckel.** Grinden är en O(n)-läsning under advisory-lås per
   kund. En synk av tusentals Buddy-kunder som också ska kunna bli prospekt
   behöver en kolumn med normaliserad orgnr och ett unikt index (partiellt, där
   orgnr finns), och samma nyckel bör användas i `upptagna`.
2. **Namnmatchning i uteslutningen ger falska träffar.** `upptagen` fäller på namn
   ELLER orgnr. Med en stor kundbas (telefonikunder heter ofta "Bygg AB",
   "Måleri AB") utesluts andra bolag med samma namn. Bör ändras till
   `samma_bolag`-semantik när CRM-raden har orgnr. Det är en beteendeändring i
   Iris och bör beslutas av Anton.
3. **orgnr-normaliseringen skiljer sig** (avsnitt 5). Särskilt `foretagsnyckel`
   (send_guard-karensen) som inte stryker prefix.
4. **Tidslinjen saknar `lead_handelser` och support.** Den ska utökas, inte
   dupliceras (086: "En egen händelsetabell hade blivit en andra sanning").
5. **`lan` döljs inte** av `webbpool.dolj` (avsnitt 6). Fråga Anton.
6. **Synken development ↔ main** kräver att nya tabeller registreras (111, 122,
   `scripts/railway_synk.py`), annars försvinner CRM-data i spegeln eller
   återuppstår raderad data.
7. **Gallringen** (`gallra_tenant`, senast `20261119230000_143_listraden_skyddar_prospektet.sql`)
   raderar gamla prospekt efter `behandlad_at`. Ett prospekt som är kopplat till
   en aktiv CRM-kund får inte gallras bort; nya CRM-tabeller måste in i
   gallringens urval eller skydda sina prospekt. **[att verifiera i 143/146/151]**
8. **Namnkrock** med `public.companies`/`public.contacts` (avsnitt 1.8).
9. **`antal between 1 and 200`** på `lead_lists` gör en CRM-lista som kundsynkens
   mål till ett hack (Alternativ A).
10. **Integritet:** `orgnr` kan vara ett personnummer (enskild firma) i Python-vägen
    (`orgnr.py:85-95`). CRM-kolumnen ska behandlas som personuppgift när
    juridisk form är enskild firma, och enskilda firmor får inte ringas utan
    NIX-kontroll (`merinfo.fordela`, rad 1139-1140).
11. **DeepSeek får inte se kunddata** (CLAUDE.md): Buddys kundlista är kunddata och
    får aldrig gå genom en DeepSeek-prompt.

Öppna frågor till Anton:
- Ska CRM-kunder uteslutas på orgnr enbart, eller som i dag på namn eller orgnr?
- Ska en befintlig kund som också ligger som Iris-prospekt arkiveras, flyttas
  eller bara märkas när synken hittar den?
- Får `lan` visas för alla kunder i CRM:et?
- Ska CRM-bolag utan orgnr accepteras från API:t, och i så fall matchas på vad
  (namn, domän)?
