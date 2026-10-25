# Plan: utkasten, erbjudandena och kampanjerna (2026-10-25)

Antons beställning 2026-10-25, i hans ordning. Bevakningslistan längst ned
uppdateras efter varje steg. Den visar vad som är klart, vad som är verifierat
och vad som återstår.

## Utgångsläget (uppmätt, inte antaget)

- **Autoutkasten.** Körningen 2026-10-24 21:01 hos Snajp: 19 bolag
  researchades, 11 blev leads och 10 fick utkast. Åtta byggbolag i Umeå fälldes
  med "Ingen av kundens produkter passar bolaget" fast researchens egen
  motivering sa att de passar ("god matchning för Snajps AI-agenter"). Samma
  fel drabbade 27 av 57 bolag 2026-10-24 och 0 av 53 bolag 2026-10-22.
  Tidsmässigt sammanfaller det med att Iris produkttext skrevs om 2026-10-24.
  Därtill står luckan "Du har INGA godkända erbjudanden … Erbjud därför
  ingenting" i varje research hos Snajp, fast erbjudandena finns i
  inställningarna. Körningens lista "Leads och utkast" visade de fällda bolagen
  som leads med "Inget utkast", och "Skriv utkast till 9" hade researchat om dem
  bara för att fälla dem igen.
- **Sebbes utkaständringar 2026-10-24** är fyra commits: omgång 7 (`16a121f`,
  `d604e51`) och Iris-formen "erbjudandet först" (`2f61284`, `7508326`). Hans
  leveransändringar (ren text, volym, stopp vid studs) rör inte texten och
  står kvar.
- **Erbjudandena** finns sedan 2026-10-10 (`app/leads/erbjudanden.py`). De
  består av en fast katalog med tre erbjudanden, vikter, deterministisk
  tilldelning per prospekt och mätning per erbjudande med ett z-test. UI:t är
  ett kort i Inställningar › Målgrupp och automation och inte en flik under
  Leads. Kunden kan inte lägga till egna erbjudanden. Erbjudandet läggs till som
  ett block i ärendet, och vinkeln kommer ur researchens eget erbjudande.
  Onboardingen har inget erbjudandesteg, och nya kunder skickar därför utan
  erbjudande. Kampanjer till befintliga listor finns inte.

## Steg 1: autoutkasten (klart i koden)

1. Kontextpaketet säger inte längre "inga godkända erbjudanden" när kunden har
   aktiva erbjudanden (`app/leads/context_pack.py`).
2. Iris produkttext återställs till texten före 2026-10-24
   (`scripts/snajp_malgrupp.py`). Den når databasen när skriptet körs med
   `--apply`, tillsammans med de nya pilotvillkoren i steg 3.
3. Körningens lista visar bara leads. De bortvalda står under Bortvalda med
   skälet, och "Skriv utkast" researchar inte om dem (`api/leads.py:_korningens_leads`).

## Steg 2: Sebbes utkaständringar tillbaka (klart i koden)

Utkastdelen av de fyra commitsen är återställd: skrivstilen, grundprompten,
`_IRIS_FORM`, grindens tillägg och Snajps villkor och instruktion. Hans två
testfiler går med i återställningen. `docs/BESLUT.md` och förslagsdokumentet
står kvar som historik. Beslutet skrivs in som en ny post.

## Steg 3: mejlformen (A) och B-versionen

**Form A**, efter hälsningen:

1. **Ingången:** en antagen utmaning i deras typ av arbete som produkten löser,
   med något konkret ur deras verksamhet. Den skrivs som en balansgång eller
   något som tar tid, inte som kritik. Mejlet påstår aldrig att de brister och
   ställer aldrig deras eget löfte mot ett misslyckande. Förebilderna är
   Antons tre första exempel. Hans två sista är motexempel.
2. **Produkten:** vad agenten gör åt dem, i en mening.
3. **Piloten, i varje mejl:** vi tar in 20 företag i en kostnadsfri pilot på
   tre månader med alla funktioner. Den som är nöjd och vill stanna får 50 %
   rabatt därefter. Inget mer.
4. **Avslutet:** en vardaglig inbjudan. Den som vill veta mer eller testa kan gå
   in på snajp.se/demo eller svara på mejlet, så bokar vi en kostnadsfri
   genomgång. Ett avslut av typen "Svara X så gör vi Y" är förbjudet, och
   grinden fäller det.

**Form B** behåller samma ingång. Därefter kommer en fråga om vilket av två
moment som tar mest tid hos dem. För Iris är det att hantera de leads de redan
får in eller att hitta nya, och för Supportagenten att gå igenom kundmejlen
eller att sitta i supportchattarna. Produkten tar hand om båda delarna och
anpassas efter deras behov. Sedan följer piloten och avslutet som i A.

- A och B är två arms i erbjudandemätningen med lika vikt, alltså hälften var.
- Tonen är vardaglig, som ett mejl från en person till en annan.
- Kod: `leads-skrivstil.md`, grundprompten § 10, `leads-hard-rules.md` (som
  tillåter två vägar till samma inbjudan), `_INGANGSUPPGIFT`, `_INGANGSFORMER`,
  formerna i `erbjudanden.py` och grinden (fynden `svara_sa_avslut` och
  `kritisk_ingang`).
- **Facit 2026-10-16** slutar med "Svara 'pilot' …", som Anton nu förbjuder.
  Facit står kvar för allt annat. Det nya fyndet undantas där, med en
  hänvisning till beslutet, och ett nytt facit tas fram ur första körningen
  med den nya formen. Anton godkänner det.

## Steg 4: egna erbjudanden, fliken Erbjudanden och statistiken

