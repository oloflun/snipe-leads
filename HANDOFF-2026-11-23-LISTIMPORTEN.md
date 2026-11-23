# Handoff 2026-11-23: listimporten och fliken Listor (till Sebbe)

Antons beställning efter Henrik (Buddy): leads ur kundens egna data (gamla prospekt,
förlorade affärer, avtal som går ut). Skälen till varje val står i
[docs/BESLUT.md](docs/BESLUT.md), posten 2026-11-23 om listimporten.

## Vad som är byggt

- **Filläsaren** `lib/leads/importfil.ts`: CSV, TSV och text i UTF-8, UTF-16,
  Windows-1252 och Mac Roman; Excel (.xlsx) utan beroende; HTML-tabeller och Excel
  2003-XML. Gammal .xls avvisas med en anvisning.
- **Kolumnmatchningen** `lib/leads/importmallar.ts`: rubrikrad, fot och summarader,
  en aliaslista över leverantörer och språk, och innehållet som sista ord.
- **Värdena** `lib/leads/importvarden.ts` och **raderna** `lib/leads/importrader.ts`:
  org.nr, e-post, telefon, webbplats, datum, dubbletter inom filen.
- **Gränssnittet** `components/leads/ImportLista.tsx` (ersätter `ImportCsv.tsx`): fil,
  kolumner, granska, klart. Kvittot sparas på listan.
- **Backend** `snajp-support/app/api/leads_suite.py`: `POST /api/leads/import` tar
  satser (`list_id`), hoppar över befintliga kunder, leads och spärrade adresser.
  `POST /api/leads/import/granska` är förhandsgranskningen.
- **Migration 152**: `lead_list_items.avtalsslut`, `lead_list_items.extra`,
  `lead_lists.importinfo`. Körs av sig själv mot development vid pushen.
- **Fliken Listor** i Leads (`LeadsSida.tsx`, `LeadslistorView.tsx`) med vyerna Listor,
  Säljlista och Befintliga kunder. Adressen bär `?vy=listor&del=`.

## Verifierat

- `npm test`: 354 gröna. `npx tsc --noEmit`: grönt. Backendens `tests/leads`: 1 531 gröna.
- 48 syntetiska exportfiler i `lib/leads/fixtures/crm-export` mappas rätt, också i
  Windows-1252 och UTF-16. Riktiga kalkylblad ur XlsxWriter och LibreOffice ger samma rader.
- Sett i webbläsaren i `/demo/leads?vy=listor`, 1280 och 375 px, svenska: alla steg
  fram till Importera, som är avstängd i demon.

## Inte verifierat

- **Själva importen mot en riktig databas.** Postgres-koden i `storage/postgres.py` har
  bara gått mot minneslagret. Prova en import i development efter pushen.
- **Rubrikerna i fixturerna.** Bara Vismas är tagna ur leverantörens dokumentation.
  Henriks riktiga export är provet. Faller en fil igenom: lägg den som fixtur och
  lägg aliaset i `ALIAS` i `importmallar.ts`.
- Engelska versionen och listtabellen med avtalsslut är inte sedda i webbläsaren.
- Hela backendsviten stannar lokalt på `tests/kaos/test_modellsvar_utan_anvandning.py`
  och roten på `test_inv_sec_013`. Båda beror på en inaktuell `snajp-support/.env`
  (DeepSeek och den avvecklade Supabase-adressen), inte på den här ändringen.

## Att bygga vidare på

1. **Avtalsslut i utkasten.** Fältet finns och listan går att dela upp efter datum,
   men utkastkedjan läser det inte. Facit är låst (INV-LEADS-UTKAST-002): kräver Antons ja.
2. **Hitta bolag som liknar kundens bästa kunder.** Saknas helt; görs för hand i piloten.
3. **Listtillägget.** Importen ligger bakom tillägget `leadlists`. Om Buddy ska ha den
   utan tillägget är det ett prisbeslut.
4. **Kör Iris visas inte på fliken Listor**, och Listor är en egen flik igen. Det
   ändrar din placering från oktober. Säg till om du vill ha det annorlunda.
5. `LeadslistorView.tsx` är cirka 1 800 rader och bör delas nästa gång den ändras.

## Maskinen (Antons dator)

C: hade 0 GB ledigt och virtuellt minne 1 GB under kvällen. En `npm install` på full
disk skadade `node_modules`; den är ominstallerad med `npm ci`. Läs diskutrymmet före
installationer.
