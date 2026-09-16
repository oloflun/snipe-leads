# Kvittohanteraren — ombyggnaden av bokföringsagenten (2026-09-16)

Bokföringsagenten är ombyggd till **Kvittohanteraren**: en agent som läser
kundens inkorg (Gmail/Outlook/Hotmail, read-only), identifierar kvitton och
utlägg, extraherar belopp/moms/datum/butik/kategori, stoppar dubbletter och
sammanställer perioden med en textsammanfattning. Inget är pushat och inget
är deployat — allt ligger i arbetsträdet, verifierat lokalt.

## Kör lokalt

```bash
# Terminal 1 — backend i minnesläge (mock-inkorg, deterministisk läsare)
snajp-support/.venv/Scripts/python.exe snajp-support/lokal_kvitton.py

# Terminal 2 — den isolerade arbetsytan (Kvittohanterarens sajt)
cd bokforing-webb && npm run dev        # http://localhost:3100

# Terminal 3 — huvudappen (öppna demon utan konto)
npm run dev                              # http://localhost:3005/demo/kvitton
```

Eller via förhandsvisningen: launch-konfigurationerna `kvitton-backend`,
`kvitton-portal-dev` och `web`.

Se särskilt: `/demo/kvitton` (öppna demon med animerad inkorg),
`http://localhost:3100/inkorgen` (skanningen på "riktigt" mot mock-inkorgen),
`/kvitton` (listan, godkännanden, export) och `/assistent` (chatten).

## Vad som byggdes

**Backend (`snajp-support`)**
- `app/kvitton/` — mejlkonton (`mejl.py`: mock + Gmail API + Microsoft Graph,
  alla read-only), kvittoidentifiering + deterministisk regexläsare
  (`tolkning.py`), skanningskedjan med två dubblettspärrar (`skanning.py`),
  kategorisummor + deterministisk sammanfattningstext + svarsmotor utan modell
  (`sammanfattning.py`).
- `app/api/kvitton.py` — `/api/kvitton/*`: mejlkonto, skanna, lista,
  sammanfattning, manuell uppladdning, godkänn (med grinden omkörd),
  CSV-export, rensa period, chat. SIE-exporten (Fortnox/Visma m.fl.) står
  kvar oförändrad på `/api/bookkeeping/period.sie` och matas av samma
  verifikat.
- `app/agent/kvitto_agent.py` + `kvitto_chat_tools.py` — kvitto-assistenten:
  samma INV-BOOK-003-grindning som bokföringschatten, 2 modellanrop per tur
  i stället för 5–7. `INTEGRITETSNOTIS` och nytt `FORBEHALL` ägs här.
- Lagring: `bk_underlag` fick kvittofälten (kalla, mejl_id, mejl_amne,
  mejl_avsandare, valuta, belopp_original) i **migration 063** — skriven, EJ
  körd mot Railway (ingen deploy). Memory- och Postgres-lagringen uppdaterade.
- `scripts/kvitto_oauth.py` — fångar OAuth-samtycket (gmail.readonly /
  Mail.Read) och skriver ut refresh-token för miljön. Samma "vi kopplar åt
  kunden"-mönster som IMAP-inkorgarna.
- Utan LLM-nyckel kör allt deterministiskt (simuleringsläge): regexläsaren
  för extraktion och svarsmotorn för chatten — varje siffra grundad per
  konstruktion.

**Huvudappen**
- Rename hela vägen: `/dashboard/kvitton`, `/demo/kvitton`, `/kvitton`
  (marknad), nav-etikett "Kvitton". Gamla adresserna redirectar. Interna
  produktnyckeln `bookkeeping` står kvar (databasens värde i
  `workspaces.products`), liksom agentsajt-sluggen `bokforing`
  (SSO-kontraktet och env-namnen) — dokumenterat i koden.
