# Handoff 2026-08-20 — Railway-development är klar så när som på tre kommandon

Allt nedan är **uppmätt**. Där något är obekräftat står det utskrivet.

Sessionen kördes i molnet, utan tillgång till din maskin. Det som gick att göra
härifrån är gjort; resten är packat i **ett** kommando som du kör ikväll.

---

## 1. Ikväll: ett kommando

```bash
cd snipe-leads
git pull origin development
python scripts/railway_gor_klart.py            # visar planen, ändrar ingenting
python scripts/railway_gor_klart.py --apply    # gör det
```

Det gör, i den här ordningen och idempotent:

| Steg | Vad | Kräver databasen |
|---|---|---|
| 1 | `.env.deploy` läses tillbaka ur Railway | nej |
| 2 | DeepSeek-nyckeln lagas → dev går från `simulation` till `live` | nej *(redan gjort)* |
| 3 | Migration **039 + 040** körs mot development | **ja** |
| 4 | Adminraden i `railway-main`, sedan i `railway-development` | **ja** |
| 5 | `verify_railway.py` — hela driftkontrollen | **ja** |
| 6 | Riktigt prov: laddar in ett exempelbolag i dev-deployen | nej |

Ordningen är inte godtycklig. `.env.deploy` först, annars **genererar**
`railway_provision.py` nya hemligheter i stället för att läsa dem — alltså
roterar Postgres-lösenordet under en levande stack. `railway-main` före
`railway-development` när adminraden skapas, eftersom `railway_seed_dev.py`
kopierar `platform_admins` main → development och en rad som bara finns i dev
försvinner vid nästa spegling.

Skriptet **mäter** i förväg om databasen går att nå och hoppar över de stegen
med besked i stället för att låta tre kommandon tajma ut på 20 sekunder var.
Från din maskin ska den raden säga `databasvägen: ÖPPEN`.

**Efter körningen:** logga in på <https://web-development-6c85.up.railway.app>,
gå till Leads → Discovery, kryssa i exempelbolag och tryck *Starta körning*.

---

## 2. Vad som redan är klart

### Koden är pushad och deployad

`development`, `railway-development` och `claude/railway-deployment-setup-waprtj`
står på samma commit. Railways egen liggare visar `SUCCESS` för **både** api och
web i development, byggda från `railway-development`. Jag såg fyra pushar byggas
och gå live under sessionen, den snabbaste på under en minut.

Handoffen från 19 augusti påstod att Railway inte deployade grenen. **Det
stämmer inte längre** — hypoteserna (kvot, deployment-trigger) föll båda.
`main` är orörd på `0329452` från 16 augusti, enligt projektreglerna.

### Driftkontrollen: 33 gröna, 2 röda

`verify_railway.py` grönt i båda miljöerna på: tjänsterna finns, rätt gren på
deployment-triggern, senaste deploy `SUCCESS`, byggkontexten är repo-roten,
`dockerfilePath` rätt, `/health/ready` svarar, api kör mot Postgres och inte
minnet, web når databasen, `/dashboard` kräver session — och korskopplingen:
**mains demo-nyckel avvisas med 401 av dev-api och tvärtom**.

Rött: `databasen går att nå`, båda miljöerna. Se §4.

### `.env.deploy` går att återskapa ur Railway

Nytt: `scripts/railway_env_bootstrap.py`. En account-token räcker — 21 värden
läses tillbaka (PG-lösenord, proxyns host/port, `snajp_app`- och
`snajp_web`-lösenorden ur tjänsternas `DATABASE_URL`, master- och demo-nycklarna,
`AUTH_SECRET`, båda URL:erna). Riktningen är envägs: ingenting härifrån ändrar
något i Railway.

Din maskin har redan filen. Skriptet finns för nästa maskin — och för att
`railway_provision.py --apply` från en maskin UTAN filen är tyst destruktivt.

### DeepSeek-nyckeln är inte förlorad

Värdet i Railway är 39 tecken med icke-ASCII på position 0 och 2, i **båda**
miljöerna. Tas skräpet före `sk-` bort återstår 35 tecken av rätt form, och
**DeepSeek svarar 200 på den** (uppmätt mot `GET /models`).

`scripts/railway_repair_llm_key.py` prövar kandidaten mot leverantören INNAN
den skriver, och skiljer ett 401 (svar: nyckeln duger inte) från ett avbrutet
TLS-handslag (inget svar alls). `--env` tar en miljö åt gången med flit.

