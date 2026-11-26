# Paritetslistan: Snajp CRM mot Twenty

Måttet på hur komplett Snajp CRM är mot förlagan. Varje funktionsrad i inventeringen av
Twenty (`docs/crm/underlag/twenty-01` till `twenty-13`, 3 666 rader, och luckgranskningarna
`twenty-99a` till `99c`) får ett läge mot det som finns i Snajps kod. Raderna står i en fil
per område under [`paritet/`](paritet/).

Senast uppdaterad 2026-11-26. **Listan är inte klar**: tio av sexton delar är genomgångna,
och bara en av dem är kontrollerad. Se "Vad som återstår".

## Lägena

- **verifierad**: funktionen finns, och ett test prövar den eller en godkänd bild visar den.
- **byggd**: koden finns, men inget test och ingen bild prövar just den raden.
- **delvis**: en del av raden finns. Filen säger vad som finns och vad som saknas.
- **inte gjord**: finns inte. Filen säger i vilken fas den hör hemma.
- **avstår**: byggs inte. Skälet står på raden: Enterprise-fil i förlagan, gäller bara egen
  drift av Twenty, ersätts av något Snajp redan har, eller strider mot en regel.

## Läget i tal

Tio områden, 2 581 rader.

| Område | Rader | Verifierad | Byggd | Delvis | Inte gjord | Avstår | Kontrollerad |
|---|---:|---:|---:|---:|---:|---:|---|
| [01 Datamodell, fält och relationer](paritet/paritet-01-datamodell-falt-relationer.md) | 210 | 5 | 3 | 74 | 111 | 17 | nej |
| [02 Vyer, filter, sortering, gruppering](paritet/paritet-02-vyer-filter-sortering-gruppering.md) | 208 | 3 | 2 | 54 | 147 | 2 | nej |
| [03 Postsida, tidslinje, anteckningar, uppgifter](paritet/paritet-03-postsida-tidslinje-anteckningar-uppgifter.md) | 241 | 18 | 4 | 83 | 125 | 11 | nej |
| [04 Navigering, kommandomeny, sök, favoriter](paritet/paritet-04-navigering-kommandomeny-sok-favoriter.md) | 166 | 2 | 6 | 40 | 117 | 1 | nej |
| [05 Mejl, kalender, synk, utskick](paritet/paritet-05-mejl-kalender-synk-utskick.md) | 347 | 0 | 0 | 14 | 317 | 16 | nej |
| [06 Arbetsflöden och automationer](paritet/paritet-06-arbetsfloden-automationer.md) | 291 | 0 | 0 | 10 | 270 | 11 | nej |
| [07 API, webhooks, appar, MCP](paritet/paritet-07-api-webhooks-appar-mcp.md) | 351 | 25 | 1 | 41 | 264 | 20 | nej |
| [10 Dashboards och diagram](paritet/paritet-10-dashboards-diagram.md) | 192 | 1 | 0 | 32 | 154 | 5 | nej |
| [11 AI-agenter och färdiga appar](paritet/paritet-11-ai-agenter-och-fardiga-appar.md) | 271 | 0 | 0 | 2 | 259 | 10 | nej |
| [12 UI-system och användarflöden](paritet/paritet-12-ui-system-och-anvandarfloden.md) | 304 | 29 | 34 | 130 | 92 | 19 | ja |
| **Summa** | **2 581** | **83** | **50** | **480** | **1 856** | **112** | |

I andelar: 3 procent är verifierade, 2 procent byggda, 19 procent delvis, 72 procent inte
gjorda och 4 procent avstår vi från.

**Så ska talen läsas.** Snajp CRM är i dag ett register med kundsynk, API, webhooks och
svenska format. Twenty är dessutom en plattform: egna objekt och fält, sparade vyer med
filter och gruppering, arbetsflöden, mejl- och kalendersynk, dashboards och AI-agenter. De
fyra områdena 05, 06, 10 och 11 står för 1 000 av de 1 856 rader som inte är gjorda, och
ingenting i dem är påbörjat. Snajp har egen mejlhantering och egna agenter i Leads och i
supporten, men de nås inte från CRM:et än och räknas därför inte här (fas 4 och 5).

**Talen är läsarnas egna.** I det enda område som hann kontrolleras (12) prövades 126 rader
mot koden och 15 fick ändrat läge, alltså ungefär var åttonde. Efter kontrollen var de
verifierade 29 i stället för 32, delvis 130 i stället för 139 och inte gjorda 92 i stället
för 80. Räkna med samma felandel i de nio okontrollerade områdena, och med att felen oftare
gör listan för snäll än för sträng.

Läget är också taget medan två byggen pågick. Affärer med tavla, uppgifter, anteckningar,
aktiviteter och bilagor är sedan dess committade i API:t (`2fa09eb3`), och gränssnittet för
synkens två nivåer, webhooks, papperskorg och historik likaså (`bd1b5b81`). Rader som
gäller dem kan stå för lågt.

## De största luckorna

Det en användare av Twenty skulle sakna mest, ur områdesfilernas egna sammanfattningar:

1. **Affärer, uppgifter, anteckningar, aktiviteter och bilagor finns bara i API:t.** Ingen
   tavla att dra affärer på, ingen uppgiftslista, ingen anteckning i postpanelen.
2. **Inga sparade vyer.** Filter och sortering försvinner vid omladdning, och det finns
   ingen filterbyggare, ingen gruppering, inget kolumnval och ingen summering.
3. **Ingen postsida.** Posten öppnas i en panel med fasta flikar.
4. **Inga egna objekt och fält.** Egna värden går att spara genom API:t (`custom`, högst
   50) men har ingen definition, etikett eller visning i gränssnittet.
5. **Ingen redigering direkt i cellen** och ingen tangentbordsnavigering i listan.
6. **Ingen import och export genom gränssnittet**, och ingen sammanslagning av dubbletter
   för hand.
7. **Inga arbetsflöden.**
8. **Mejl och kalender når inte CRM:et.** Tidslinjen visar Snajps egna utskick och svar,
   men kundens egen inkorg och kalender synkas inte in på posten.
9. **Inga dashboards med egna diagram.** Översikten har fasta nyckeltal.
10. **Inga roller och behörigheter per objekt eller fält** i CRM:et, och ingen
    inställningsyta.

## Vad som återstår

Arbetet stoppades av veckogränsen för Opus 2026-11-26. Den nollställs 2 december. Enligt
Antons regel körs läsarna på Opus och inte på en lägre modell.

| Del | Läge |
|---|---|
| 08 Inloggning, arbetsyta, roller, säkerhet | påbörjad: 34 av cirka 350 rader i [filen](paritet/paritet-08-inloggning-arbetsyta-roller-sakerhet.md) |
| 09 Import, export, dubbletter, berikning | nästan klar: 204 rader i [filen](paritet/paritet-09-import-export-dubbletter-berikning.md), inte räknad och inte kontrollerad |
| 13 Handboken som facit | inte påbörjad |
| 99a, 99b, 99c Luckgranskningarnas egna rader | inte påbörjade |
| Kontroll av område 01 till 07, 10 och 11 | inte gjord |
| Omläsning av raderna om affärer, uppgifter, bilagor, webhooks och papperskorg efter att byggena landat | inte gjord |

Flödet går att återuppta där det stannade: skriptet ligger i sessionens katalog
(`crm-paritetslista`), och läsarna fortsätter i de filer som finns.
