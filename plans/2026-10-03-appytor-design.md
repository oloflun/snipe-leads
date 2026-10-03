# Appytornas design: från luftig dokumentsida till arbetsyta (2026-10-03)

Antons ord 2026-10-03, efter Snajp Suite fas 1–2: "Det ser inte särksilt bra ut, applicera /design på
all frontend".

**Verb:** redesign. **Läge:** preserve (IA:n är nyss godkänd, varumärket står). **Tier 0**, DESIGN.md
låst. **Operate mode** (impeccable `operate.md`). **Omfång:** alla appytor: `/dashboard`, `/admin`,
`/settings`, `/demo`. Marknadssidorna ingår inte (annan yta, Persuade).

## Referenslås

**Dominant referens: Twenty** (twenty.com, produktbilden i heron, fångad `.shots/ref-twenty/`).
Bevaras:
1. Objektets namn står litet i en rubrikrad; vyerna väljs i en tunn rad under den (vyväljare till
   vänster, Filter/Sort/Options som textknappar till höger).
2. Tabell som arbetsyta: rader runt 33–40 px, 14 px text, hårlinjer mellan rader, etikettrad överst
   i dämpad ton, värden som små chip.
3. Knappar i radhöjd, inte i hero-höjd: en primär per sida, liten.

**Lån 1: Mailchimp-konsolen** (katalogen, `entries/mailchimp`): serif-sidrubrik på en tät yta
(vår Fraunces), understrukna flikar med accentlinje under den valda, nyckeltal överst med hårlinjer.
**Lån 2: vår egen `SupportWorkspaceTabs`**: understrukna flikar med ochre, redan i bruk.

**Avvisat:** pillerflikar i 44 px med mörk platta (läser som knappar, inte som vyer), två stora
knappar per tabellrad, rubrikrad med 40 px luft ovan och 32 px under, kort med skugga, versaler med
spärrning (F-016, INV-UI-001).

**Auktoriteten** (TASTE § 1): datan. Allt annat (rubrik, flikar, knappar) går ner ett steg.

## Diagnos (pixlarna, inte koden)

Ur Antons skärmbilder 2026-10-03 och demon:

| Fel | Var | Varför det ser fel ut |
|---|---|---|
| Vyflikar är 44 px pillerknappar i `paper2` med svart aktiv | `ui.tsx` `flik*`, Leads, Tabell, Listor, admin Körningar/Händelser | Flikar ser ut som primärknappar; tre svarta block i samma vy tävlar med "Kör Iris" |
| Rubrikraden äter skärmen | `PageShell` `py-10` + `mt-8` | 120 px innan första datan; ingen hårlinje som säger var sidhuvudet slutar |
| Tabellceller `py-4`, 15 px | `ui.tsx` `Cell`, `Rad` | Hälften så många rader per skärm som Twenty; data läses som brödtext |
| Två stora knappar per kundrad | admin `Kundtabell` | Knapparna, inte kunderna, äger tabellen |
| Datum bryts på två rader | admin Kunder ("2026-\n08-16") | Kolumnbredd utan `nowrap` |
| Pipelinekort med fullbred `<select>` 44 px | `Pipeline.tsx` | Kontrollen är större än kortets innehåll |
| Versaler med spärrning | `LeadsControls` m.fl. ("BARA UTKAST", "MÅLGRUPP OCH AUTONOMI") | Bryter appytornas skala och F-016 |

## Rundor

Kedjans § 5: en runda byggs, verifieras helt (pixlar lästa), sedan nästa.

**Runda 1: systemet** (`components/ui.tsx`, `PageShell`) slår igenom överallt.
- Sidhuvud: `py-6 md:py-8`, hårlinje under rubrikraden, `mt-6` till innehållet.
- Flikar: understrukna (`border-b-2`, ochre på vald, 44 px träffyta kvar), flikraden med
  hårlinje (`fliklista`).
- Tabell och rader: `py-3`, 14 px data, `nowrap` på meta som datum.
- Knappar: samma vokabulär, `text-[0.875rem]`, `px-4`.
- DESIGN.md § App surfaces uppdateras med tabellen ovan som beslut.

**Runda 2: tyngsta sidorna.** Admin Kunder (radknappar → länkar, datum nowrap), Pipelinekort
(kompakt statusval), Leads-listans rader, LeadsControls versaler, Kundtjänst-inkorgens verktygsrad.

**Runda 3: genomgång.** Varje route i 1440/375/320, fynd rättas, tills ett helt pass är rent.

## Verifiering per runda

Demo (`/demo`, `/demo/leads` alla vyer, `/demo/att-gora`, `/demo/support`, `/demo/kvitton`,
`/demo/installningar`) i 1440 och 375, PNG via `shoot.py`, lästa. Admin och inloggade sidor:
lokal stack saknas (Docker), så de granskas på development efter push, utan kunddata i bilder
som lämnar sessionen. tsc, rotinvarianter (INV-UI-001, INV-COPY-001), npm test.
