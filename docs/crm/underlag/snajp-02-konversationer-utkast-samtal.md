# Underlag 02: konversationer, utkast, samtal och uppföljningar på CRM:ets tidslinje

Skrivet 2026-11-25 som underlag för Snajp CRM. Källa: grenen `claude/snajp-crm-dd0d83`
(senaste commit `9970d304`). Alla sökvägar är relativa till repots rot; backendens filer
ligger under `snajp-support/`, migrationerna under `db/migrations/`.

**Märkning.** "Läst" = jag har läst koden eller SQL:en på angiven rad. "Antar" = slutsats
eller förslag som inte står i koden. Allt under avsnitt 6 är förslag.

Supportärendena (ss_tickets, ss_emails, ss_drafts) kartläggs i
`docs/crm/underlag/snajp-03-support-arenden.md`; här tas de bara med där de ska in på
samma tidslinje.

---

## 0. Det viktigaste först

1. **Allt i leadsflödet hänger på `prospects.id`.** Bolaget och personen är samma rad:
   `prospects` bär både bolaget (`company_name`, `orgnr`, `website`) och EN kontaktperson
   (`contact_name`, `contact_email`, `contact_phone`, `contact_role`). Det finns ingen
   persontabell för leads (läst: `db/migrations/010_agent_backend.sql:100-112`,
   `031_prospect_nischfalt.sql:28-35`, `058_prospect_kontaktniva.sql:19-24`,
   `20261001200000_081_kontakt_telefon.sql:9-10`).
2. **Bolagsnyckeln finns redan:** `prospects.foretagsnyckel` är en genererad kolumn:
   orgnr-siffror, annars e-postdomänen (läst: `031_prospect_nischfalt.sql:50-60`, index
   `(tenant_id, foretagsnyckel)`). CRM:ets orgnr-nyckel ska matcha mot den, inte mot rå
   `orgnr`.
3. **En tråd per prospekt.** `outreach_threads.prospect_id` → `prospects.id`; koden tar
   alltid den äldsta tråden (`order by created_at limit 1`, läst:
   `snajp-support/app/storage/postgres.py:1959-1999`). Alla mejl, utkast, köposter,
   händelser och demolänkar hänger på tråden.
4. **Det finns en händelselogg, men den är ofullständig och inte prenumererbar:**
   `lead_handelser` (migration 149) loggar svar, klassning, utkast, stegbyten, möten,
   överlämningar och mejl utanför Snajp. Den loggar INTE första utskicket eller
   uppföljningar som skickas via granskningskön eller schemaläggaren, inte samtal (de
   bor i `lead_samtal`), inte statusbyten (de bor i `prospect_status_logg`), inte
   anteckningar eller uppgifter. Det finns ingen webhook, ingen SSE och ingen
   händelseström ut. `platform_events`/`app/api/events.py` är en fellogg, inte ett
   domänflöde.
5. **Ett mejlsvar knyts till ett lead på avsändaradressen**, inte på
   `In-Reply-To`/`References`: exakt `contact_email`, annars samma domän som bolagets
   `website` (utom gratisdomäner). Första träffen bland upp till 20 000 prospekt vinner
   (läst: `snajp-support/app/email_pipeline/klassning.py:80-101`).
6. **Det finns redan en tidslinje** (`GET /api/leads/prospects/{id}/tidslinje`,
   `snajp-support/app/api/leads_suite.py:147-195`) som komponeras i kod ur prospektet,
   statusloggen, tråden, samtalen, anteckningarna och uppgifterna. Den tar inte med
   `lead_handelser`, demolänkens klick, leveransutfall eller supportärenden, och den
   visar osända och kasserade utkast som skickade mejl (se 6.5).
7. **Ingen rad bär vem (vilken användare) som gjorde något.** `kalla` säger bara
   `kod`/`manuell`/`import`. Backenden autentiserar med en API-nyckel per kund
   (`require_tenant`, `snajp-support/app/api/deps.py:62-72`); användaren når aldrig
   backenden. Ett CRM som vill visa "Anna ringde" måste lägga till det.

---

## 1. Tabellerna, kolumnerna och nycklarna

Alla tabeller nedan har `tenant_id uuid not null` med RLS-policyn `tenant_isolation`
(`tenant_id = current_setting('app.tenant_id')`). Kaskad: allt under ett prospekt
försvinner med det (`on delete cascade`).

### 1.1 `prospects` — bolaget och kontaktpersonen

Skapad `010_agent_backend.sql:100-112` (läst). Kolumner som rör tidslinjen och nyckeln:

| Kolumn | Typ | Källa (migration:rad) | Not |
|---|---|---|---|
| `id` | uuid PK | 010:101 | Leadets nyckel överallt |
| `company_name` | text not null | 010:103 | |
| `contact_name`, `contact_email` | text | 010:104-105 | Den ENDA personen per prospekt |
| `contact_phone` | text | 081:9-10 | |
| `contact_role`, `contact_level`, `contact_form_url` | text | 058:19-24 | |
| `status` | text | 010:109-110 | se 2.1 |
| `orgnr`, `ort`, `postnr`, `sni`, `website`, `anstallda`, `omsattning` | | 031:28-35 | |
| `foretagsnyckel` | text, genererad | 031:50-60 | orgnr-siffror, annars mejldomän |
| `origin` | text | 039:23-24, utökad 107:29-31 | `manual`, `example`, `import`, `test`, `inkorg`, `lista`, `iris`, `ring` |
| `arkiverad_at` | timestamptz | 107:27 | Arkiverad = dold, står kvar i uteslutningen |
| `created_at` | timestamptz | 010:111 | |

`webbrevision`, `lan` m.fl. finns också men är hemliga för alla utom plattformsadmin,
Umeå Webdesign och Alunix (projektregeln 2026-10-08). **De får inte följa med till
CRM:et.**

### 1.2 `prospect_status_logg` — varje statusbyte

`20261003140000_086_leads_suite.sql:45-53` (läst).