**Uppdatering samma dag, 10:40 — development är redan lagad.** Kommandot kördes
skarpt: nyckeln skrevs, api deployades om, och `/health/ready` gick från
`simulation` till **`live`**. Kvarvarande varningar är bara IMAP och sändvägen.
Steg 2 säger därför "nyckeln är hel, ingenting att laga" när du kör ikväll.

**`main` lämnas åt dig** — samma korrupta värde står där, kandidaten är prövad
och godkänd av DeepSeek (status 200), men `main` rörs först när dev är verifierad:

```bash
python scripts/railway_repair_llm_key.py --env main --apply
```

---

## 3. Exempelbolagen — vägen in, och de nya testerna

### Vad som händer när du trycker på knappen

```
LeadsRunForm                    (components/leads/LeadsRunForm.tsx)
  → /api/snajp-support/leads/prospects/exempel      (Next-proxyn, tenant ur sessionen)
    → POST /api/leads/prospects/exempel             (FastAPI)
      → bygg_exempelbolag(icp, antal)               (deterministiskt, ingen LLM)
        → create_prospect(..., origin="example")    (migration 039)
  → /api/snajp-support/leads/runs/batch             (körningen startar)
```

Två egenskaper är hela poängen, och båda har nu tester:

**Vägen IN kräver ingen LLM-nyckel.** Körningen den leder till gör det
(`_require_live_llm` → 503 i simuleringsläge). En demonstrationsfunktion som
bara fungerar när allt annat redan fungerar demonstrerar ingenting.

**Bolagen kan aldrig mejlas.** `origin='example'` läses av
`scheduler._kor_send_guard` som spärr noll, före `provider.send()` — samma
ställe som de sex spärrarna, inte i UI:t. Ett påhittat bolagsnamn kan råka vara
ett riktigt bolag; då är mejlet inte ofarligt, det är fel mottagare.

### 22 nya tester

| Fil | Antal | Vad den vaktar |
|---|---|---|
| `snajp-support/tests/leads/test_exempelbolag.py` | 9 | Generatorn: ICP:t styr bransch/ort/roll/storlek, samma ICP ger samma lista, tomt ICP faller tillbaka på svenska SMB-branscher, `antal=0` ger tom lista |
| `snajp-support/tests/api/test_exempelbolag_api.py` | 5 | `origin='example'` sätts, vägen in fungerar utan nyckel MEDAN körningen ger 503, överskrivningarna styr bolagen, taket 1–10, **och att testkörningen startar på de inladdade bolagen** |
| `snajp-support/tests/db/test_prospect_origin_fallback.py` | 3 | Utan kolumnen: vanliga prospekt skapas ändå, exempelbolag VÄGRAS med ett fel som namnger migration 039 |
| `snajp-support/tests/leads/test_scheduler.py` (tillägg) | 2 | Spärr noll blockerar exempelbolaget — och släpper igenom ett riktigt prospekt på samma tråd |
| `tests/test_leads_ui_endpoints.py` | 3 | Varje sökväg `LeadsRunForm` anropar finns i backendens OpenAPI-schema |

Det sista testet finns för att sökvägarna är strängar i båda ändar, utan typ
och utan import — döps en route om svarar knappen 404 och felet syns först när
någon klickar.

### Så kör du dem

```bash
python3.12 -m venv .venv && . .venv/bin/activate     # 3.12 KRÄVS, se nedan
pip install -r snajp-support/requirements.txt -r scripts/requirements-scripts.txt pytest
cd snajp-support && python -m pytest -q               # 637 passed, 4 skipped
cd .. && python -m pytest tests -q                    # 219 passed, 25 skipped
```

**Python 3.12 krävs** för backendsviten: `scrapegraph-py>=2.1.0` finns inte för
3.11, och på 3.11 faller fem tester på `ModuleNotFoundError`. På 3.12 är sviten
grön rakt igenom — det var första gången den kördes komplett i den här
sessionen.

---

## 4. Vad som INTE gick härifrån, och varför

**Bara port 443 går ut ur molnsessionen.** Uppmätt: `github.com:22` och en hög
port mot en publik ekotjänst tajmar ut, 443 mot samma värd svarar direkt.
Railways Postgres nås utifrån via en TCP-proxy på en hög port — alltså går
`railway_migrate.py`, `admin_cleanup.py` och `railway_seed_dev.py` inte att
köra därifrån, oavsett token.