- **Egna erbjudanden.** Kunden lägger till ett erbjudande med namn, fritext
  (villkoren, per produkt eller för alla) och form (A rak eller B fråga), och
  slår på det med en vikt. Katalogens tre erbjudanden står kvar som de är, så
  gamla inställningar fungerar utan migrering. Allt sparas i
  `settings.erbjudanden` (`egna`), och ingen tabell tillkommer.
- **Erbjudandet styr hela mejlet.** Det läggs inte till som ett stycke. Det
  avgör ingångens utmaning, produktmeningen och avslutet. Agenten översätter
  erbjudandet till mottagarens verksamhet, och villkorens siffror och löften
  står kvar oförändrade i sak. Det kundens erbjudande ger går före
  researchens egen vinkel.
- **Fliken Leads › Erbjudanden** finns för alla kunder med leads och flyttar
  hit från Inställningar. Där går det att slå på och av, lägga till och ta bort
  erbjudanden, sätta vikt (A/B/C …) och se utfallet per erbjudande: utkast,
  skickade, svar, positiva och möten, med andelar och vilket som leder när
  skillnaden håller.

## Steg 5: erbjudandet i onboardingen

Onboardingen får ett valfritt steg, Erbjudande: "Vilket erbjudande ska
utskicken bygga på?". Svaret blir kundens första egna erbjudande, aktivt i
form A. Agenten anpassar det till varje prospekt på samma sätt som för Snajp
och Alunix (steg 4).

## Steg 6: kampanjer till befintliga listor

En kampanj består av namn, ämnesrad och text. Varje mottagare får "Hej
{förnamn}," (eller "Hej,") och sedan kampanjtexten, utan research och utan
modell. Mottagarna är en befintlig leadslista eller körningens leads.
Utkasten hamnar i granskningen och skickas med "Godkänn och skicka alla"
genom samma sändspärrar, fot och avregistrering som allt annat. Utfallet
räknas per kampanj i samma mätning som erbjudandena. Förloppet och utfallet
står kvar på kampanjens rad efter en omladdning.

## Verifiering

- Pytest för leads, agent och api, plus facit och grind.
- `tsc` och `lint`, och INV-COPY-001 (sv+en) för varje komponent som ändras.
- Fliken och onboardingen kontrolleras i den lokala stacken
  (`scripts/lokal_stack.py`) och aldrig mot development-databasen.
- Provutkast i development på fem leads per form efter push, lästa av mig.
  Kräver Antons ja till push och till `snajp_malgrupp.py --apply`.

## Bevakningslista

Senast uppdaterad 2026-10-25. Allt nedan är kod i arbetskatalogen, inte
committat och inte pushat. "Testad" betyder pytest, typkontroll och
INV-COPY-001 lokalt. Inget har körts mot en riktig modell eller i development.

| # | Punkt (Antons ord) | Läge | Återstår |
|---|---|---|---|
| 1 | Utkast genereras inte till alla klara leads | Kod klar och testad. Bortvalda bolag syns bara under Bortvalda | Push till development och en ny körning som visar att byggbolagen kvalificeras igen |
| 1a | Byggbolag fälls med "ingen produkt passar" | Kod klar (luckan), produkttexten återställd i skriptet | `snajp_malgrupp.py --env development --apply` och en ny körning |
| 2 | Återställ Sebbes utkaständringar | Kod klar, testad | Push |
| 3 | Mjukare ingång, inte påhoppande | Klar: skrivstil, grundprompt, ingångsformer, personaliseringssteget, fyndet `kritisk_ingang` (testat på Antons fem exempel) | Prov på riktiga leads |
| 4 | Förbjud "svara X så gör vi Y" | Klar: alla prompter plus fyndet `svara_sa_avslut`. Gamla facit undantar fyndet | Nytt facit efter första körningen (Antons ja) |
| 5 | Piloten i varje mejl (20 företag, 3 mån gratis, 50 %) + demo/genomgång | Klar i `snajp_malgrupp.py` (pilot_a/pilot_b, villkor per produkt) | `--apply` mot development, och main efter release |
| 6 | Vardagligt, person till person | Klar i skrivstil och erbjudandeblocket | Prov på riktiga leads |
| 7 | B-version med frågan, A/B 50/50 | Klar: form B i `erbjudanden.FORMER`, två arms med lika vikt, testad fördelning | Prov på riktiga leads |
| 8 | Fliken Erbjudanden under Leads, alla kunder | Klar: Leads › Erbjudanden, länk från Inställningar | Visuell kontroll i den lokala stacken |
| 9 | Statistik och styrning A/B/C | Klar: utkast, skickade, svar, positiva, möten, ledare per erbjudande; vikt, på/av, lägg till och ta bort | Visuell kontroll |
| 10 | Erbjudandet styr hela utkastet, inte ett stycke | Klar: blocket styr ingång, produktmening och avslut, och går före researchens vinkel | Prov på riktiga leads |
| 11 | Onboarding: sektion för erbjudanden | Klar: sektion i målgruppssteget, ett erbjudande per stycke | Visuell kontroll; en ny testregistrering |
| 12 | Agenten anpassar kundens erbjudande till prospektets verksamhet | Klar i blocket ("översätt erbjudandet till mottagarens verksamhet") | Prov med en kunds eget erbjudande |
| 13 | Kampanjer: massutskick till befintliga listor, Hej Namn + text | Klar: API, kö, sändspärr, utfall, UI. Testad med minneslagret | Migration 114 i development (Antons ja), visuell kontroll, ett provutskick |
| 14 | Plan och bevakningslista | Den här filen | Uppdateras löpande |
