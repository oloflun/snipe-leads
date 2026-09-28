# Iris-körning: Snajp AB som egen intern kund — 2026-09-20

Första skarpa Iris-körningen där Snajp är sin egen leads-kund. Kontot är en
vanlig tenant utan specialfall i koden (`kund-7cea8ee9`, arbetsytan "Snajp AB",
skapad via samma väg som en riktig kund — se
[`scripts/skapa_snajp_intern_kund.py`](../scripts/skapa_snajp_intern_kund.py)).
Körningen är både en riktig prospektlista och ett levande produktionstest av
V2-kedjan i Railway `development`, precis som beställt.

## ICP-profilen

| Fält | Värde |
|---|---|
| Geografi | Sverige |
| Bransch | Utbildningsföretag inom hälsa & säkerhet: HLR, första hjälpen, brandskydd, heta arbeten, arbetsmiljö |
| Storlek | 10–250 anställda; mindre bolag bara vid hög kursvolym (kodad som signal, storleksspannet 1–250 för att inte hårdfiltrera bort dem) |
| Signaler | Bokningskalender/kursanmälan, FAQ om intyg/certifikat, flera kursorter/instruktörer, synlig kundtjänstkontakt |
| Kontaktroller | VD, utbildningsansvarig, kursadministratör, kundtjänstansvarig |
| Uteslut | Bolag som synligt kör Zendesk/Intercom/Freshdesk |

## Resultat

**Körning:** `POST /api/leads/runs/batch`, scope `research`, limit 10,
`is_test=false`. Startad 2026-09-20 ca 14:24, klar 14:26:45 (≈ 2,5 min).
Samtliga 11 jobb (1 batch + 10 research) `completed` i `leads_job_ledger`.

**10 bolag hittade, 6 kvalificerade (60 %), alla i rätt nisch:**

| Bolag | Ort | Kontakt | Roll | Kontaktnivå | ICP-fit |
|---|---|---|---|---|---|
| Rotestam HLR & Brand (Brandskyddsutbildning Sthlm) | Stockholm | Niclas Rotestam | Ägare | named_other | 1,00 |
| HLR Proffsen | Motala | — | — | role_address | 1,00 |
| HLR Konsulten | Solna | Christian Ceder | CEO | named_other | 0,90 |
| Praktisk HLR | — | André Kaldani | HLR-instruktör | named_other | 0,90 |
| HLR-Gruppen | Stockholm | — | — | role_address | 0,90 |
| Hsafety AB | Skellefteå | Mattias Hedlund | VD/Projektledare | named_other | 0,90 |

**Underkända, med Iris egna skäl (diskvalificeringarna fungerar):**

- **HLR.se** — inget källmaterial gick att hämta (sajt bakom spärr); rätt att fälla hellre än gissa.
- **Rädda Barnen** — ideell organisation, inte utbildningsföretag; saknar boknings- och intygssignalerna.
- **Sanandum AB** och **SEIE AB** — bemanningsföretag inom vård; bemanningsregeln fällde båda (deras annonser gäller kundernas behov, inte egna).

## Produktionsmått

| Mått | Värde |
|---|---|
| LLM-anrop (research) | 10 × `gemini-2.5-flash` via Vertex |
| Tokens | 118 642 in / 13 873 ut |
| Uppskattad kostnad | ≈ 1,3–1,5 kr totalt ⇒ **≈ 0,13–0,15 kr per lead** (under V2-målet 0,19) |
| Latens per research | 3–24 s (median ≈ 10 s) |
| Källor | 34 rader i `prospect_sources`, samtliga `company_website` med laglig grund loggad |
| Rollflaggning | 2 av 6 kvalificerade saknar belagd roll (`role_address`) — syns nu som `rollkoppling_oklar` i API:t |

## Noteringar för säljarbetet

- Alla sex kvalificerade är småbolag i exakt rätt vertikal — samma bransch som
  Livrustning, så referenscaset passar rakt av.
- Kontaktnivåerna är ärliga: fyra namngivna personer, två funktionsadresser.
  Inga gissade adresser.
- **Inget är skickat.** Utkast och utskick kräver GDPR-kedjan (policylänken i
  foten kom på plats samma dag) och att `policy_url` + bolagsuppgifter fylls i
  för Snajp-tenanten — och Snajps riktiga orgnr är fortfarande platshållare
  (P0.3b i `docs/JURIDIK_ATGARDER.md`), så send_guard blockerar tills Anton
  fyllt i det. Det är rätt ordning.

## Reproducera

```bash
python scripts/skapa_snajp_intern_kund.py --env development --apply   # idempotent
# nyckel: RAILWAY_DEVELOPMENT_KEY_KUND_7CEA8EE9 i .env.deploy
# starta: POST /api/leads/runs/batch {"scope":"research","limit":10,"is_test":false}
# läs:    GET /api/leads/prospects  ·  GET /api/jobs/<job_id>
```
