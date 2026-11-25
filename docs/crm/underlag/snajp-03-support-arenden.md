# Underlag 03 — Kundtjänstsidan: ärenden, slutkunder, kanaler

Underlag för Snajp CRM (beslut 2026-11-25, `docs/BESLUT.md:12-50`). Skrivet 2026-11-25 av en
läsande agent på grenen `claude/snajp-crm-dd0d83`. Ingen befintlig fil är ändrad.

**Läsanvisning.** Varje påstående om koden bär fil:rad. Sökvägar under `app/` avser
`snajp-support/app/`, migrationer avser `db/migrations/`. Det som är **[antagande]** eller
**[förslag]** är markerat så; allt annat är läst i koden.

---

## 0. Det viktigaste först (för den som ska bygga)

1. **Slutkunden heter `ss_customers` och har bara `id`, `name`, `created_at`, `tenant_id`**
   (`002_snajp_support.sql:7-11`, `003_snajp_multitenant.sql:35-45`). Identiteten bor i
   `ss_customer_identifiers` med `type in ('email','phone')`, unik per `(tenant_id, type, value)`
   (`002:13-20`, `003:49-52`). **Det finns inget bolagsbegrepp alls på supportsidan**: inget
   orgnr, ingen domän, ingen koppling till `prospects`.
2. **Ett ärende per inkommande meddelande.** Varje chattmeddelande och varje mejl skapar ett
   nytt `ss_tickets` + ett `ss_conversations` (`app/agent/support_agent.py:1384-1401`,
   `app/email_pipeline/processor.py:692-712`, kommentar i `066_support_samtalslage.sql:5-8`).
   "Samtalet" är därför en *kund*, inte ett ärende. Tidslinjen i CRM:et ska byggas per
   `customer_id`, inte per ärende. `parent_ticket_id` finns i schemat (`002:33`) men används
   ingenstans i Python-koden (grep utan träff i `app/`).
3. **Matchningen i dag är exakt e-post (skiftlägesokänslig) och sedan exakt telefon**, utan
   normalisering av telefonnummer (`app/storage/postgres.py:529-566`). Webbchattens besökare
   har en **påhittad adress `<uuid>@session.snajp.se`** (`app/api/chat.py:312-317`) som aldrig
   får matchas mot ett bolag.
4. **Sekretess:** allt i `ss_messages`, `ss_emails`, `ss_drafts`, `customer_memory` är kundens
   kunders personuppgifter. DeepSeek är förbjudet i varje miljö med riktig data
   (`app/config.py:793-860`), development är en spegel av produktionen, och det finns **inga
   utgående webhooks i dag** (grep efter webhook-utskick i `app/` träffar bara inkommande
   kanalwebhooks i `app/api/kanaler.py`). Ett tvåvägs-API och webhooks ut är alltså en ny
   överföringsväg och ska behandlas som ett nytt underbiträdes-/mottagarflöde (se § 6).
5. **Gallringen raderar på riktigt** (`048_gallring.sql:23-27`, `119_gallring_alla_kategorier.sql:31-41`):
   `ss_customers` raderas med kaskad. CRM-tabeller som pekar på supportrader måste tåla att
   raderna försvinner (FK `on delete set null`/`cascade`), och en webhook-mottagare får inte bli
   en kopia som aldrig gallras.

---

## 1. Tabellerna

Alla tabeller nedan har `tenant_id uuid not null references ss_tenants(id)` och RLS-policyn
`tenant_isolation` (`tenant_id = current_setting('app.tenant_id', true)::uuid`) om inget annat
sägs. Mönstret: `003_snajp_multitenant.sql:67-83`. Applikationen sätter `app.tenant_id` per
transaktion via `_scoped(tenant_id)` i `app/storage/postgres.py` och filtrerar dessutom
explicit på `tenant_id` i varje fråga (t.ex. `postgres.py:540`, `604`, `650`).

Tabellerna i listan i `111_tvavagssynk.sql:57-60` har dessutom kolumnen
`synk_andrad_at timestamptz not null default now()` och triggrarna `synk_markera`/`synk_radera`
(`111:67-73`) för tvåvägssynken development↔main. Det gäller `ss_customers`,
`ss_customer_identifiers`, `ss_tickets`, `ss_conversations`, `ss_messages`, `ss_emails`,
`ss_email_attachments`, `ss_classifications`, `ss_decision_log`, `ss_drafts`,
`ss_human_reviews`, `customer_memory`, `ss_agent_metrics`.

### 1.1 Slutkund och identitet

**`ss_customers`** (`002:7-11`, tenant `003:35-45`)
| kolumn | typ | anm. |
|---|---|---|
| id | uuid pk | |
| name | text, null | sätts bara när kunden skapas, uppdateras aldrig (`postgres.py:549-553`) |
| created_at | timestamptz | |
| tenant_id | uuid not null | |
| synk_andrad_at | timestamptz | (111) |

