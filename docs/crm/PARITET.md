# Paritetslistan: Snajp CRM mot Twenty

Måttet på hur komplett Snajp CRM är mot förlagan. Varje funktionsrad i inventeringen av
Twenty (`docs/crm/underlag/twenty-01` till `twenty-13`, och luckgranskningarna `twenty-99a`
till `99c`) får ett läge mot det som finns i Snajps kod. Raderna står i en fil per område
under [`paritet/`](paritet/).

Senast uppdaterad 2026-11-27. **Alla sexton delar är lästa. Fyra är kontrollerade** (01,
03, 07 och 12). Tolv är det inte, och flera av dem lästes innan de senaste byggena landade.
Se "Vad som återstår".

## Lägena

- **verifierad**: funktionen finns, och ett test prövar den eller en godkänd bild visar den.
- **byggd**: koden finns, men inget test och ingen bild prövar just den raden.
- **delvis**: en del av raden finns. Filen säger vad som finns och vad som saknas.
- **inte gjord**: finns inte. Filen säger i vilken fas den hör hemma.
- **avstår**: byggs inte. Skälet står på raden: Enterprise-fil i förlagan, gäller bara egen
  drift av Twenty, ersätts av något Snajp redan har, eller strider mot en regel.

## Läget i tal

Sexton delar, 3 665 rader.

| Område | Rader | Verifierad | Byggd | Delvis | Inte gjord | Avstår | Kontrollerad |
|---|---:|---:|---:|---:|---:|---:|---|
| [01 Datamodell, fält och relationer](paritet/paritet-01-datamodell-falt-relationer.md) | 210 | 4 | 4 | 75 | 110 | 17 | ja |
| [02 Vyer, filter, sortering, gruppering](paritet/paritet-02-vyer-filter-sortering-gruppering.md) | 208 | 3 | 2 | 54 | 147 | 2 | nej |
| [03 Postsida, tidslinje, anteckningar, uppgifter](paritet/paritet-03-postsida-tidslinje-anteckningar-uppgifter.md) | 241 | 21 | 2 | 82 | 125 | 11 | ja |
| [04 Navigering, kommandomeny, sök, favoriter](paritet/paritet-04-navigering-kommandomeny-sok-favoriter.md) | 166 | 2 | 6 | 40 | 117 | 1 | nej |
| [05 Mejl, kalender, synk, utskick](paritet/paritet-05-mejl-kalender-synk-utskick.md) | 347 | 0 | 0 | 14 | 317 | 16 | nej |
| [06 Arbetsflöden och automationer](paritet/paritet-06-arbetsfloden-automationer.md) | 291 | 0 | 0 | 10 | 270 | 11 | nej |
| [07 API, webhooks, appar, MCP](paritet/paritet-07-api-webhooks-appar-mcp.md) | 351 | 23 | 3 | 42 | 263 | 20 | ja |
| [08 Inloggning, arbetsyta, roller, säkerhet](paritet/paritet-08-inloggning-arbetsyta-roller-sakerhet.md) | 346 | 11 | 7 | 91 | 96 | 141 | nej |
| [09 Import, export, dubbletter, berikning](paritet/paritet-09-import-export-dubbletter-berikning.md) | 203 | 25 | 15 | 41 | 117 | 5 | nej |
| [10 Dashboards och diagram](paritet/paritet-10-dashboards-diagram.md) | 192 | 1 | 0 | 32 | 154 | 5 | nej |
| [11 AI-agenter och färdiga appar](paritet/paritet-11-ai-agenter-och-fardiga-appar.md) | 271 | 0 | 0 | 2 | 259 | 10 | nej |
| [12 UI-system och användarflöden](paritet/paritet-12-ui-system-och-anvandarfloden.md) | 304 | 29 | 34 | 130 | 92 | 19 | ja |
| [13 Handboken som facit](paritet/paritet-13-handboken-som-facit.md) | 393 | 13 | 3 | 99 | 197 | 81 | nej |
| [99a Luckor, fronten](paritet/paritet-99a-luckor-front.md) | 35 | 0 | 0 | 6 | 17 | 12 | nej |
| [99b Luckor, servern](paritet/paritet-99b-luckor-server.md) | 55 | 2 | 2 | 14 | 10 | 27 | nej |
| [99c Luckor mot facit](paritet/paritet-99c-luckor-facit.md) | 52 | 1 | 0 | 4 | 28 | 19 | nej |
| **Summa** | **3 665** | **135** | **78** | **736** | **2 319** | **397** | |

I andelar: 4 procent är verifierade, 2 procent byggda, 20 procent delvis, 63 procent inte
gjorda och 11 procent avstår vi från.