- `components/kvitton/` — `KvittoVy` (fliken), `KvittoYta` (skanning +
  uppspelning + tabell + uppladdning + godkänn), `KvittoChatt`,
  `KvittoSammanfattning`, `Integritetsnotis`, och **`KvittoDemo`** — den
  öppna demon där inkorgen rullar in och beloppen markeras i realtid
  (reduced motion hoppar till slutläget). `lib/demo/kvitton.ts` speglar
  backendens mock-inkorg — en berättelse, två ytor.
- Marknadscopy, USP, FAQ, priser (paketet heter "Snajp Kvitton") och
  villkoren omskrivna. Proxyn `/api/snajp-support/kvitton/*` tillagd
  (entitlement-grindad, binärsäker).

**Portalen (`bokforing-webb` — katalognamnet är infrastruktur och rörs inte)**
- Ny IA: Översikt / **Inkorgen** / Kvitton / Assistent. Gamla flikarna
  redirectar. Rebrandad till "Snajp Kvitton" rakt igenom.
- `InkorgVy` — huvudvyn: skanningen spelas upp mejl för mejl med
  beloppsmarkering; `KvittolistaVy` — tabell, uppladdning, godkännanden,
  CSV-export, rensning; `OversiktVy` — nyckeltal, kategorier,
  sammanfattningstext; `AssistentVy` — chatten. Ny proxy `/api/kv/*`.

## Integritetsnotisen — formuleringen är verifierad mot tekniken

Kravet i uppdraget om "allt sker lokalt" hade varit osant: extraktionen
använder en extern AI-modell i drift. Texten som visas (UI + API) lyder
därför: read-only-åtkomst, inget säljs/delas utöver AI-tjänsten som tolkar
kvittotexten (under PUB-avtal), mejlens innehåll sparas aldrig — bara
utlästa fält + kontrollsumma. Det stämmer med koden: skanningen skriver
fälten och ett sha256-fingeravtryck, aldrig mejltexten.

## Testresan (utförd 2026-09-16, lokalt)

Miljö: backend i minnesläge med mock-inkorg (13 påhittade mejl: 10 kvitton,
1 omskickad kopia, 2 icke-kvitton) och deterministisk läsare.

| Steg | Utfall |
|---|---|
| Skanna inkorgen (portal + API) | ✅ 13 mejl genomlästa, 11 kvitton, nyhetsbrev/mötesmejl lämnade. Uppspelningen med beloppsmarkering fungerar. |
| Extraktion | ✅ 8 kvitton kompletta (7 817,50 kr, ingående moms 1 194,60 kr — verifierat mot handräkning i test). |
| Dublettkontroll | ✅ Samma mejl igen: 0 nya, 11 hoppade. Omskickad kvittokopia: flaggad "möjlig dubblett", inget verifikat, räknas inte. |
| Flaggor | ✅ USD-kvitto (45.00 USD, räknas inte om), kvitto utan läsbart belopp — båda i granskningskön med begriplig anmärkning. |
| Godkänn | ✅ Dubbletten godkänd rakt av; USD-kvittot godkänt med omräknat belopp (grinden körs om, verifikat byggs, summan uppdaterades 7 817,50 → 9 535,50 kr). |
| Manuell uppladdning | ✅ 3 egengenererade PDF-kvitton inlästa (belopp/moms/datum/betalstatus rätt); samma fil igen → 422 med dubblettbesked. |
| CSV-export | ✅ 200, korrekt Content-Disposition, BOM för Excel. |
| Resultat + textsammanfattning | ✅ Tabell och text bygger på samma summor; texten byggs av kod (kan inte glida mot tabellen). |
| Kvitto-assistenten, 3+ frågor | ✅ (simulerat läge) Resor → 1 034,00 kr med specifikation; granskningsfrågan → de tre flaggade med skäl; summafrågan → sammanfattningen. Alla tal grundade. |
| Öppna demon `/demo/kvitton` | ✅ Hela flödet utan backend, inga konsolfel, exempelmärkt. |
| Kvalitetsgrindar | ✅ 1957 backendtester, 501 root-tester (nya vakter för demosiffrorna + åtkomstgrinden), `tsc` rent i båda apparna. |