**`ss_customer_identifiers`** (`002:13-20`, unik nyckel omlagd i `003:49-52`)
| kolumn | typ | anm. |
|---|---|---|
| id | uuid pk | |
| customer_id | uuid → ss_customers on delete cascade | |
| type | text check `('email', 'phone')` | |
| value | text | lagras `lower($4)` (`postgres.py:558`), även telefon |
| created_at | timestamptz | |
| tenant_id | uuid | unik `(tenant_id, type, value)` |

**`ss_channel_contacts`** (`067_integrationer_och_kanaler.sql:103-122`) — vem på en extern kanal
som är vilken slutkund.
| kolumn | anm. |
|---|---|
| id, tenant_id | |
| anslutning_id → ss_channel_connections on delete cascade | |
| customer_id → ss_customers on delete cascade | |
| extern_anvandare text | WhatsApp `wa_id` (telefon), Messenger PSID, Slack användar-id, Teams aad-id (`067:109-110`) |
| adress jsonb | allt som behövs för att svara senare (Slack-kanal, Teams serviceUrl) |
| visningsnamn text | |
| created_at, updated_at | unik `(anslutning_id, extern_anvandare)` |

**`ss_chat_state`** (`066_support_samtalslage.sql:35-55`) — samtalsläget per slutkund.
PK `(tenant_id, customer_id)`. Kolumner: `lage text check ('agent','overlamnad')`,
`misslyckade_i_rad int`, `erbjod_manniska bool`, `overlamnad_orsak text` (kod ur
`support_regler.ORSAKER`), `overlamnad_ticket_id → ss_tickets on delete set null`,
`overlamnad_at`, `sprak text` (ISO 639-1, null = svenska), `updated_at`.

**`customer_memory`** (`052_customer_memory.sql:25-35`) — fakta som *slutkunden själv* uppgett.
Kolumner: `id`, `tenant_id`, `customer_id → ss_customers on delete cascade`, `fakta text`,
`created_at`. ADD-only. Uttryckligen aldrig agentens slutsatser eller sentiment (`052:12-21`).

### 1.2 Ärende, konversation, meddelande

**`ss_tickets`** (`002:22-36`; tenant `003`; `is_test` `057:12-13`; kategori- och kanalvillkor
omlagda, se § 3)
| kolumn | typ / villkor |
|---|---|
| id | uuid pk |
| customer_id | uuid not null → ss_customers on delete cascade |
| subject | text default '' |
| category | text, se § 3 |
| status | text default `'open'`, se § 3 |
| priority | text default `'normal'`, se § 3 |
| escalation_reason | text |
| channel | text default `'web'`, se § 3 |
| parent_ticket_id | uuid → ss_tickets (oanvänd i koden) |
| created_at, updated_at | timestamptz |
| tenant_id | uuid not null |
| is_test | boolean default false (057) |
| synk_andrad_at | (111) |

Index: `ss_tickets_customer_idx (customer_id)`, `ss_tickets_category_idx`, `ss_tickets_is_test_idx`
(partiellt, `057:30-32`).

**`ss_conversations`** (`002:41-46`): `id`, `ticket_id uuid not null unique → ss_tickets on delete
cascade`, `channel text default 'web'`, `created_at`, `tenant_id`. Exakt ett samtal per ärende.

**`ss_messages`** (`002:48-56`; `author` `066:30-33`)
| kolumn | typ / villkor |
|---|---|
| id | uuid pk |
| conversation_id | → ss_conversations on delete cascade |
| direction | `'inbound'` \| `'outbound'` |
| content | text not null (fulltext, kundskriven) |
| sentiment | numeric(3,2) 0–1 (modellens bedömning) |
| has_image | boolean |
| author | null \| `'customer'` \| `'agent'` \| `'human'` (null = äldre rad: inbound=kund, outbound=agent, `066:22-27`) |
| created_at, tenant_id, synk_andrad_at | |

**`ss_agent_metrics`** (`002:88-94`): `id`, `ticket_id → ss_tickets on delete set null`,
`metric_name`, `value numeric`, `created_at`, `tenant_id`.

### 1.3 Mejlflödet (inkorgen, "Ärenden" i portalen)

**`ss_mailboxes`** (`004_snajp_email_pipeline.sql:6-16`): `id`, `tenant_id`,
`provider in ('gmail','outlook','imap','mock')`, `address`, `status in ('active','error','disabled')`,
`last_sync_at`, `last_error`, `created_at`, unik `(tenant_id, address)`. Tillägg:
`syfte in ('support','leads','bada')` default `'support'` (`084_inkorg_klass.sql:18-20`),
`imap_last_uid bigint`, `imap_uidvalidity bigint` (`150_last_i_brevladan.sql`).

