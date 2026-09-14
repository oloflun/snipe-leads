# Handoff — testisolering, flytta och kundväxel, till Sebbe

2026-08-31 kväll. Grok. Bygger på
[HANDOFF-2026-08-31-TESTLAGER-OCH-UI.md](HANDOFF-2026-08-31-TESTLAGER-OCH-UI.md).

Första leveransen (exempelbolag, Bearbetas, undersökningsärende, impersonation,
inställningscopy) ligger redan på `origin/development`. Den här omgången tar
de öppna punkterna: testmail i eget lager, ifyllnad vid flytta, byt kund,
konvertera testkund, migration 057, Redis-mätning.

## Vad som landade

### Testmail skilda från skarpa ärenden

- Migration `057_email_ticket_is_test.sql` — `ss_emails.is_test` och
  `ss_tickets.is_test`. Backfill: `provider='mock'`. **Körd mot development.**
- `GET /inbox` default: skarpa för riktiga kunder. Demo (Nordlys), publik demo
  och `testkund-*` visar testmail under Ärenden.
- Riktiga kunder får fliken **Testmail** i Kundtjänst. **Hämta testmail**
  ligger där, inte bland skarpa ärenden. **Flytta till ärenden** sätter
  `is_test=false` på mailet och det länkade ärendet.
- Admin som tittar som kund: **skrivningar** tvingas `is_test` (POST/PUT/PATCH).
  GET visar kundens riktiga inkorg — annars hade admin trott att profilen var
  tom.

### Flytta över med ifyllnad

`POST /leads/prospects/{id}/befordra` tar nu orgnr, webbplats och e-post i
kroppen, skriver dem, sedan samma validering som förut. 422 visar ett
ifyllnadsformulär i Bolagsregistret. PATCH på samma tre fält fungerar också.

### Byt kund

Sökbar växel i adminheadern och i AppShell (synlig för plattformsadmin). Samma
`bytVy`-action som "Öppna" på Kunder-raden.

### Testkund → riktigt konto

På `/admin/kunder/{id}` för slug `testkund-*`: torrkörning, sedan skriv över.
Kopierar kunskapsbas, regler, agentinställningar och röstdokument. Ärenden och
mail följer inte med. CLI:t `scripts/konvertera_testkund.py` finns kvar.

### Redis (mätt, inte ändrat)

- Region: GCP `europe-west1` (EU).
- `SEMANTIC_CACHE=shadow` på development/api.
- TLS **av**, REDIS_URL är `redis://` inte `rediss://`. Jobbposter går i
  klartext. Påslaget är `python scripts/redis_tls_pa.py --apply` — det byter
  både Redis Cloud och Railway-URL:en i ett svep. Inte kört: det är en
  skrivning mot delad infra.

### Data

21 exempelbolag raderade från Snajp-tenanten (`scripts/rensa_exempelbolag.py
--env development --apply`). Nordlys och publik demo rördes inte.

## Verifiera live

Konto: `snajpsupport@gmail.com` (lösen i `scripts/qa_vyer.mjs`).
URL: `https://web-development-6c85.up.railway.app`

Auto-deploytriggern för `development` fyrade inte 29/8 22:42Z. Manuell deploy
efter den här pushen:

```
python -c "import sys;sys.path.insert(0,'scripts');from railway_provision import deploy;EID='02c39616-1b8e-47b7-beea-d8c6cfba1acd';print(deploy('5828c279-ad8f-429b-b5e1-969372db8a0a',EID));print(deploy('0261f633-1247-4d92-b5ab-40c2a1828b90',EID))"
```

1. `/admin/support` som Snajp: Kundtjänst utan mock-ordermail. Testmail-flik.
   Hämta testmail → Bearbetas → frågor ur Snajps KB. Flytta till ärenden.
2. Öppna en riktig kund via **Byt kund**. Bannern: "Allt du kör här är test".
   Testchatt ska inte synas när kunden loggar in själv.
3. Bolagsregister: markera ett ofullständigt testbolag → Flytta över → fyll i
   org.nr / webb / e-post → Spara och flytta.
4. En `testkund-*` under Kunder: "Flytta till riktigt konto". Torrkör först.

## Fortfarande öppet

- `lib/skatteverket/oauth.ts` tomt `.json()` (INV-API-001) — oförändrat.
- Redis TLS av. Kommandot ovan.
- Railway auto-deploytrigger död.
- Browser-QA som `snajpsupport@gmail.com` mot den här omgångens deploy är
  inte kört i den här sessionen — koden och API-testerna är gröna.

## Tester

`test_inbox_is_test`, `test_konvertera_api`, befordra-ifyllnad,
`test_inv_store_001`, Redis-enhetstester, inställningsmenyn: gröna.