| Kolumn | Typ |
|---|---|
| `id` | uuid PK |
| `prospect_id` | uuid → `prospects(id)` cascade |
| `fran` | text (null vid första) |
| `till` | text not null |
| `kalla` | `kod` \| `manuell` \| `import` |
| `created_at` | timestamptz |

Skrivs BARA av `storage.update_prospect` i samma transaktion som statusbytet, och bara
när statusen faktiskt ändras (läst: `snajp-support/app/storage/postgres.py:2850-2876`).
Varje kodväg som byter status (svaret, utskicket, samtalet, steget, PATCH) loggas alltså
här.

### 1.3 `outreach_threads` — konversationen

`010_agent_backend.sql:171-179` plus tillägg (läst).

| Kolumn | Typ | Källa | Not |
|---|---|---|---|
| `id` | uuid PK | 010 | |
| `prospect_id` | uuid → `prospects(id)` cascade | 010 | |
| `offer_id` | uuid → `offers(id)` | 010 | |
| `language_state` | `sv` \| `en_confirmed` | 010 | |
| `last_inbound_at` | timestamptz | 010 | sätts av `record_inbound_reply` |
| `created_at` | timestamptz | 010 | |
| `svarsklass`, `svarsklass_at` | text, timestamptz | 116:28-35 | se 2.4 |
| `struktur` | `a` \| `b` | 116:30-39 | utkastvariant för A/B |
| `aterkom_datum` | date | 149:36 | Återkom/återkontakt |
| `steg` | text | 149:37-40 | se 2.3 |
| `synk_andrad_at` | timestamptz | 111 | sätts av trigger vid varje skrivning |

### 1.4 `outreach_messages` — mejlen och utkasten

`010_agent_backend.sql:181-189` plus tillägg (läst).

| Kolumn | Typ | Källa | Not |
|---|---|---|---|
| `id` | uuid PK | 010 | |
| `thread_id` | uuid → `outreach_threads(id)` cascade | 010 | ENDA länken uppåt; ingen `prospect_id` |
| `direction` | `inbound` \| `outbound` | 010 | |
| `subject` | text not null default `''` | 014:6 | Inkomna svar sparas UTAN ämne (`''`) |
| `body` | text | 010 | |
| `humanizer_variant` | text | 010 | |
| `sent_at` | timestamptz | 010 | utgående: skickat; inkommande: tid då Snajp hämtade svaret (`now()`), inte mejlets Date |
| `created_at` | timestamptz not null default now() | 107:20-21 | äldre rader fick migrationsdagen |
| `kasserad_at` | timestamptz | 107:22-23 | utkast som avvisats/ersatts, aldrig skickat |
| `leverans`, `leverans_at` | `studs` \| `klagomal` | 113:8-10 | från Resends webhook |
| `kampanj_id` | text | 114:10 | kampanjens id (definitionen i inställningarna) |
| `behandlad_at` | timestamptz | 141:37 | trigger: när ämne/text ändrades |

Ett meddelandes läge (läst: `snajp-support/app/api/leads_konversationer.py:185-201`):
`inbound` = **svar**; `outbound` + `sent_at` = **skickat**; `outbound` + `kasserad_at` =
**kasserat**; annars **utkast** (väntande).

### 1.5 `send_queue` — granskning och sändkö

`010_agent_backend.sql:193-205`, status utökad `023_agent_config_settings.sql:43-45`
(läst).

| Kolumn | Typ | Not |
|---|---|---|
| `id` | uuid PK | "queue_item_id" i API:t |
| `thread_id` | uuid → `outreach_threads(id)` cascade | **Ingen `message_id`.** Posten gäller trådens väntande utkast |
| `scheduled_at` | timestamptz | |
| `status` | `queued`, `awaiting_review`, `sent`, `cancelled`, `blocked` | |
| `gate_checks` | jsonb | `approved_by`, `rejected_by`, `via`, `send_guard_regel`, `send_guard_skal`, `held`, `decision`, `sandfel_*` |
| `created_at`, `behandlad_at` | timestamptz | |

### 1.6 `lead_samtal` — samtal i ring- och återkopplingslistan

`20261008090000_107_crm_samtal.sql:33-43` (läst).

| Kolumn | Typ |
|---|---|
| `id` | uuid PK |
| `prospect_id` | uuid → `prospects(id)` cascade |
| `utfall` | `ej_svar`, `aterkom`, `ej_intresserad`, `kontakta_inte`, `mote` |
| `aterkom_datum` | date |
| `anteckning` | text |
| `created_at` | timestamptz |

Bara `select, insert` för `snajp_app` (107:55): **ett samtal går inte att ändra eller
radera** från appen.

### 1.7 `lead_handelser` — konversationens händelselogg och notiserna

`20261122090000_149_iris_konversationer.sql:42-57` (läst).

| Kolumn | Typ | Not |
|---|---|---|
| `id` | uuid PK | |
| `prospect_id` | uuid not null → `prospects(id)` cascade | |
| `thread_id` | uuid → `outreach_threads(id)` cascade | nullable |
| `typ` | se 2.5 | 14 värden |
| `kalla` | `kod` \| `manuell` | |
| `detalj` | jsonb | id:n, klass, steg; aldrig svarstext, UTOM `extern` som bär hela texten |
| `notis` | boolean | sant för `svar`, `utkast`, `mote`, `overlamnat` |
| `last_at` | timestamptz | läst av arbetsytan (inte per användare) |
| `created_at` | timestamptz | |
| `synk_andrad_at` | timestamptz | 149:84-91 |

Rättigheter: `select, insert, update` (149:76).

### 1.8 `lead_anteckningar`, `lead_uppgifter`

`086_leads_suite.sql:22-41` (läst). Båda pekar på `prospect_id`.
`lead_anteckningar`: `id, prospect_id, text, created_at`.
`lead_uppgifter`: `id, prospect_id, titel, forfaller date, klar boolean, klar_at, created_at`.

### 1.9 `ss_demolankar`, `ss_demolank_handelser` — demolänken i utkasten