Jag försökte gå in i containern med `railway ssh` i stället (token räckte), men
att generera en SSH-nyckel nekades av sessionens behörighetsspärr. Samma spärr
stoppade `--apply` på nyckelreparationen. Båda spåren lämnades där i stället för
att kringgås.

### Följden, mätt genom API:t

`GET /api/leads/prospects` mot dev svarar 200, och raden **saknar fältet
`origin`** — migration 039 är alltså inte körd. Fälten från `031` (`orgnr`,
`ort`, `postnr`, `sni`, `website`, `anstallda`, `omsattning`, `foretagsnyckel`)
finns allihop, så kedjan står stilla just före 039.

Provet är läsande med flit: `POST /api/leads/prospects/exempel` hade svarat på
samma fråga men skapat rader i en spegel av produktionen.

### Och `/admin`

Fortfarande 404. Koden är rätt och deployad — det som saknas är raden i
`public.platform_admins`, som skapas av `admin_cleanup.py` och inte av
migrationskedjan. `isPlatformAdmin()` är fail-closed med flit, så symptomet är
en 404 för rätt person och en inloggning som ser ut att gå till fel ställe.

Steg 4 i kommandot i §1 löser det. Kontrollera efteråt att sista raden i
`--diagnos` säger:

```
    isPlatformAdmin() som appen . True
```

Den frågan ställs som `snajp_web` med `app.user_id` satt, alltså med RLS
påslagen. Som `postgres` (BYPASSRLS) ser den rätt ut även när den inte är det.

---

## 5. Rotera Railway-token

Token klistrades in i chatten och ligger därför i klartext i transkriptet.
Rotera den när du är klar: Railway → Account Settings → Tokens. Den nya sätts
utan att synas i terminalen:

```bash
python scripts/set_railway_token.py
```

---

## 6. Öppna trådar som inte hör till det här arbetet

- **Utgående mail saknas i hela kodlinjen.** Magic link och
  lösenordsåterställning svarar ärligt att de inte är kopplade.
- **OAuth-nycklarna är inte satta** (`AUTH_GOOGLE_ID`,
  `AUTH_MICROSOFT_ENTRA_ID_ID`). Providrarna registreras bara när de finns.
- **IMAP saknas** — inga inkommande mail hämtas i någon Railway-miljö.
- **`main`-miljön** har samma korrupta LLM-nyckel och sannolikt samma saknade
  adminrad. Rör den först när development är verifierad.
- **Preview-routerna** (`/dashboard/companies`, `/contacts`, `/inbox`,
  `/analytics`, `/assistant`) går inte att nå som kund — `AppShell`s
  stranded-effekt skickar tillbaka till `/dashboard` medan `lib/routes.ts`
  påstår att de nås direkt. Motsägelsen är äldre än det här arbetet.

---

## 7. Filer som tillkom eller ändrades i den här sessionen

| Fil | Vad |
|---|---|
| `scripts/railway_gor_klart.py` | Kvällens kommando — alla steg, i ordning, idempotent |
| `scripts/railway_env_bootstrap.py` | `.env.deploy` ur Railway med en token |
| `scripts/railway_repair_llm_key.py` | Lagar LLM-nyckeln, verifierad mot leverantören först |
| `scripts/verify_railway.py` | En onåbar databas tar inte längre med sig hela körningen; hemligheter scrubbas ur felmeddelanden |
| `snajp-support/tests/leads/test_exempelbolag.py` | Ny |
| `snajp-support/tests/api/test_exempelbolag_api.py` | Ny |
| `snajp-support/tests/db/test_prospect_origin_fallback.py` | Ny |
| `snajp-support/tests/leads/test_scheduler.py` | Två tester för spärr noll |
| `tests/test_leads_ui_endpoints.py` | Ny — UI:ts sökvägar mot backendens schema |
| `RAILWAY.md` | Bootstrap, nyckelreparationen, portbegränsningen |
| `MIGRATIONS-PENDING.md` | 039 uppmätt som inte körd, och hur det mättes |
| `handoffs/2026-08-19-adminytan-och-railway/HANDOFF.md` | §4 rättad — deployen HAR gått |