**Hittat och åtgärdat under testet:** tekniska `mock-004:`-prefix läckte i
kundanmärkningar (borttaget); redundanta brister för valutakvitton (filtrerade);
uppladdade filer saknade motpart (första-raden-heuristik tillagd) och
anmärkning (bristerna viks in); godkänn-flödet saknade kategorifråga (tillagd).

**Inte verifierat / följs upp:**
1. **Riktig LLM-extraktion och -chatt** — lokala Gemini-nyckeln är slut
   (kreditslut, snyggt hanterat med kundbesked, verifierat i förbifarten) och
   `gemini-2.5-flash` svarar dessutom 404 lokalt ("use gemini-3.6-flash").
   Kör om mot development/Vertex.
2. **"Ny kund"-registreringen och inloggat `/dashboard/kvitton`** — kräver
   lokal Postgres som faller på pgvector (känd sedan tidigare). Vyn delar
   verifierade komponenter; verifieras i development efter deploy.
3. **Riktig Gmail/Graph-koppling** — kopplingskoden är skriven men behöver
   en app-registrering (client id/secret) och ett samtycke via
   `scripts/kvitto_oauth.py`. Avtalsdelen (PUB-bilaga för mejlläsning enligt
   GDPR-planen) är Antons bord.
4. Migration 063 ska köras mot Railway development (torrkörning först) vid
   deploy. `agent_runs.agent_type` återanvänder "bookkeeping" — ingen
   migrationsändring behövs där.

## Slutgranskningen före release (2026-09-16, kväll)

En oberoende kodgranskning av backend plus Iris-sessionens genomgång av
portalen hittade fel som är rättade och testade (29 kvittotester, 1975
backend, 501 rot, `tsc` + produktionsbyggen gröna i båda apparna):

- **Mejlkontot var per deployment, inte per kund.** Varje tenant hade kunnat
  skanna samma Gmail-inkorg. Nu krävs `KVITTO_MEJL_TENANT` för riktiga
  leverantörer (annars ingen koppling). Mocken nekas i miljöer med riktig
  kunddata om den inte pekats ut till en tenant.
- **Utländsk valuta räknades som kronor** i modellvägen och i flera format
  (`45,00 €`, `EUR 45.00`, valuta på egen rad). `valutaspärr` körs nu i båda
  läsvägarna.
- **Beloppsläsaren valde fel total** ("Subtotal" matchade "total", "Summa 3
  artiklar" blev 3 kr, "1,245.00" blev 1,245). Omskriven med etikettrang.
- **Godkännandet satte betalstatus till "betald"** av sig självt. Nu gissas
  den aldrig; gränssnittet frågar. Godkända kvitton kan inte rättas förbi
  sitt verifikat (409), floatbelopp tas emot, okänd kategori/momssats ger
  422, ogiltigt id ger 404.
- **Intäkter räknades som utlägg** och summorna kapades vid 200 rader.
- **Okänd kategori från modellen** gav en "klar" rad utan verifikat och 500.
- **"Resor" och "Resor & logi" överlappade** — etiketterna heter nu "Resor &
  transport" och "Logi", och en fråga om resor täcker båda.
- Gmail-datum läses ur `internalDate`, Outlook läser bara inkorgen med
  oföränderliga id:n, CSV:n har separata kolumner för SEK- och originalbelopp.
- **Integritetstexten** sa att mejlens innehåll inte sparas, men avsändare och
  ämnesrad lagras. Texten säger nu exakt det, på alla ställen.

Kvar som känd begränsning: backend kontrollerar inte produkträttighet på
`/api/kvitton/*` (samma som `/api/bookkeeping`; grinden sitter i webbens
proxy), och ett kvitto som både mejlas och laddas upp som fil räknas två
gånger (bara mejl mot mejl dedupliceras på innehåll).

## Release

Pausad på Sebbes beslut: ingen push till development förrän Anton mergat
PR #18. Därefter: migration 063 mot Railway development (torrkörd), push,
verifiera dev, ny release-PR till main med 063 för Anton.

## Öppna trådar (beads)

Se `bd ready` — uppföljningsärenden skapade för punkterna ovan.