`20261115090000_116_demolank_och_svarsklass.sql:71-92` (läst).
`ss_demolankar(token PK, tenant_id, thread_id → outreach_threads cascade, mal_url,
created_at)`, unik på `(tenant_id, thread_id)`.
`ss_demolank_handelser(id bigserial, token → ss_demolankar, tenant_id, typ 'klick'|'besok',
skanner boolean, user_agent, created_at)`. `skanner = true` = e-postskyddets klick, räknas
inte (116:142-150).

### 1.10 `suppressions` — spärrlistan

`000_base_schema.sql:170` (läst rubriken, inte kolumnerna i detalj). Skrivs via
`storage.add_suppression(tenant_id, email=…, reason=…)` vid Kontakta inte, avregistrering,
andra nej, studs och klagomål. Nyckeln är e-postadressen, inte prospektet.

### 1.11 Supportsidan, bara nycklarna

(Läst: `002_snajp_support.sql:7-56`, `004_snajp_email_pipeline.sql:19-118`.)
`ss_customers(id, name)` + `ss_customer_identifiers(customer_id, type 'email'|'phone',
value)`; `ss_tickets.customer_id`; `ss_emails(from_email, ticket_id, status, klass)`;
`ss_drafts(email_id, ticket_id, status 'pending'|'approved'|'rejected'|'auto_sent')`;
`ss_decision_log(email_id, event, detail)`. **Inget av det bär orgnr eller prospect_id.**
Kopplingen till ett CRM-bolag måste gå via e-postadress eller domän (antar). Ett
leadssvar som kommer via inkorgen lämnar spår i `ss_decision_log` med
`event='lead'` och `detail.prospect_id/thread_id`
(läst: `snajp-support/app/email_pipeline/processor.py:475-482`).

### 1.12 Översikt: vad pekar på vad

```
prospects (id, foretagsnyckel, contact_*)
 ├─ prospect_status_logg.prospect_id
 ├─ lead_samtal.prospect_id
 ├─ lead_anteckningar.prospect_id
 ├─ lead_uppgifter.prospect_id
 ├─ lead_handelser.prospect_id (+ thread_id)
 └─ outreach_threads.prospect_id  (en per prospekt i praktiken)
     ├─ outreach_messages.thread_id
     ├─ send_queue.thread_id
     └─ ss_demolankar.thread_id ─ ss_demolank_handelser.token
```

---

## 2. Utfall och statusvärden, ordagrant, och vad de utlöser

### 2.1 `prospects.status`

Tillåtna: `new`, `researching`, `ready`, `contacted`, `replied`, `meeting`, `won`,
`lost`, `suppressed` (läst: `010_agent_backend.sql:109-110`).

| Status | Sätts av (läst) |
|---|---|
| `contacted` | Första lyckade utskicket, bara framåt från `new`/`researching`/`ready` (`app/leads/scheduler.py:614-619`); ett samtal till ett lead i `new`/`ready` (`app/leads/samtal.py:173-175`) |
| `replied` | Svar klassat `aterkom`, `invandning`, `fraga` (`app/leads/svar.py:374, 465, 491`); steget Svarat eller Återkom (`app/leads/konversation.py:43-49`) |
| `meeting` | Svar klassat `positivt` (`svar.py:425`); samtalsutfallet `mote` (`samtal.py:33`); steget Möte bokat (`konversation.py:45`) |
| `lost` | Svar `negativt` (första nejet) (`svar.py:347-351`); samtalet `ej_intresserad`; steget Ej intresserad |
| `suppressed` | Svar `avregistrering` eller ett andra nej (`svar.py:336-351`); samtalet `kontakta_inte`; steget Kontakta inte |
| `won` | Bara via `PATCH /api/leads/prospects/{id}` (antar: ingen kodväg sätter det, sökt i `svar.py`, `samtal.py`, `konversation.py`, `scheduler.py`) |

Avslutade statusar som stoppar uppföljningar: `replied`, `meeting`, `won`, `lost`,
`suppressed` (läst: `app/leads/follow_up_generator.py:149`).

### 2.2 Samtalsutfall (`lead_samtal.utfall`)

Ordagrant i koden: `ej_svar`, `aterkom`, `ej_intresserad`, `kontakta_inte`, `mote`
(läst: `app/leads/samtal.py:30`). UI:ts etiketter (CLAUDE.md, leadsregel 17): Ej svar,
Återkom (datum), Ej intresserad, Kontakta inte, Möte bokat.

Vad `samtal.registrera` gör (läst: `app/leads/samtal.py:152-205`):

| Utfall | Prospektstatus | Övrigt |
|---|---|---|
| `ej_svar` | `contacted` om leadet var `new`/`ready`, annars oförändrad | Kommer tillbaka i listan efter 2 arbetsdagar (`EJ_SVAR_ARBETSDAGAR = 2`, rad 36; helger och svenska röda dagar hoppas över, rad 53-60) |
| `aterkom` | som ovan | Kräver datum (422 annars, `leads_suite.py:205-206`). Står i listan igen på datumet. Om tråden finns: `outreach_threads.steg='aterkom'`, `aterkom_datum` sätts (`samtal.py:197-198`) |
| `ej_intresserad` | `lost` | Avslutande: `avbryt_utskick_for_prospekt` ställer in kön och kasserar osända utkast (`samtal.py:169-170`, `scheduler.py:653-661`) |
| `kontakta_inte` | `suppressed` | Avslutande + `contact_email` läggs i `suppressions` med skälet `kontakta inte (samtal)` (`samtal.py:171-172`) |
| `mote` | `meeting` | Avslutande + `lead_handelser` typ `mote`, `kalla='manuell'`, `detalj={"via":"samtal"}`, markerad läst (`samtal.py:199-203`) |

Statusbytet från ett samtal loggas med `kalla='manuell'` (`samtal.py:177`).