**Så ska talen läsas.** Snajp CRM är i dag ett register med kundsynk, API, webhooks,
affärstavla, uppgifter, filer, spärrlista och svenska format. Twenty är dessutom en
plattform: egna objekt och fält, sparade vyer med filter och gruppering, arbetsflöden, mejl-
och kalendersynk, dashboards och AI-agenter. De fyra områdena 05, 06, 10 och 11 står för
1 000 av de 2 319 rader som inte är gjorda, och ingenting i dem är påbörjat. Snajp har egen
mejlhantering och egna agenter i Leads och i supporten, men de nås inte från CRM:et än och
räknas därför inte här (fas 4 och 5).

**Område 13 och 99 räknar delvis samma funktioner en gång till.** Handboken (13) beskriver
ur användarens håll det som område 01 till 12 beskriver ur kodens, och luckgranskningarna
(99) är rader som de första läsarna missade. Summan är därför ett mått på hur mycket av
underlaget som är läst, inte ett exakt antal funktioner.

**Område 08 avstår från 141 rader.** De flesta gäller Twentys egen inloggning, egna roller
och egen drift, som Snajp redan har i arbetsytan och inte bygger en gång till i CRM:et.

**Talen är läsarnas egna, och kontrollen ändrar dem.** I de fyra kontrollerade områdena
prövades 361 rader mot koden och 44 fick ändrat läge, alltså ungefär var åttonde: 12 (126
prövade, 15 ändrade), 01 (63 och 17), 03 (80 och 5), 07 (92 och 7). Räkna med samma andel
i de tolv okontrollerade delarna, och med att felen oftare gör listan för snäll än för
sträng.

**Det som byggts efter läsningen står för lågt.** Sedan områdena lästes har detta fått
gränssnitt eller API: filer i postens panel (`6fbd9c5d`), kundlistan Iris och Egna, bolagets
affärer i panelen samt ändra och ta bort i historiken (`b7e93ea3`), relationen ej aktuell,
förlustorsak ur lista och personens källa (`f1b8eea9`, `80db6b8c`), Hjälprutan i CRM:et
(`80db6b8c`), den gemensamma spärrlistan med NIX-uppladdning (`69b8537e`, `04badf37`), den
samlade uppgiftslistan (`0d5257f9`), egna steg på tavlan (`1b51e2e5`), jobbet som tömmer
papperskorgen (`9967d7f1`) och uppslaget i SCB:s företagsregister (`05c16340`, `a0b35b45`). Raderna om dem
ändras först när områdena läses om.

## De största luckorna

Det en användare av Twenty skulle sakna mest, ur områdesfilernas egna sammanfattningar:

1. **Inga sparade vyer.** Filter och sortering försvinner vid omladdning, och det finns
   ingen filterbyggare, ingen gruppering, inget kolumnval och ingen summering.
2. **Ingen postsida.** Posten öppnas i en panel med fasta flikar.
3. **Inga egna objekt och fält.** Egna värden går att spara genom API:t (`custom`, högst
   50) men har ingen definition, etikett eller visning i gränssnittet.
4. **Ingen redigering direkt i cellen** och ingen tangentbordsnavigering i listan.
5. **Ingen import och export genom gränssnittet**, och ingen sammanslagning av dubbletter
   för hand. Det enda som laddas upp i gränssnittet är spärrlistan.
6. **Inga arbetsflöden.**
7. **Mejl och kalender når inte CRM:et.** Tidslinjen visar Snajps egna utskick och svar,
   men kundens egen inkorg och kalender synkas inte in på posten.
8. **Inga dashboards med egna diagram.** Översikten har fasta nyckeltal.
9. **Inga roller och behörigheter per objekt eller fält** i CRM:et, och ingen
   inställningsyta.
10. **Arbetet runt affärerna har rester.** Tavlan, egna steg, panelen, filer, uppgifter,
    anteckningar och aktiviteter finns. Kvar: affärer som lista med filter, flera tavlor,
    påminnelser om uppgifter och uppgifter knutna till en person eller affär från den
    samlade listan (där väljs bara bolag).

## Vad som återstår

| Del | Läge |
|---|---|
| Kontroll av område 02, 04, 05, 06, 08, 09, 10, 11, 13 och 99a till 99c | inte gjord |
| Omläsning av raderna om det som byggts efter läsningen (stycket ovan) | inte gjord |

Läsarna av 08, 09, 13 och 99 och kontrollanterna av 01, 03 och 07 kördes på Sonnet, enligt
Antons ja 2026-11-27 (det gäller bara paritetslistan). Område 12 kontrollerades tidigare på
Opus. Flödet går att återuppta: skriptet ligger i sessionens katalog
(`crm-granskning-och-paritet`), och läsarna fortsätter i de filer som finns.