**`ss_emails`** (`004:19-37`)
| kolumn | anm. |
|---|---|
| id, tenant_id, mailbox_id → ss_mailboxes | |
| provider text default 'mock' | `'api'` för `POST /api/inbox/ingest` (`app/api/inbox.py:414`) |
| provider_message_id text | unik `(tenant_id, provider_message_id)` |
| from_email text not null | lagras som det kom, inte gemener (jämför `processor.py:440`, som gör `.lower()` vid läsning) |
| from_name text | |
| subject, body_text | fulltext, kundskriven |
| received_at | |
| status | se § 3 |
| ticket_id → ss_tickets | sätts när CRM-stegen körts (`processor.py:712`) |
| created_at, updated_at | |
| is_test bool | (057) |
| hanterad_at timestamptz | manuell avbockning (`071_inkorgsflaggor.sql:32-33`) |
| klass | null \| `'support'` \| `'lead'` \| `'ej_relaterat'` (`084:13-16`) |
| klass_kalla text | `regel` \| `jev` \| `syfte` \| `standard` \| `manuell` (kommentar `084:10`) |
| automatutskick bool | (`092_automatutskick.sql:12-13`) |
| last_i_brevladan, besvarat_i_brevladan bool | (`150`) |

**`ss_email_attachments`** (`004:42-53`): `id`, `tenant_id`, `email_id → ss_emails on delete cascade`,
`filename`, `content_type`, `size_bytes`, `data_url` (base64 i databasen), `is_image`, `created_at`.

**`ss_classifications`** (`004:56-72`): `id`, `tenant_id`, `email_id → ss_emails cascade`,
`category`, `priority text default 'normal'` (inget check-villkor), `sentiment`, `confidence`,
`escalate bool`, `escalation_reason`, `reasoning`, `kb_sources jsonb`, `model`, `created_at`,
plus `offertforfragan bool`, `utbildningsintresse bool` (`071:22-25`).

**`ss_drafts`** (`004:75-87`): `id`, `tenant_id`, `email_id → ss_emails cascade`,
`ticket_id → ss_tickets`, `content`, `status in ('pending','approved','rejected','auto_sent')`,
`auto bool`, `confidence`, `created_at`, `updated_at`.

**`ss_human_reviews`** (`004:92-100`): `id`, `tenant_id`, `draft_id → ss_drafts cascade`,
`action in ('approve','edit','reject','takeover')`, `edited_content`, `note`, `created_at`.

**`ss_category_rules`** (`004:103-109`): `tenant_id`, `category`,
`mode in ('auto','draft','escalate')`, unik `(tenant_id, category)`.

**`ss_decision_log`** (`004:112-119`): `id`, `tenant_id`, `email_id → ss_emails cascade`,
`event text`, `detail jsonb`, `created_at`. Händelsenamn som skrivs i koden bl.a.:
`klassning`, `omklassning`, `taken_over`, `hanterad`, `ohanterad`, `reprocessed`, `befordrad`
(`app/api/inbox.py:542-713`), `approved_and_sent` (`app/api/drafts.py:79`), `auto_sent`
(räknas i `postgres.py:3829`).

### 1.4 Kanaler och konfiguration

**`ss_channel_connections`** (`067:72-92`): `id`, `tenant_id`,
`kanal in ('whatsapp','messenger','slack','teams')`, `namn`, `extern_id` (unik per kanal över alla
tenants), `konfig jsonb`, `hemlighetsnamn text[]`, `hemligheter_krypterat text` (Fernet),
`aktiv`, `created_at`, `updated_at`.

**`ss_channel_inbound_seen`** (`067:132-141`): PK `(anslutning_id, extern_meddelande_id)`,
`tenant_id`, `seen_at`. Dubblettspärr.

**`ss_channel_configs`** (`002:76-86`, `003:56-63`, `067:162-172`): `id`, `tenant_id` (null =
global standard), `channel`, `tone`, `max_length`. Läsbar för alla tenants på globala rader
(`003:95-98`).

**`ss_integrations`** (`067:43-58`): kundens HTTP-/MCP-verktyg åt agenten,
`typ in ('http','mcp')`. Hemligheter krypterade.

### 1.5 Övrigt som rör support men inte slutkunden

- Kunskapsbasen: `ss_knowledge_base` (`002:60-70`, `117` `source_url`, `giltig_till`,
  `is_placeholder` `20260730204754:33`), `ss_kb_skanningar`, `ss_kb_forslag` (`121`),
  `ss_kb_version` (`137`). Ingen slutkunddata.
- `ss_gallringspolicy` (`048:31-40`): `tenant_id pk`, `dagar int check (>=30)`, `beslutad_av`,
  `beslutad_at`. Ingen rad = ingen gallring (`048:11-14`).
- **Förväxlingsrisk:** `ss_customer_details` och `ss_customer_contacts`
  (`053_kundregister.sql:28-63`) är **Snajps egna kunder (tenants)**, inte slutkunder.
  Admin-only via RLS (`053:120-133`). CRM:et ska inte blanda ihop dem med `ss_customers`.

---

## 2. Hur slutkunden identifieras

### 2.1 Uppslaget
`find_or_create_customer(tenant_id, *, email, phone, name)` (`app/storage/postgres.py:529-566`):
1. Slår upp `email` först, sedan `phone`, i `ss_customer_identifiers` med
   `lower(i.value) = lower($3)` (`:536-546`). Första träff vinner och returneras.