Listorna (läst: `samtal.py:76-149`): **återkoppling** = leads med telefon och status
`contacted` (eller `replied` med ett konversationsdatum), utom `origin='ring'`;
**ring** = `origin='ring'` som inte är `lost`/`suppressed`/`meeting`/`won`. Arkiverade
och `example`/`test` tas aldrig med. Ett mejlsvar flyttar leadet ur återkopplingen
eftersom statusen lämnar `contacted`.

### 2.3 Konversationens steg (`outreach_threads.steg`)

Tillåtna: `svarat`, `aterkom`, `mote`, `ej_intresserad`, `kontakta_inte` (läst:
`149:38-40`, `konversation.py:40`).

Steget som visas härleds av `konversation.steg()` (läst: `konversation.py:61-75`):
status `meeting`/`won` → `mote`; `suppressed` → `kontakta_inte`; `lost` →
`ej_intresserad`; annars `steg='svarat'` → `svarat`; `steg='aterkom'` eller ett
`aterkom_datum` eller `svarsklass='aterkom'` → `aterkom`; annars `svarat`.

`satt_steg` (läst: `konversation.py:389-450`) gör:

| Steg | Status | Utlöser |
|---|---|---|
| `svarat` | `replied` | `aterkom_datum` nollas |
| `aterkom` | `replied` | Kräver datum (`ValueError`/422) |
| `mote` | `meeting` (inte om redan `won`) | Avslutande: väntande utkast kasseras (händelse `utkast_kasserat`, `orsak: "steg:mote"`), kön ställs in; händelse `mote` (notis) |
| `ej_intresserad` | `lost` | Avslutande; utan datum sätts återkontakt om kundens antal månader (standard 6, `ATERKONTAKT_STANDARD`, rad 122) |
| `kontakta_inte` | `suppressed` | Avslutande; adressen spärras (`kontakta inte (konversation)`), aldrig datum |

Alltid: händelse `steg` med `detalj={fran, till, aterkom_datum}`. Ett nytt svar nollar
`steg` (`storage.nolla_trad_steg`, `svar.py:198-201`), så Iris klassning gäller igen.

"Att göra" (läst: `konversation.py:95-103`): olästa notiser, ett väntande utkast, eller
ett `aterkom_datum` som infallit (för Återkom och Ej intresserad).

### 2.4 Svarsklassen (`outreach_threads.svarsklass`)

Iris klasser (läst: `svar.py:83`): `positivt`, `aterkom`, `invandning`, `fraga`,
`negativt`, `avregistrering`, `autosvar`. Kolumnen tar alla utom `autosvar`
(116:33-35); ett autosvar skriver ingen klass (`svar.py:322`).

| Klass | Utlöser (läst: `svar.py:334-491`) |
|---|---|
| `positivt` | Kön ställs in, call-prep-underlag, handoff, status `meeting`, prioriterat mejl till Snajp, händelser `overlamnat` + `mote` |
| `aterkom` | Kön ställs in, status `replied`, återkontaktdatum (prospektets egna eller standard 2 mån), prioriterat mejl |
| `invandning` / `fraga` | Svarsutkast köas `awaiting_review` (alltid granskning), status `replied`, händelse `utkast` (notis). Tar svaret upp pris/juridik och kundens eskaleringsregel är på: inget utkast, överlämnas |
| `negativt` | Kön ställs in, status `lost`, återkontakt om 6 mån; andra nejet efter en återkontakt → som avregistrering |
| `avregistrering` | Kön ställs in, adressen spärras, status `suppressed`, inget datum |
| `autosvar` | Köade utskick skjuts 7 dagar (`AUTOSVAR_UPPSKJUTNING`, rad 88) |
| (`avbrutet`) | Kod, inte modell: påhopp/missbruk → kön ställs in, handoff. Skrivs inte som svarsklass |

### 2.5 Händelsetyperna (`lead_handelser.typ`)

Ordagrant (läst: `149:47-51`): `svar`, `klassad`, `utkast`, `utkast_ersatt`,
`utkast_kasserat`, `utkast_aterstallt`, `utkast_redigerat`, `generering_startad`,
`generering_fel`, `skickat`, `steg`, `mote`, `overlamnat`, `extern`.

| Typ | Skrivs av (läst) | `detalj` |
|---|---|---|
| `svar` | `svar.py:190-197` | `message_id`, ev. `last_i_brevladan`, `besvarat_i_brevladan` |
| `klassad` | `svar.py:327-330` | `klass`, `motivering` (≤300 tecken) |
| `utkast` | `svar.py:767-775`; omskrivning `leads_konversationer.py:475-478` | `message_id`, `klass`, ev. `oppnat`, `omskrivet` |
| `utkast_ersatt` | `app/agent/leads_tools.py:279-282` (ett nytt utkast ersatte ett väntande) | `message_id` |
| `utkast_kasserat` | `konversation.py:417-420`, `svar.py:777-780`, `leads_konversationer.py:393-396, 420-423` | `message_id`, `orsak`: `steg:<steg>`, `svar:<klass>`, `manuellt`, `aterstallning` |
| `utkast_aterstallt` | `leads_konversationer.py:427-430` | `message_id` |
| `utkast_redigerat` | `leads_konversationer.py:319-322` | `message_id` |
| `generering_startad` / `generering_fel` | `leads_konversationer.py:452-455, 468-471, 484-487` | `instruktion` / `fel` |
| `skickat` | **bara** `leads_konversationer.py:371-375` (Godkänn och skicka i Konversationer) | `message_id`, `utfall`, `bekraftat_handlingar` |
| `steg` | `konversation.py:440-443` | `fran`, `till`, `aterkom_datum` |
| `mote` | `konversation.py:446-449`, `samtal.py:200-203`, `svar.py:787-790` | `via: "samtal"` eller `klass: "positivt"` |
| `overlamnat` | `svar.py:782-785` | `klass`, `eskalerat` (lista) |
| `extern` | `leads_konversationer.py:523-527` (för hand) | `riktning`, `text`, `amne`, `tid` |

