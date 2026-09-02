# Handoff — testlager, inkorg och Redis, till Sebbe

2026-08-31. Grok. Bygger på [HANDOFF-2026-08-30-LEADS-KORNING.md](HANDOFF-2026-08-30-LEADS-KORNING.md)
och [HANDOFF-2026-08-30-KB-WRAP.md](HANDOFF-2026-08-30-KB-WRAP.md).

Antons skärmbilder: exempelbolag med färdiga pitchar, flytta röd på `.example`,
inkorg som först såg statisk ut, nästan allt eskalerat, testchattens
kunskapsartikel som lät som uppladdad affärskontext.

**Pushat.** Resten av de öppna punkterna (testmail-lager, flytta-ifyllnad,
byt kund, konvertera) står i
[HANDOFF-2026-08-31-TESTISOLERING.md](HANDOFF-2026-08-31-TESTISOLERING.md).

## Produktmodellen (tre lager)

1. **`/demo`** — enda ytan med färdigskrivna exempelbolag. Ingen LLM.
2. **Test** — samma motor som skarpt, märkt `is_test` / `origin='test'`.
3. **Skarpt** — det som ska följas upp mot riktiga prospekt och slutkunder.

Admin som öppnar en kund (`kund:<slug>`) tvingar `is_test=true` på JSON-kropp
och query i `proxyAsTenant`. Bannern säger det rakt ut.

## Vad som landade i koden

### Exempelkörningar borta utanför demon

- `LeadsRunForm` har ingen checkbox och skapar inga exempelbolag. Efter
  `POST /leads/runs/batch` pollas varje jobb mot `/leads/jobb/{id}`
  (inloggad proxy — inte den anonyma `/jobs/{id}`).
- `POST /leads/prospects/exempel` svarar **403** om tenanten inte är Nordlys
  (`DEFAULT_TENANT_ID`). GET-listan döljer `origin='example'` samma väg.
- Batch hoppar över exempelbolag utanför demon.
- Städskript: `python scripts/rensa_exempelbolag.py` (torrkörning) /
  `--apply` mot `DATABASE_URL`. **Inte kört mot development ännu.**

### Inkorg

- Medan testmail klassas: badge **Bearbetas** / "Agenten läser…", inte `Ny` +
  tom beslutslogg som ser färdig ut.
- `build_mock_emails(..., kb=...)` bygger frågor ur tenantens kunskapsartiklar
  plus ett eskalerande ärende (pengar/GDPR/ilska). Snajp Admin ska alltså få
  frågor om leads och testchatt, inte "var är mitt paket?".
- Tom KB: varningen visas i ochre **före** listan.

### Testchatt

- Kortet heter "Agenten behöver undersöka det här innan den svarar".
  Primärknapp: **Öppna som ärende** → `POST /api/agent/forslag/{id}/arende`
  (skapar ärende "Undersökning: …", ingen KB-skrivning).
  Sekundärt: spara som kunskapsartikel. "Tillagt i kunskapsbasen. Nästa
  meddelande använder den nya texten…" är borta.
- Feedback: `POST /api/agent/feedback` ger **403** om körningen inte är
  `is_test`. Godkända rättningar wrappas in i testchattens case_context
  (user-position, `tenant:test-feedback`). Notis: "Feedbacken är kalibrerad in".
- KB-steg-prompten: "kontakta oss igen", aldrig "kontakta supporten".

### Inställningar

Menyn i `lib/routes.ts`: **Underlag** (kunskapsbas först, sedan "Vad ni säljer",
"Så ska agenten låta"), **Så får agenten göra**, sedan personligt och konto.
URL:er oförändrade.

### Redis (enhetstester)

`test_inv_redis_001` och `test_arbetsminne`: 16 gröna. Live (TLS, shadow-träff
i Händelser, återtag vid deploy) **inte kört den här sessionen**.

## Verifiera live

Konto: `snajpsupport@gmail.com` (lösen i `scripts/qa_vyer.mjs`).
URL: `https://web-development-6c85.up.railway.app`

1. `/admin/leads` → Starta körning: inga Ekberg/Västrnäs-kort. Status pågår,
   sedan registret under.
2. `/admin/support` → Hämta testmail: först Bearbetas. Ämnesrader ur Snajps KB,
   inte bara order/garanti. Inte 7/8 rött om underlaget täcker frågan.
3. Testchatt: undersökningskort + tumme ned ger kalibreringsnotis. Widget
   `/chat/...` har inga tummar.
4. Admin → Kunder → Öppna en riktig kund → testchatt. Logga in som kunden:
   adminens körning ska inte synas (is_test på chatten). **Mock-inkorg har
   ännu inget is_test-fält** — se öppet nedan.

## Öppet för dig

- **`lib/skatteverket/oauth.ts` tomt `.json()`** (INV-API-001) — oförändrat,
  din yta sedan KB-WRAP.
- **Railway auto-deploytrigger** för `development` fyrade inte 29/8 22:42Z.
  Manuell deploy-kommandot står i LEADS-KORNING-handoffen.
- **Flytta över** på ofullständiga *researchade* testbolag: fortfarande
  422 med fältlista, inget ifyllnadsformulär. Exempelbolagen som fällde den
  (ogiltigt org.nr / `.example`) ska inte längre skapas.
- **Mock-mail i Kundtjänst** är fortfarande samma lista som skarpa ärenden.
  `provider='mock'` finns; de filtreras inte till en Testkörningar-flik än.
  Demo-/testkonton ska visa dem under Ärenden (planens lager 2).
- **Byt kund** är fortfarande "Öppna" på Kunder-raden, plus bannern. Ingen
  sökbar växel i headern.
- **Konvertera testkund → riktig** (`scripts/konvertera_testkund.py`) har
  ingen knapp i UI.
- **Redis live:** `python scripts/redis_kontroll.py` (TLS/EU) och
  `SEMANTIC_CACHE=shadow` träffkvot i Händelser. R5/R6 spärrade.
- **rensa_exempelbolag.py --apply** mot development när du är redo.

## Commits (lokala, ej pushade)

- `9993125` exempelbolag bara i demon, polla leads-jobb
- `f3f632c` testmail mot profilens KB, Bearbetas
- `917ad32` undersökningsärende, kalibrering, impersonation-is_test, inställningscopy

Claudes `ee9b989` (session 30/8) ligger också före origin.