2. Ingen träff → ny `ss_customers` med `name`, och en identifierare per angivet värde,
   `lower(value)`, `on conflict do nothing` (`:549-565`).

Konsekvenser (läst):
- **Telefon normaliseras inte.** `+46701234567`, `070-123 45 67` och `0046…` blir tre olika
  identifierare. WhatsApp ger `+<wa_id>` (`app/kanaler/whatsapp.py:88`).
- **En träff på e-post lägger inte till ett nytt telefonnummer** och uppdaterar inte namnet.
- `find_customer(tenant_id, *, email)` (`postgres.py:757-770`) är en ren läsning, används av
  `POST /api/chat/samtal`.

### 2.2 Per kanal
| Väg | e-post | telefon | namn | externt id |
|---|---|---|---|---|
| Mejl (IMAP/ingest) | `from_email` | — (`processor.py:692-694`, `phone=None`) | `from_name` | `provider_message_id` på mejlet, inte på kunden |
| Webbchatt (`POST /api/chat`) | `customer_email` ur anropet; widgeten skickar `<uuid>@session.snajp.se` (`chat.py:312-317`) | `customer_phone` (agentparameter, `support_agent.py:1078-1080`) | `customer_name` | — |
| Chatt via tenantens egen integration | en riktig adress om tenanten skickar den (`chat.py:313-315`) | | | |
| WhatsApp | — | `+wa_id` | visningsnamn | `ss_channel_contacts.extern_anvandare` |
| Messenger | — | — | visningsnamn | PSID (`067:109`) |
| Slack | profilens e-post om scope `users:read.email` finns (`app/kanaler/slack.py:149`) | — | visningsnamn | Slack användar-id |
| Teams | — | — | visningsnamn | aad-id |

Kanalkunder hittas först via `ss_channel_contacts` och skapas först därefter
(`app/kanaler/mottagning.py:91-112`). En Messenger-kund har alltså varken e-post eller telefon
(`mottagning.py:11-15`).

### 2.3 Bolagsbegrepp
**Inget.** Varken `ss_customers`, `ss_tickets` eller `ss_emails` bär orgnr, domän eller
bolagsnamn (§ 1). Det närmaste är avsändardomänen i `ss_emails.from_email` och i
`ss_customer_identifiers.value`. Bolaget måste härledas i CRM:et.

En korsning finns redan åt leads-hållet: ett mejl som klassas `lead` och saknar prospekt blir
`prospects` med `origin='inkorg'` och `company_name` = avsändarnamnet eller e-postdomänen
(`processor.py:440-447`, `084:33-37`). Det är en enkelriktad gissning utan orgnr.

---

## 3. Statusar, prioriteter, kategorier, kanaler (ordagrant)

**`ss_tickets.status`** (`002:28-29`): `'open'`, `'in_progress'`, `'escalated'`, `'resolved'`,
`'closed'`. Övergången får bara gå framåt: `STATUS_ORDER = ["open", "in_progress", "escalated",
"resolved", "closed"]` och `status_transition_allowed` kräver `index(new) >= index(current)`
(`app/storage/base.py:2471-2478`); en otillåten övergång ignoreras tyst (`postgres.py:696-698`).
Skrivs i koden: `escalated` (`processor.py:771`, `support_agent.py:2357`), `resolved`
(`processor.py:859`, `drafts.py:77`), `closed` vid omklassning bort från support (`inbox.py:498-499`).
`in_progress` skrivs inte någonstans jag hittat [antagande: oanvänd].

**`ss_tickets.priority`** (`002:30`): `'low'`, `'normal'`, `'high'`. Mejltriagen ger
`low|normal|high` (`app/agent/triage.py:31`, `:210-216`); chattflödet sätter `high` om triagen
ger `P1`/`P2`, annars `normal` (`support_agent.py:1390`); eskalering i mejlflödet sätter `high`
(`processor.py:771`).

**`ss_tickets.category`** (gällande villkor `20260730204754_snajp_pilot_categories.sql:18-21`):
`'teknisk_support'`, `'garanti'`, `'leverans'`, `'utbildning'`, `'retur_reklamation'`,
`'betalning'`, `'orderstatus'`, `'ovrigt'`. Speglas i `app/config.py:43-52` (`CATEGORIES`).
(`'konto'` finns inte längre; agentverktygets docstring nämner det fortfarande,
`app/agent/tools.py:97`, men värdet faller till `ovrigt`, `:101-102`.)

**`ss_tickets.channel`** (`067:155-157`): `'web'`, `'email'`, `'whatsapp'`, `'messenger'`,
`'slack'`, `'teams'`.

**`ss_emails.status`** (`084:24-29`): `'new'`, `'processing'`, `'awaiting_approval'`,
`'auto_sent'`, `'sent'`, `'escalated'`, `'rejected'`, `'taken_over'`, `'failed'`,
`'att_hantera'`, `'lead'`, `'ej_relaterat'`. Översiktens tolkning: `auto_sent` = agentens svar,
`sent` = godkänt utkast, `escalated`/`taken_over`/`rejected` = till människa
(`app/support_oversikt.py:12-14`, `:37-39`).