`notis = true` för `svar`, `utkast`, `mote`, `overlamnat` (`konversation.py:55`).

### 2.6 Utkastets status (härledd, ingen kolumn)

`app/leads/utkaststatus.py:41`: `saknas`, `vantar`, `godkant`, `koad`, `skickat`,
`avvisat`, `stoppat`, plus `skrivs` medan ett utkastjobb går (rad 160-161). Härleds ur
trådens senaste `send_queue`-post och meddelandena (rad 82-141):
`awaiting_review` → `vantar`; `queued` + `gate_checks.approved_by='human'` → `godkant`,
annars `koad`; `sent` eller ett `skickat_at` → `skickat`; `cancelled` → `avvisat`;
`blocked` → `stoppat` (med `utkast_regel` = `send_guard_regel`).

### 2.7 Uppföljningarna (härledda, ingen tabell)

`app/api/leads_uppfoljningar.py:86-131` (läst). Fack: `vantar`, `skrivs`, `forfallna`,
`kommande`, `skickade`, `fel`. Max 5 utgående per tråd (`MAX_OUTBOUND = len(LEVERS)+1`,
`follow_up_generator.py:97`), alltså 4 uppföljningar där den fjärde är breakup.
Avstånd 4/6/8/10 dagar (`follow_up_generator.py:88-93`); första uppföljningen styrs av
kundens `uppfoljning_dagar` per härkomst. Uppföljningens nummer räknas ur trådens antal
skickade (rad 134-163). Svepet körs av `run_godkand_sandare` (`scheduler.py:934-962`)
och skriver bara utkast till granskning.

### 2.8 Leverans och demolänk

`outreach_messages.leverans`: `studs`, `klagomal` (113). En tillfällig studs räknas inte
(`app/sending_domains.py:113-114`). Båda spärrar adressen.
`ss_demolank_handelser.typ`: `klick`, `besok`; `skanner=true` räknas inte.

### 2.9 Kampanjer

Kampanjens definition bor i leadsinställningarna (`settings.kampanjer`), inte i en
tabell; status `pagar`, `klar`, `fel`, härledd `avbruten` efter 30 min
(`leads_kampanjer.py:62-95`, läst). Varje kampanjutkast är ett vanligt
`outreach_messages` med `kampanj_id`.

---

## 3. API-endpoints som läser och skriver detta

**Behörighet:** alla nedan har `Depends(require_tenant)`: headern `X-API-Key` måste vara
en kundnyckel; master-nyckeln avvisas med 403 (läst: `app/api/deps.py:62-72`). Ingen
endpoint skiljer på roller inom kunden. Webbens proxy anropar med kundens nyckel (antar,
ej läst i proxyn).

### 3.1 Konversationer (`app/api/leads_konversationer.py`)

| Metod och sökväg | Rad | Gör |
|---|---|---|
| `GET /api/leads/konversationer` | 148 | Listan + räknare per filter (`att_gora`, `alla`, `utkast`, varje steg) och sammanfattning |
| `GET /api/leads/konversationer/{thread_id}` | 204 | Tråden: `meddelanden`, `externa`, `samtal`, `handelser`, `utkast`, `generering`, `forslag_mote` |
| `POST /api/leads/konversationer/{thread_id}/last` | 297 | Trådens notiser lästa |
| `PUT /api/leads/konversationer/{thread_id}/utkast` | 305 | `{subject, brodtext}` → `utkast_redigerat` |
| `POST /api/leads/konversationer/{thread_id}/utkast/skicka` | 326 | `{bekraftat_handlingar}`; 409 om utkastet påstår en handling utan bekräftelse → `skickat` |
| `POST /api/leads/konversationer/{thread_id}/utkast/kassera` | 379 | → `utkast_kasserat` |
| `POST /api/leads/konversationer/{thread_id}/utkast/{message_id}/aterstall` | 400 | → `utkast_aterstallt` |
| `POST /api/leads/konversationer/{thread_id}/utkast/generera` | 434 | 202, bakgrundsjobb → `generering_startad`, sedan `utkast` eller `generering_fel` |
| `POST /api/leads/konversationer/{thread_id}/steg` | 494 | `{steg, aterkom_datum}` → `satt_steg` |
| `POST /api/leads/konversationer/{thread_id}/extern` | 509 | 201, `{riktning, text, amne, tid}` → `extern` (ingen rad i outreach_messages) |
| `GET /api/leads/notiser?limit=` | 534 | Notiserna (1–100) |
| `GET /api/leads/notiser/antal` | 553 | Olästa |
| `POST /api/leads/notiser/last` | 563 | `{ids}` eller alla |

### 3.2 Samtal, tidslinje, anteckningar, uppgifter (`app/api/leads_suite.py`)

| Metod och sökväg | Rad | Gör |
|---|---|---|
| `GET /api/leads/prospects/{prospect_id}/tidslinje` | 147 | Den befintliga tidslinjen (se 6.5) |
| `POST /api/leads/prospects/{prospect_id}/samtal` | 198 | 201, `{utfall, aterkom_datum, anteckning}` → `samtal.registrera` |
| `GET /api/leads/samtal?lista=aterkoppling\|ring` | 216 | Listan |
| `GET /api/leads/samtal/antal` | 228 | Att ringa i dag per lista |
| `POST /api/leads/prospects/{prospect_id}/anteckningar` | 271 | 201; synkar också till HubSpot/Pipedrive (`crm_synk`) |
| `POST /api/leads/prospects/{prospect_id}/uppgifter` | 287 | 201 |
| `PATCH /api/leads/uppgifter/{task_id}` | 305 | `{klar}` |
| `GET /api/leads/uppgifter?oppna=` | 316 | |

### 3.3 Uppföljningar och sökning (`app/api/leads_uppfoljningar.py`)

| Metod och sökväg | Rad |
|---|---|
| `GET /api/leads/uppfoljningar` | 166 |
| `POST /api/leads/uppfoljningar/skapa` (202, `{prospect_ids}`) | 200 |
| `GET /api/leads/sok?q=` (namn, kontakt, e-post, webbplats, orgnr; ≤20 träffar) | 247 |

