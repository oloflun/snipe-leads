# Samhällspåverkan av Snajps AI-system (ISO 42001 A.5.5)

**Utkast, inte godkänt.** 2026-11-18, Claude (agent), på Antons uppdrag.
A.5.5 står som "saknas" (`docs/compliance/ramverk/iso42001/matris.md:124`).
Här står vad koden begränsar i dag och vad som inte är mätt. Ingen bedömning
är beslutad, och ingen åtgärd är föreslagen som beslut.

## 1. Mängden automatiska kallmejl (Iris)

**Vad koden begränsar** (`snajp-support/app/leads/send_guard.py`):

- Högst 100 utskick per dag och kund (rad 66), 20 per dag de första 14 dagarna
  (rad 48-49), och högst 5 fler än veckans största dag (rad 59-60).
- Ett bolag kontaktas högst en gång per 90 dagar (rad 85), bara vardagar
  08-17 (rad 89-90).
- Alla utskick stoppas vid mer än 3 % studs eller 0,1 % klagomål på 14 dagar
  (rad 74-79).
- Avregistrering gäller hela kunden och permanent; de tre första utskicken
  granskas av människa (rad 93; `docs/intresseavvagning_kallmejl.md:210, 223`).
- I drift skickas inget utan mänskligt godkännande, eftersom
  `SEND_QUEUE_POLL_SECONDS` inte är satt (`iris.md` avsnitt 5).

**Inte mätt:** den samlade volymen över alla kunder. Taket gäller per kund;
med många kunder växer den totala mängden linjärt. I oktober gick omkring 600
kallmejl ut på några dagar, och de flesta tycks ha hamnat i skräpposten
(IA rad 164-168). Hur mottagarna uppfattar AI-skrivna säljmejl är inte mätt.

**Beslutad:** nej (ägarens beslut). IA:n kräver att Anton bekräftar taket på
100 som ett medvetet val (IA rad 270-271).

## 2. Följder för arbetet i kundtjänst (supportagenten)

**Vad koden begränsar:** varje kategori står på utkast till granskning från
start (`snajp-support/app/email_pipeline/processor.py:652-653`;
`app/villkor/VillkorSida.tsx:38-40`). Ärenden utan underlag, med begäran om en
människa eller med negativt sentiment lämnas över (`processor.py:657-673,
756`). En människa äger ett överlämnat samtal (INV-ESC-001).

**Inte mätt:** hur mycket arbete som flyttas från människor till agenten hos
kunderna, vilka kunder som satt kategorier på automatiskt svar
(`matris.md:212`), och om kundernas kunder får sämre tillgång till en
människa. Andelen överlämningar i drift följs inte (`matris.md:76`).

**Beslutad:** nej (ägarens beslut).

## 3. Informationskvalitet och förtroende

**Vad koden begränsar:**

- Supportsvar prövas mot namngivna källor; ett ostött tal, en frist eller en
  adress stoppar autosvar (INV-GROUND-002, -003). Iris utkast grindas på den
  exakta text som köas (INV-GROUND-001, -004). Kvitto- och bokföringschatten
  fäller belopp som inte hämtats (INV-BOOK-003, `bokforingschatt.md`).
- Autosvar och chatt säger att en AI svarar (INV-AI-001), **bara i
  `development`** till release-PR 60 (`README.md`, läsanvisningen).

**Inte begränsat:** kallmejl från Iris bär ingen upplysning om att en AI skrev
dem; om art. 50.1 kräver det är en juristfråga
(`docs/compliance/ramverk/iso42001/ai-forordningen.md:66`). Art. 50.2
(maskinläsbar märkning) är inte bedömd (samma, rad 46, 67).

**Inte mätt:** felandelen i svar och utkast som går ut i drift.

**Beslutad:** nej (ägarens beslut).

## 4. Miljö och beräkning

**Belagt:** bara tokenmängder. Tänkandet stängdes av 2026-09-19 efter mätning
som visade 5-13 gånger fler utdatatokens med tänkande
(`snajp-support/app/config.py:327-339`). Leads har ett tokentak per kund och
dygn (`config.py:456-462`). Leads drog 165 M tokens på 14 dygn i oktober
(`docs/compliance/modellbyte-underlag.md:425-428`).

**Inte belagt:** energi, utsläpp eller vattenåtgång. Google redovisar inget
sådant per anrop i något dokument i repot. Ingen bedömning görs här.

**Beslutad:** nej (ägarens beslut).

## 5. Beroende av en modelleverantör

**Läge:** alla textsteg, bildsteg och inbäddningar går till Google Gemini på
Vertex AI i ett projekt med ett servicekonto för alla miljöer
(`docs/compliance/gemini-bedomning.md:86`, A8). Gemini 2.5 har passerat
Googles pensionsdatum, och ingen godkänd ersättare finns för utkast och bilder
(`README.md`, sista avsnittet). Jev (TypeSafe) används bara i leads och är av
i `main` (`jev.md`).

**Vad koden begränsar:** uppstarten vägrar leverantörer och regioner utanför
EU där data är riktig (INV-DATA-004, -006, bara i `development`). Det minskar
risken för fel leverantör men ökar beroendet av en.

**Inte mätt:** någon reservleverantör. Jämförelsen med Mistral, Azure och
Bedrock är orientering, inte prövad (`gemini-bedomning.md:239-249`). Ett byte
kräver en ny utvärdering av hela kedjan (samma, rad 249).

**Beslutad:** nej (ägarens beslut).

## Det som saknas för en beslutbar bedömning

Riskkriterier (`matris.md:44`), mätning i drift av volym, överlämningar och
fel, juristens svar om art. 50, och ägarens beslut om tak och leverantör.