**`ss_emails.klass`**: `'support'`, `'lead'`, `'ej_relaterat'` (null = oklassad).
**`ss_drafts.status`**: `'pending'`, `'approved'`, `'rejected'`, `'auto_sent'`.
**`ss_human_reviews.action`**: `'approve'`, `'edit'`, `'reject'`, `'takeover'`.
**`ss_category_rules.mode`**: `'auto'`, `'draft'`, `'escalate'`.
**`ss_messages.direction`**: `'inbound'`, `'outbound'`; **`author`**: `'customer'`, `'agent'`, `'human'`.
**`ss_chat_state.lage`**: `'agent'`, `'overlamnad'`.
**Överlämningsorsaker** (`app/agent/support_regler.py:217-226`): `kund_bad_om_manniska`,
`utanfor_amnesomradet`, `utanfor_kunskapsbasen`, `fortydligandetak`, `sakerhet`, `pahopp`,
`modellbedomning`, `medarbetare_tog_over`.

---

## 4. Endpoints

Behörighet: `require_tenant` = giltig `X-API-Key` som hör till en tenant; master-nyckeln får 403
(`app/api/deps.py:62-72`). Demo-nyckeln mappar till Nordlys Handel (`deps.py:48-49`),
`snajp_live_`-nycklar slås upp i `ss_api_keys` (`deps.py:52-58`). `require_master_key` loggar
varje anrop i `audit_logs` (`deps.py:75-87`). Portalen når tenant-routerna via Next-proxyn
`/api/ag/*` med tenantens nyckel (`app/api/chattar.py:3-5`); proxyn sätter `X-Snajp-Demo` ur
`workspaces.is_demo` (`inbox.py:76-78`) och `X-Snajp-User` (`chat.py:252-254`).

### Ärenden och slutkund
| Metod | Sökväg | Behörighet | Vad | Fil |
|---|---|---|---|---|
| GET | `/api/tickets/{ticket_id}` | tenant | ärendet + `conversation_id` + alla `messages` | `tickets.py:10-18`, `postgres.py:647-675` |
| GET | `/api/customers/{customer_id}/history` | tenant | kundens senaste **20** ärenden, nyast först, med `conversation_id` | `tickets.py:21-29`, `postgres.py:568-610` |

Ingen endpoint listar slutkunder, söker på e-post eller visar identifierare. Ingen skriver ett
ärende utifrån (utom via chatt/ingest).

### Chatt
| Metod | Sökväg | Behörighet | Vad |
|---|---|---|---|
| POST | `/api/chat` → 202 `{job_id}` | tenant | kör supportagenten i bakgrunden (`chat.py:236-310`); avtalsgrind 403, kvot/budget 429 |
| POST | `/api/chat/samtal` | tenant | chattfönstrets samtal; **bara** `…@session.snajp.se` (`chat.py:320-353`) |
| GET | `/api/jobs/{job_id}` | tenant (jobbets tenant) | status/resultat/fas (`chat.py:368-390`) |
| POST | `/api/triage` | tenant | synkron sortering av ≤20 mejl, sparar inga ärenden (`triage.py:56-124`) |

### Överlämnade chattar (medarbetarens vy)
| Metod | Sökväg | Behörighet | Vad |
|---|---|---|---|
| GET | `/api/chattar` | tenant | överlämnade samtal (≤100) med kundnamn, ämne, kategori, kanal (`chattar.py:32-35`, `postgres.py:899-918`) |
| GET | `/api/chattar/{customer_id}` | tenant | hela samtalsutskriften över kundens ärenden (`chattar.py:38-48`, `overlamning.py:50-75`) |
| POST | `/api/chattar/{customer_id}/svar` → 201 | tenant | medarbetarsvar, levereras i kanalen (`chattar.py:51-88`) |
| POST | `/api/chattar/{customer_id}/aterlamna` | tenant | lämnar tillbaka till agenten (`chattar.py:91-97`) |

### Inkorgen (mejl)
Alla `require_tenant` (`inbox.py`):
`POST /api/inbox/mock` (201, testmail, `:35`), `GET /api/inbox/mailboxes` (`:148`),
`GET /api/inbox/mailboxes/upptack` (`:199`), `POST /api/inbox/mailboxes` (`:212`),
`DELETE /api/inbox/mailboxes/{mailbox_id}` (`:312`), `POST /api/inbox/sync` (`:324`),
**`POST /api/inbox/ingest`** (201, API-first-ingest för externa system, `:407-436`; kropp
`from`, `from_name`, `subject`, `body`, `provider_message_id`, `attachments`, `schemas.py:793-803`;
409 vid dubblett), `GET /api/inbox` (query `status`, `category`, `q`, `limit` ≤200, `is_test`,
`klass`; `:448-487`), `POST /api/inbox/sortera` (`:502`), `POST /api/inbox/{email_id}/klassa`
(`:557`), `GET /api/inbox/{email_id}` (`:584`), `POST /api/inbox/{email_id}/takeover` (`:594`),
`POST /api/inbox/{email_id}/hanterad` (`:616`), `POST /api/inbox/{email_id}/processa-om`
(bara `failed`/`new`, annars 409; `:644-687`), `POST /api/inbox/{email_id}/befordra` (`:690`).

