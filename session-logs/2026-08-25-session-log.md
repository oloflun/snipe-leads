# Session Log — 2026-08-25

## Session Summary
Lagade publika `/bokforing`, som renderade Snajp Support-agenten (etiketten
"Snajp Support", demovarumärket "Nordlys Handel", supportens förslagsfrågor) i
stället för bokföringen. Rotorsaken var att `LandingPhoto.tsx`:s demoslot bara
hade två grenar (`leads ? … : supportDemo`). Kompletterade dessutom
bokföringschatten med en egen versionerad kunskapsbas + fjärde vitlistat
verktyg, och en dubblettspärr på uppladdningen. Verifierat lokalt och live på
Railway (dev), commit `db42924`, rebasead och pushad till `development` +
`railway-development`.

Viktig kontext: uppdragsprompten antog att bokföringsagenten skulle byggas
från noll — den fanns redan komplett sedan 2026-08-23/24. Arbetet blev därför
en riktad fix + kompletteringar, inte en nybyggnation.

## What Changed

### Files Created
- `snajp-support/app/bookkeeping/kunskap.py` — 15 svenska ämnen (momssatser,
  momsdeklaration, periodisering, representation, resor/traktamente,
  milersättning, hemmakontor, telefon/bil, fakturakrav, bankavstämning,
  bokföringslagen/arkivering, omvänd byggmoms, EU-handel/VAT, import, K1–K3,
  avdragsrätt) som DATA + `sok_amne()` med tvåpass-matchning (exakt ord/fras
  före prefix; längsta prefix vinner så "momsdeklarationen" inte fastnar på
  "moms")
- `snajp-support/tests/bookkeeping/test_kunskap.py` — uppslag, ordgränser,
  INV-BOOK-003-samspel (tal ur uppslagen text räknas som hämtade)

### Files Modified
- `components/marketing/LandingPhoto.tsx` — tredje demoslot `bookkeepingDemo`,
  paneletikett per produkt ("Snajp Bokföring")
- `components/marketing/ProductPage.tsx` — skickar `<BokforingDemo />` (samma
  komponent som /demo/bokforing; ingen duplicering)
- `snajp-support/app/agent/bookkeeping_chat_tools.py` — verktyget
  `sla_upp_kunskap` (dataset 4), sparar i `ctx.resultat` för beloppsgrinden
- `snajp-support/app/agent/bookkeeping_agent.py` — `CHATT_SYSTEMPROMPT` listar
  verktyget ("svara ur texten, inte ur minnet")
- `snajp-support/app/api/bookkeeping.py` — dubblettspärr i `ta_emot_underlag`:
  sha256-träff hos tenanten → 422 FÖRE textutvinning/LLM
- `snajp-support/app/storage/{base,memory,postgres}.py` —
  `get_bk_underlag_by_sha256` i protokoll + båda lagringarna (INV-STORE-001)
- `snajp-support/tests/api/test_bookkeeping_api.py` — dubblettsektion
  (422 + per-tenant-isolering på lagringsnivå)

## Decisions Made
- **Ingen anonym live-agent på publika sidan.** Repot hade redan avgjort det:
  INV-SEC-008 (publik yta får inte skriva), BokforingDemos docstring (LLM per
  anonym besökare = kostnad utan mervärde), invite-only (anonym besökare har
  ingen tenant). Publika sidan visar demon; den levande vyn är
  /dashboard/bokforing.
- **Ingen `SNAJP_BOKFORING_URL`.** Backend är EN tjänst; `SNAJP_SUPPORT_URL`
  är tjänstens namn, inte supportagentens. Ingen ny env-variabel, ingen
  migration.
- **Ingen Supabase Storage.** Filer sparas aldrig (dataskyddsbeslut,
  personnummer på kvitton) — befintlig multipart-proxy behölls.
- **Dubblett = 422-avvisning, inte flaggad rad.** Byteidentisk fil är nästan
  alltid en dubbelklick; exakt sha256-match har ~noll falsklarm (skälet
  verifieringsgrinden avvisade dubblettdetektering gäller periodgrinden, inte
  uppladdningsögonblicket). Sparas hashen är det för just den här frågan —
  står ordagrant i storage/base.py.
- **Årsvolatila belopp i kunskapstexterna** (traktamente, milersättning)
  hänvisar till Skatteverket i stället för siffra; stabila lagfästa tal
  (300 kr-taket, 7 års arkivering) står ut.

## Verification
- Backend-pytest: 1302 → (efter rebase) 1333 passerade. Rotens vaktposter:
  317 → 322. `tsc --noEmit` rent. Allt omkört EFTER rebasen mot uppströms
  (agentinstruktioner, logo-refresh, CI-spegling) innan push.
- Live på Railway dev: /bokforing visar bokföringsdemon (rätt paneler
  synliga/dolda), demochatten svarar vid klick, inga konsolfel, /support
  intakt.

## Open Threads
- Parallell session committade `fa67c29` ("agenterna löser i stället för att
  ge upp") ovanpå mitt under sessionen; `scripts/railway_tenantnyckel.py`
  ligger otrackad i arbetsytan och tillhör den — INTE upplockad.
- Kvarstår från tidigare: Gemini-kvoten blockerar kvalitetskontrollen av ett
  riktigt LLM-svar i bokföringschatten (kedjan testad fram till leverantören).
- `FORBEHALL`-texten i chatten är fortfarande inte människogodkänd (markerad
  så i koden sedan tidigare).