### 3.4 Kampanjer (`app/api/leads_kampanjer.py`)

`GET /api/leads/kampanjer` (170), `GET /api/leads/kampanjer/{kampanj_id}` (197),
`POST /api/leads/kampanjer` (209, 202), `POST /api/leads/kampanjer/{kampanj_id}/skicka`
(247), `POST /api/leads/kampanjer/{kampanj_id}/skicka-jobb` (259, 202).

### 3.5 Granskningskön, svar och skickat (`app/api/leads.py`)

| Metod och sökväg | Rad | Not |
|---|---|---|
| `GET /api/leads/queue` | 2220 | Utkast som väntar |
| `PUT /api/leads/queue/{item_id}` | 2269 | Redigera |
| `POST /api/leads/queue/{item_id}/approve` | 2339 | Godkänn och skicka; **loggar ingen `lead_handelser`** |
| `POST /api/leads/queue/{item_id}/skicka-nu` | 2425 | |
| `POST /api/leads/queue/{item_id}/reject` | 2483 | `gate_checks={rejected_by:"human", via:"granskningskön"}`; ingen händelse |
| `POST /api/leads/queue/schemalagg`, `/tillbaka-till-iris` | 2368, 2394 | |
| `POST /api/leads/svar` | 1290 | Ett svar in över API: `{thread_id \| prospect_id, body}` → `hantera_prospektsvar` |
| `GET /api/leads/svar` | 1546 | Inkomna svar |
| `GET /api/leads/skickat`, `/skickat/antal` | 1560, 1608 | |
| `GET /api/leads/prospects/{prospect_id}/utkast` | 806 | |
| `PATCH /api/leads/prospects/{prospect_id}` | 2514 | `status` loggas `manuell` och synkas till extern CRM |
| `POST /api/leads/uppfoljning/svep` | 1319 | |

### 3.6 Support (för samma tidslinje)

`POST /api/drafts/{draft_id}/approve|omformulera|reject` (`app/api/drafts.py:23, 95,
148`), `GET /api/inbox`, `GET /api/inbox/{email_id}`, `POST /api/inbox/{email_id}/klassa`,
`/takeover`, `/hanterad`, `/befordra` (`app/api/inbox.py`). Se underlag 03.

### 3.7 Webhooks in (inte ut)

`POST /api/webhooks/resend/emails` (`app/api/sending_domains_api.py:27-33`) tar emot
`email.bounced`/`email.complained`, signaturkontrollerat, och skriver
`outreach_messages.leverans` via taggarna `tenant` och `meddelande` som sändaren satte
(`scheduler.py:557-562`).

---

## 4. Hur ett mejlsvar knyts till ett lead

Läst kedja:

1. **Hämtning.** IMAP-pollern sparar mejlet i `ss_emails` med `provider_message_id` =
   mejlets `Message-ID` (`app/email_pipeline/connectors/imap.py:257`). `In-Reply-To` och
   `References` sparas inte (sökt i `app/email_pipeline/`; de används bara UT, i
   `sender.py:72-82`, för supportsvar).
2. **Klassning** (`app/email_pipeline/klassning.py:118-152`): avsändare i suppressions →
   `ej_relaterat`. Annars `_prospektmatch` (rad 80-94) över ALLA prospekt
   (`limit=20_000`): **exakt `contact_email` (casefold)**, eller **samma domän som
   `website`** om domänen inte är en gratisdomän (gmail, hotmail, outlook, live.se,
   icloud, yahoo, telia, bredband, me, protonmail). Första träffen vinner. Träff →
   klass `lead` med `prospect_id` och `thread_id` (äldsta tråden).
3. **Styrning** (`processor.py:418-482`): `ss_emails.status='lead'`. Utan prospekt skapas
   ett nytt med `origin='inkorg'`. Med tråd anropas `hantera_prospektsvar`.
4. **Sparandet** (`svar.py:187`, `postgres.py:2001-2021`): en rad i `outreach_messages`
   (`direction='inbound'`, `body`, `sent_at=now()`, inget ämne) och
   `outreach_threads.last_inbound_at=now()`. Händelsen `svar` loggas direkt.
5. **Spår mellan mejlet och svaret:** bara `ss_decision_log` med `event='lead'`,
   `detail={prospect_id, thread_id, svar: <klass>}`. `outreach_messages` bär inget
   `email_id` (läst: schema i 1.4).
6. **Svar in över API** utan inkorg: `POST /api/leads/svar` med `thread_id` eller
   `prospect_id` (tråd skapas vid behov, `leads.py:1270-1287`).
7. **Utskicket** sätter `Reply-To` till kundens avsändaridentitet så att svaret hamnar i
   den synkade brevlådan (`scheduler.py:564-570`).

**Svagheter för CRM:et (antar, följer av koden):** två prospekt med samma webbdomän ger
första träffen; ett svar från en kollega på en gratisdomän matchar inte; inkommande tid
är hämtningstid, inte mejlets datum; ämnet går förlorat. Ett CRM med flera personer per
bolag kommer att vilja matcha per person (e-post) och sedan per bolag (domän/orgnr), och
spara `email_id` på svaret.

---

## 5. Händelselogg och prenumeration

**Läst: det finns ingen prenumererbar händelseström.** Det som finns:

| Mekanism | Vad den är | Duger som CRM-flöde? |
|---|---|---|
| `lead_handelser` (149) | Logg per tråd, se 2.5 | Delvis: täcker konversationen men inte utskick via kön, samtal (förutom möte), statusbyten, anteckningar |
| `prospect_status_logg` (086) | Varje statusbyte | Ja för status, komplett (skrivs i `update_prospect`) |
| `synk_andrad_at` + `synk_raderingar` (111) | Ändringstid per rad och raderingslogg på `prospects`, `prospect_status_logg`, `outreach_threads`, `outreach_messages`, `send_queue`, `lead_samtal`, `lead_anteckningar`, `lead_uppgifter`, `suppressions`, `ss_*` m.fl.; `lead_handelser` sedan 149 | **Bästa befintliga markören** för att hämta "allt som ändrats sedan X". Byggd för dev/main-synken (`scripts/railway_synk.py`) |
| `ss_decision_log` | Supportmejlens beslut | För support |
| `platform_events` (026) / `app/api/events.py` | Fel och varningar per plattform | Nej, en fellogg |
| `app/jobs/stream.py` | Redis-ström för chattjobb | Nej |
| `app/notifications/prioriterat_mejl.py` | Mejl till Snajps egen inkorg | Nej |
| `app/leads/crm_synk.py` | Envägssynk UT till HubSpot/Pipedrive: bolag + en anteckning per statusbyte eller anteckning | Mönstret för "skicka ut"; fire-and-forget, kastar aldrig |

En händelse i `lead_handelser` ser ut så här i API:t
(`leads_konversationer.py:273-277`):

```json
{"id": "uuid", "typ": "steg", "kalla": "manuell",
 "detalj": {"fran": "svarat", "till": "mote", "aterkom_datum": null},
 "tid": "2026-11-22T10:14:03+00:00", "olast": false}
```

och en notis (`leads_konversationer.py:540-547`):

```json
{"id": "uuid", "typ": "svar", "tid": "…", "last": false, "thread_id": "uuid",
 "prospect_id": "uuid", "company_name": "…", "klass": null, "oppnat": false}
```

---

## 6. Förslag: avbildningen på CRM:ets tidslinje (antar, inget av detta finns)

### 6.1 Princip

- **Tidslinjen komponeras ur källorna, den kopieras inte** (samma beslut som 086:4-6 och
  `leads_suite.py:5-7`). Ett CRM-bolag (orgnr) slår upp sina prospekt med
  `prospects.foretagsnyckel = <orgnr-siffror>` per tenant; personen slås upp på
  `contact_email`. Bolagets tidslinje = unionen av prospektens poster; personens =
  posterna på prospekt där `contact_email` är personens.
- **Varje post har en stabil nyckel** `<källa>:<id>` så att CRM:et kan deduplicera och
  ett tvåvägs-API kan peka på en post.
- **Webbplatsbedömningen följer aldrig med.**
- **Undvik dubbla poster:** ett svar finns både som `outreach_messages` (inbound) och
  `lead_handelser.svar`; ett samtal med `mote` både i `lead_samtal` och som
  `lead_handelser.mote`. Tidslinjen visar källraden och använder händelsen bara som
  komplement (klass, notis).

### 6.2 Tidslinjeposterna

Länkarna är Snajps befintliga vyer: `/dashboard/leads?vy=konversationer&trad=<thread_id>`
och `?lead=<prospect_id>` (läst: `components/leads/LeadsSida.tsx:130-155`; att
`/dashboard/leads` är sökvägen bygger på att den förekommer 10 gånger i `components/`
och `lib/`).

| Källa | Posttyp | Tid | Rubrik (sv) | Länk tillbaka | Nyckel |
|---|---|---|---|---|---|
| `outreach_messages` outbound, `sent_at` satt, första i tråden | `mejl_skickat` | `sent_at` | "Iris mejlade: <subject>" | konversationen | `msg:<id>` |
| samma, nummer n ≥ 1 | `uppfoljning_skickad` | `sent_at` | "Uppföljning n av 4: <subject>" (4 = sista) | konversationen | `msg:<id>` |
| samma med `kampanj_id` | `kampanjmejl` | `sent_at` | "Kampanj <namn>: <subject>" | kampanjen | `msg:<id>` |
| `outreach_messages` inbound | `svar` | `sent_at` | "<contact_name> svarade" + klass ur `svarsklass`/`klassad` | konversationen | `msg:<id>` |
| outbound utan `sent_at`, utan `kasserad_at` | `utkast_vantar` (tillstånd, inte historik; visas överst som "nästa steg") | `created_at` | "Utkast väntar på granskning" + `utkaststatus` | granskningen/konversationen | `msg:<id>` |
| `send_queue` `blocked` | `utkast_stoppat` | `behandlad_at` ?? `created_at` | "Utskick stoppat: <send_guard_skal>" | leadet | `sq:<id>` |
| `outreach_messages.leverans` | `studs` / `klagomal` | `leverans_at` | "Mejlet studsade" / "Markerat som skräppost" | leadet | `lev:<msg id>` |
| `ss_demolank_handelser` (`skanner=false`) | `demo_klick` / `demo_besok` | `created_at` | "Klickade på demolänken" / "Besökte demon" | leadet | `demo:<id>` |
| `lead_samtal` | `samtal` | `created_at` | "Samtal: Ej svar / Återkom <datum> / Ej intresserad / Kontakta inte / Möte bokat" + `anteckning` | `?vy=samtal` | `samtal:<id>` |
| `lead_handelser.steg` | `steg` | `created_at` | "Konversationen flyttad till <till>" | konversationen | `h:<id>` |
| `lead_handelser.mote` utan samtal samma minut | `mote_bokat` | `created_at` | "Möte bokat" | konversationen | `h:<id>` |
| `lead_handelser.overlamnat` | `overlamnat` | `created_at` | "Iris lämnade över till en människa" + `eskalerat` | konversationen | `h:<id>` |
| `lead_handelser.extern` | `mejl_extern` | `detalj.tid` | "Mejl utanför Snajp" | konversationen | `h:<id>` |
| citat ur svaren (`konversation.externa_ur_citat`) | `mejl_extern` | ur citathuvudet | som ovan | konversationen | `citat:<nyckel>` (beräknas vid läsning, lagras inte) |
| `lead_handelser.utkast_*`, `generering_*` | utelämnas på bolagets tidslinje (arbetsdetalj); visas i konversationen | | | | |
| `prospect_status_logg` | `status` | `created_at` | "Status: <fran> → <till>" (UI översätter) | leadet | `st:<id>` |
| `lead_anteckningar` | `anteckning` | `created_at` | texten | leadet | `ant:<id>` |
| `lead_uppgifter` | `uppgift` | `created_at` (och `klar_at`) | titel, förfaller | leadet | `upp:<id>` |
| `prospects` | `skapad` | `created_at` | "Blev lead (<origin>)" | leadet | `p:<id>` |
| `prospects.arkiverad_at` | `arkiverad` | `arkiverad_at` | "Arkiverad" | leadet | `ark:<id>` |
| `outreach_threads.aterkom_datum` | `aterkom` (framtida påminnelse) | datumet | "Hör av er igen" | konversationen | `ak:<thread_id>` |
| `ss_tickets` (matchat på e-post/domän) | `supportarende` | `created_at`, status-byten | "Supportärende: <subject>" | ärendet | `t:<id>` (se underlag 03) |