### Utkast och regler
`POST /api/drafts/{draft_id}/approve` (skickar **före** statusskrivning, 502 vid sändfel,
`drafts.py:23-92`), `POST /api/drafts/{draft_id}/omformulera` (`:95`),
`POST /api/drafts/{draft_id}/reject` (`:148`), `GET`/`PUT /api/rules` (`rules.py:12`, `:23`).
Alla `require_tenant`.

### Konfiguration, översikt, KB
`GET`/`PUT /api/support/config` (`support_config.py:36`, `:44`), `GET /api/support/oversikt`
(`support_oversikt.py:21`), `GET /api/kb`, `POST /api/kb` (201), `DELETE /api/kb/{artikel_id}`,
`POST /api/kb/skanna` (202), `GET /api/kb/forslag`, `POST /api/kb/forslag/beslut`,
`POST /api/kb/extrahera` (`kb.py:65-395`). Alla `require_tenant`.

### Kanaler och integrationer
Prefix `/api/kanaler` (`kanaler.py:39`): `GET ""`, `POST ""` (201), `PATCH /{anslutning_id}`,
`DELETE /{anslutning_id}`, `POST /{anslutning_id}/prova` — `require_tenant`.
**Utan API-nyckel:** `GET` och `POST /api/kanaler/{kanal}/{tenant_id}/{anslutning_id}/webhook`
(`kanaler.py:233-275`); skyddas av kanalens signatur (`adapter.verifiera`), 413 över
`MAX_WEBHOOK_BYTES`, och bearbetas i bakgrunden (`mottagning.py:115-200`).
Prefix `/api/integrationer` (`integrationer.py:37`): `GET ""`, `POST ""`, `PATCH /{id}`,
`DELETE /{id}`, `GET /{id}/verktyg`, `POST /{id}/prova` — `require_tenant`.

### Admin (master)
`GET /api/admin/gallring`, `GET /api/admin/tenants/{tenant_id}/gallring`
(`admin_gallring.py:22-45`, `require_master_key`).

---

## 5. Knyta ärenden till person och bolag i CRM:et [förslag, byggt på det lästa]

### 5.1 Grundmodell
- **Person** i CRM:et ↔ **en eller flera** `ss_customers.id` (inom samma tenant). En länktabell
  behövs, t.ex. `crm_person_supportkund (tenant_id, person_id, customer_id, kalla, skapad_at)`,
  eftersom samma människa redan i dag kan vara flera `ss_customers` (session-adress i chatten,
  riktig adress i mejl, WhatsApp-nummer). Länken ska inte ligga som kolumn på `ss_customers`:
  supporttabellerna speglas mellan miljöerna (`111`) och gallras med kaskad.
- **Bolag** i CRM:et nås via personen, aldrig direkt från ärendet. Ett ärende får sitt bolag
  genom `ss_tickets.customer_id → länk → person → bolag`. Då följer en rättad
  personkoppling med till alla ärenden.
- FK från länktabellen till `ss_customers(id)` med `on delete cascade`: gallring av slutkunden
  (`119:34`) ska ta med länken, inte lämna en hängande pekare.

### 5.2 Matchningsordning
1. **Exakt e-post** (`lower(trim)`) mot CRM-personens e-postadresser → säker träff.
2. **Exakt telefon** efter normalisering till E.164 (`+46…`) på *båda* sidor. Supportens
   identifierare är inte normaliserade (§ 2.1), så CRM:et måste normalisera vid jämförelsen,
   inte förutsätta det.
3. **Kanal-id** (`ss_channel_contacts.extern_anvandare`) bara om CRM-personen har just det
   id:t registrerat; annars ingen automatisk koppling.
4. **E-postdomän → bolag** som *förslag*, aldrig som automatisk koppling till en viss person:
   - domänen jämförs med bolagets registrerade domäner/webbplats (orgnr är nyckeln för bolaget
     enligt beställningen; domänen är bara en väg dit);
   - ger domänen exakt ett bolag i CRM:et kan ärendet visas på bolagets tidslinje som
     "från någon på bolaget", och en ny person kan föreslås — men skapas först när en människa
     bekräftar, eller när kundens API-synk (Buddy) redan har personen.