Statusbyten som följer av ett svar, samtal eller steg samma sekund kan fällas ihop med sin
orsak i UI:t; som data står de kvar.

### 6.3 Utfall som ska speglas åt båda hållen

Ut ur Snajp till CRM:et (läsning) gäller allt i 6.2. Åt båda hållen, alltså att CRM:et
får ändra och Snajp verkställer, föreslår jag bara de utfall som redan har en
verkställande funktion, så att CRM:et aldrig skriver i tabellerna direkt:

| Utfall i CRM:et | Verkställs i Snajp av | Sidoeffekter som MÅSTE följa med |
|---|---|---|
| Möte bokat | `konversation.satt_steg(nytt="mote")` om tråd finns, annars `samtal.registrera(utfall="mote")` eller `update_prospect(status="meeting")` | Väntande utskick stoppas, notis |
| Ej intresserad | `satt_steg("ej_intresserad")` | Kö stoppas, återkontakt om N månader |
| Kontakta inte | `satt_steg("kontakta_inte")` | Kö stoppas, adressen i `suppressions`. Får aldrig tas bort av CRM:et utan människa (antar: skyddet mot återkontakt) |
| Återkom (datum) | `satt_steg("aterkom", aterkom_datum)` | Datumet lyfter konversationen till Att göra och återkopplingslistan |
| Samtal med utfall | `POST /api/leads/prospects/{id}/samtal` | Som 2.2 |
| Anteckning, uppgift | befintliga POST | |
| Vunnen (`won`) | `PATCH /api/leads/prospects/{id}` `status=won` | Ingen kodväg utöver statusloggen i dag |
| **Blev kund** (CRM:ets eget, Buddy-synken) | ny: bolaget till CRM-kundlistan (`lead_lists.kalla='crm'`, 098) så att `upptagna.py` utesluter det, + ev. `won` | Iris får aldrig prospektera det igen |

In från Snajp till CRM:et ska varje statusbyte, svarsklass och samtalsutfall spegla
CRM:ets fas/steg. Konfliktregel (antar): Snajps avslutande utfall (`suppressed`) vinner
alltid över ett CRM-värde som skulle öppna leadet igen.

### 6.4 Vad som behöver byggas för att det ska hålla

1. **En komplett händelsekälla.** Antingen loggas `skickat` (och `utkast_avvisat`) i
   `lead_handelser` också från `scheduler._process_due_item` och
   `POST /api/leads/queue/{id}/approve|reject`, eller så läser CRM:et utskicken ur
   `outreach_messages.sent_at` som i 6.2 (rekommenderat: källraden är redan sanningen).
2. **En läsmarkör för tvåvägs-API:t:** `synk_andrad_at` finns på alla berörda tabeller
   och `synk_raderingar` fångar raderingar. Ett `GET /api/crm/tidslinje?sedan=<tid>` kan
   läsa på den utan nya kolumner (antar). Det finns inget index på `synk_andrad_at` i
   någon migration (läst: grep över `db/migrations/` 2026-11-25), så ett sådant läsanrop
   behöver ett additivt index per tabell, `(tenant_id, synk_andrad_at)`.
3. **Vem gjorde det:** ingen tabell bär en användare. Lägg `utford_av` (nullable) på
   `lead_samtal`, `lead_handelser`, `lead_anteckningar`, `prospect_status_logg` i en
   additiv migration, och skicka användaren från webben.
4. **Person per bolag:** `prospects` har en kontakt. CRM:ets personer måste ligga i en
   egen tabell med `foretagsnyckel`/orgnr och kopplas till prospektet via
   `contact_email`.
5. **Svar ↔ mejl:** spara `ss_emails.id` (och originalets `Date`/ämne) på det inkomna
   `outreach_messages`-raden, så att tidslinjen visar rätt tid och ämne och länkar till
   mejlet.

### 6.5 Fel i den befintliga tidslinjen som CRM:et inte ska ärva (läst)

`leads_suite.py:163-175`: `nar = m.get("sent_at") or m.get("created_at")` och raden
hoppas över bara om båda saknas. Sedan migration 107 är `created_at not null default
now()`, så **väntande och kasserade utkast visas som `mejl_ut`**, alltså som skickade
mejl, och kommentaren "osänt utkast: ingen händelse än" stämmer inte längre. Rätt villkor
är `direction='inbound' or sent_at is not null`. Inkomna svar visas med tom rubrik
eftersom deras `subject` är `''`.

---

## 7. Öppna frågor

1. Ska CRM:et få sätta Kontakta inte och därmed spärra adressen, eller bara föreslå det?
2. Gäller "befintlig kund" (Buddy-synken) per orgnr eller per e-postdomän när orgnr
   saknas? `foretagsnyckel` faller tillbaka på domänen.
3. Ska `won` få en verkställande funktion (stoppa kö, lägga bolaget i kundlistan) eller
   förbli bara en status?
4. Ska svarsutkast och genereringar synas på bolagets tidslinje, eller bara i
   konversationen (förslaget: bara i konversationen)?
5. Ska supportärenden kopplas på e-post, domän eller ett explicit orgnr på
   `ss_customers`?