### 5.3 Fällorna
- **Privata och delade domäner.** `gmail.com`, `hotmail.se`, `outlook.com`, `icloud.com`,
  `telia.com`, `bredband.net`, `spray.se` m.fl. (förteckning i
  `app/leads/discovery.py:137-161`, `_PRIVATA_DOMÄNER`) säger ingenting om bolaget. Domänmatchning
  ska aldrig köras på dem. Telia och Bredband är dessutom **internetleverantörer**: tusentals små
  bolag använder `@telia.com`. Notera motsatsen i leads-reglerna: en gmail-/telia-adress som
  bolaget *självt publicerar på sin webbplats* räknas där som bolagets adress (CLAUDE.md regel 13,
  `discovery.py:895`, `:1003`). Det gäller exakt adress, aldrig domänen. CRM:et ska därför kunna
  koppla en *exakt* gmail-adress till ett bolag (om bolaget publicerat den eller kunden synkat
  den) men aldrig *domänen* gmail.com.
  Återanvänd listan i stället för att skapa en andra kopia [förslag: flytta `_PRIVATA_DOMÄNER`
  och `ar_privat_epost` (`discovery.py:188-192`) till en delad modul].
- **Webbchattens påhittade adress** `…@session.snajp.se` (`chat.py:312-317`) får aldrig matchas
  på domän och aldrig visas som en kontaktadress. Den är en hemlig sessionsnyckel (122 bitar,
  `chat.py:314-316`); att visa den i CRM:et eller skicka ut den via API gör det möjligt att läsa
  besökarens samtal via `POST /api/chat/samtal`. **Behandla den som en hemlighet, inte som e-post.**
- **Bolagets egna funktionsadresser** (info@, kontakt@) på bolagets domän identifierar bolaget men
  inte en person. Koppla dem till bolaget, inte till en namngiven person.
- **Koncerner och flera bolag på samma domän**, och **återförsäljare/byråer** som skriver åt sina
  kunder: domänen kan peka på fel orgnr. Endast förslag, aldrig automatisk.
- **Kundens egna medarbetare och Snajps aviseringar.** Mejl från tenantens egen domän eller
  Snajps larm landar som `att_hantera` (`078_att_hantera.sql:1-26`) och ska inte bli
  CRM-aktivitet på något kundbolag.
- **`klass='lead'`-mejl** ligger i samma `ss_emails` men hör till Iris/prospekt
  (`processor.py:425-447`). De ska synas på bolagets tidslinje som leadsaktivitet, inte som
  supportärende. Filtrera supportens tidslinje på `coalesce(klass,'support')='support'` och
  `status not in ('att_hantera','lead','ej_relaterat')`, samma urval som översikten
  (`postgres.py:3838-3841`).
- **Testdata.** `is_test=true` på `ss_emails` och `ss_tickets` (`057`) ska aldrig in i CRM:et.
- **Ett ärende per meddelande** (§ 0.2): räkna inte "antal ärenden" som antal samtal. Gruppera
  på `customer_id` och tid för att visa "samtal" på tidslinjen.
- **Historiktaket.** `get_customer_history` ger högst 20 ärenden (`postgres.py:605`), och
  `samtalsutskrift` bygger på den (`overlamning.py:61`). En CRM-tidslinje behöver en egen,
  paginerad fråga, inte den här funktionen.
- **Befintliga kunder ut ur Iris.** Supportens slutkunder är *kundens kunder*. Att en adress
  finns i `ss_customer_identifiers` betyder inte att bolaget är kund (den kan vara en prospekt
  som frågat något). Uteslutning ur Iris ska bygga på CRM-bolagets status (synkad kundlista),
  inte på förekomst i supporten [antagande om önskat beteende; Antons att avgöra].

---

## 6. Sekretess och vad CRM:et får visa och skicka vidare

### 6.1 Vad som gäller (läst)
- **Allt supportinnehåll är personuppgifter som kunden (tenanten) är ansvarig för och Snajp
  biträde för.** DPIA:n räknar upp avsändarnamn, e-post, hela meddelandet, bilagor, agentens svar
  och beslutsloggen (`docs/dpia_supportagenten.md:72`). Personnummer kan förekomma i löptext;
  maskeringen (`app/moderation/maskering.py:1-33`) körs bara **på väg till modellen**
  (`support_agent.py:1223-1228`, `agent/triage.py:127-128`, `agent/embeddings.py:61`) —
  **databasens `content`/`body_text` är omaskerad**.
- **DeepSeek-förbudet.** `Settings.llm_provider_fault()` fäller uppstarten om
  `LLM_PROVIDER=deepseek` i en miljö med riktig kunddata (`app/config.py:793-815`, `:856-860`),
  och CLAUDE.md slår fast att development räknas dit (spegel). Ett CRM-flöde som anropar en modell
  med supportinnehåll (sammanfattning av tidslinjen, berikning, dedup med LLM) ska gå genom samma
  klient och samma spärr; inget eget providerval.
- **Inga ej godkända underbiträden.** TypeSafe-incidenten (DPIA R7, `dpia_supportagenten.md:333-376`):
  kundmejl gick till en leverantör som inte stod i underbiträdeslistan. Varje ny mottagare av
  supportinnehåll kräver att `lib/bolag.ts`-listan och PUB:en ändras först (`:362-364`).
- **Tenantisolering.** RLS + explicit filter (§ 1). Master-nyckeln kan inte läsa kunddata
  (`deps.py:67-71`).
- **Kundskriven text är opålitlig.** `customer_memory` och meddelanden injiceras bara inkapslade i
  användarposition (`052:19-21`, INV-SEC-009 `ARCHITECTURE_INVARIANTS.md:259-273`). En CRM-funktion
  som matar in tidslinjen i en prompt ska kapsla den på samma sätt (`kapsla_kundtext`,
  `support_agent.py:1228`).
- **Gallring** är radering utan soft delete (`048:23-27`), 24 månader enligt policyn
  (`119:5-11`), men bara för tenants med en rad i `ss_gallringspolicy`.
- **Utvecklingsmiljön är en spegel** med riktiga ärenden; inga skärmdumpar eller länkar ut
  (CLAUDE.md, DPIA R9 `dpia_supportagenten.md:424`).
- **Webbplatsbedömningen** (webbrevision m.m.) är hemlig utanför plattformsadmin, Umeå Webdesign
  och Alunix (CLAUDE.md). Den hör inte till supporten men kommer att ligga på samma
  bolagspost i CRM:et; varje CRM-svar som bär bolaget måste grinda de fälten.

### 6.2 Vad det betyder för CRM:et [förslag]
1. **I gränssnittet (tenantens egna användare):** fulla ärenden och meddelanden får visas för
   tenantens egna inloggade användare, samma krets som redan ser Ärenden och Chattar. Visa
   `author`/`direction` så att agentens, medarbetarens och kundens repliker skiljs åt.
   `sentiment`, `ss_classifications.reasoning` och överlämningsorsak är modellens tolkningar:
   märk dem som sådana och lägg dem inte i personens "fakta".
2. **I API:t ut (tvåvägs):** standardnyttolasten för ett ärende ska vara **metadata** — `id`,
   `customer_id`/person-id, `channel`, `category`, `status`, `priority`, `subject`,
   `created_at`/`updated_at`, antal meddelanden, senaste aktivitet. Meddelandetext, bilagor,
   utkast och `customer_memory` bara bakom ett uttryckligt scope på API-nyckeln, och bara om
   PUB:en med tenanten tillåter att Snajp lämnar ut innehållet till tenantens system
   [Antons/juristens att avgöra]. Tenanten är personuppgiftsansvarig; att skicka tillbaka hennes
   egna data till hennes eget system är inte en ny mottagare, men ett tredje system hon pekar ut
   (Buddys CRM-leverantör) är det i praktiken.
3. **Webhooks ut:** finns inte i dag (§ 0.4). Bygg dem som "händelse + id" (t.ex.
   `ticket.created {id, person_id, bolag_id, channel, category, status}`) och låt mottagaren hämta
   innehåll via API med sin nyckel. Då når innehållet bara den som har rätt scope, och en
   felkonfigurerad webhook-URL läcker inte kundmejl. Signera nyttolasten och logga varje utskick
   (motsvarande `audit_logs`).
4. **Aldrig ut:** sessionsadressen `@session.snajp.se`, `ss_channel_contacts.adress` (kan bära
   kanal-/konversationsreferenser), `ss_channel_connections.hemligheter_krypterat`,
   `ss_integrations.hemligheter_krypterat`, `is_test`-rader, och — i alla svar som också bär
   bolagsposten — webbrevisionens fält för kunder utanför de tre undantagen.
5. **Gallring följer med:** CRM:ets kopior/länkar ska raderas när källan raderas (FK med kaskad)
   och CRM-tabeller med personuppgifter ska in i `gallra_*`-mekanismen (`119`). En
   webhookmottagare utanför Snajp gallras inte av oss; det ska stå i dokumentationen till kunden.
6. **Tvåvägssynken** (`111`): om CRM-tabellerna ska speglas mellan development och main behöver
   de `synk_andrad_at` och triggrarna, annars försvinner de vid nästa synk eller återuppstår efter
   radering [antagande: CRM-data bör speglas som supportdatan].

---

## 7. Öppna frågor

1. Ska webbchattens besökare som senare uppger en riktig e-post i samtalet slås ihop med en
   CRM-person? I dag blir det två `ss_customers` och ingenting kopplar ihop dem.
2. Får API:t lämna ut meddelandetext till kundens externa CRM (Buddy), och under vilket PUB-villkor?
3. Ska domänmatchning få skapa CRM-personer automatiskt för bolag som redan finns i kundens synkade
   lista, eller alltid kräva en människa?
4. Ska `ss_tickets.status` och `ss_emails.status` (två parallella statusmodeller) presenteras som en
   status i CRM:et? Översikten räknar på mejlen, `weekly_analytics` på ärendena
   (`app/support_oversikt.py:8-11`).
5. Ska CRM-användare kunna skriva i supporten (byta status, svara) från bolagets sida, eller bara
   läsa och länka vidare till Ärenden/Chattar? Statusen kan bara gå framåt (`base.py:2471-2478`).
