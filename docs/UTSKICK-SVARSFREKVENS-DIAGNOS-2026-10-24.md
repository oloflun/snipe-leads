# Varför ~600 utskick gav 2 riktiga svar (diagnos 2026-10-24)

Sebbes fråga 2026-10-24: "Vi har skickat typ 600 leads och bara fått 9 svar,
de flesta autosvar och 2 nej tack. Är det något fel i hur Iris skriver?"

**Kort svar:** texten är inte huvudproblemet, även om den har svagheter.
Två saker utanför texten väger tyngre: **en stor del av mejlen når troligen
inte inkorgen**, och **mejlen går mest till info@-adresser med ett erbjudande
som ber om ett köpbeslut i första kontakten**. Texten kommer på tredje plats.

## Vad siffrorna säger

| | Antal | Andel |
|---|---|---|
| Skickade | ~600 | |
| Svar totalt | 9 | 1,5 % |
| Varav människor | 2 (båda nej) | 0,3 % |
| Varav autosvar | ~7 | ~1,2 % |

- En fungerande kall kampanj mot svenska småbolag ligger brukligt på 2–5 %
  mänskliga svar. 0,3 % är en storleksordning under.
- **Autosvaren är ledtråden.** Ett mejl som hamnar i skräpposten eller
  stoppas av filtret ger inget autosvar. Mot info@-adresser (som ofta har
  ärendekvitton och frånvaromeddelanden) brukar autosvaren vara fler än
  1 %. Att de är så få tyder på att många mejl aldrig nådde inkorgen. Det är
  en slutsats, inte en mätning: se "Mät först" nedan.
- Nej tack är inget dåligt tecken. De som läser svarar. Problemet är hur få
  som läser.

> Databasen gick inte att läsa härifrån (behörighetsspärren räknar
> development-spegeln som produktionsdata), så diagnosen bygger på koden,
> DNS och facit-exemplen. Siffrorna ovan är Sebbes.

## 1. Leveransen (störst sannolik effekt)

**Vad koden gör i dag** (`app/leads/send_provider.py`, `send_guard.py`):

- Alla utskick går via Resend från **huvuddomänen `snajp.se`**, samma domän
  som supporten, lösenordsåterställningen och kundernas mejl.
- **Volymkurvan:** taket satt fast på 20/dag fram till 2026-10-20 (buggen i
  `_alder_i_dagar`). Efter fixen 2026-10-21 får volymen **dubblas per dag**
  (20 → 40 → 80 → 160 …). Med ~200 godkända i kön betyder det att en stor
  del av de 600 gick ut på några få dagar från en domän med nästan noll
  positiva signaler (inga svar, inga "inte skräp"). Det är exakt mönstret
  Microsoft 365 och Gmail straffar, och de flesta svenska småbolag ligger på
  Microsoft 365 eller Loopia/One.com.
- **HTML-delen bär en logotyp-bild** (`signatur.py`), och foten bär en
  länk. Bild + länk i ett första mejl från en okänd avsändare är en
  klassisk reklamsignal och skickar mejlet till "Andra"/"Kampanjer" eller
  skräp.
- **DNS:** DKIM för Resend finns och return-path har SPF, så autentiseringen
  är godkänd. DMARC står på `p=none` utan `rua`, så vi får inga rapporter
  om vad som händer med mejlen.

**Åtgärder:**

1. **Separat utskicksdomän** (t.ex. `snajp-mail.se` eller `hej.snajp.se`)
   med egen DKIM/SPF/DMARC, så att kalla utskick aldrig kan skada
   leveransen av supportens och kundernas mejl på `snajp.se`. Värm den i
   2–3 veckor.
2. **Byt dubblingen mot en flack kurva** och ett fast tak per brevlåda:
   ungefär 30–50 per dag och avsändaradress, höjt med ~10 i veckan, och
   **stoppa automatiskt** om studs > 3 % eller klagomål > 0,1 %
   (Resends webhook för bounce/complaint).
3. **Första mejlet utan HTML och utan bild**, bara ren text. Logotypen kan
   komma i uppföljningen eller i svaret.
4. **DMARC-rapporter** (`rua=mailto:…`) så att vi ser placering och fel.

## 2. Mottagaren och erbjudandet

- **De flesta Iris-leads går till info@/kontakt@** (regel 10 och 13 tillåter
  det). En gemensam brevlåda läses av den som svarar på kundfrågor, inte av
  den som köper verktyg. Mejlet måste överleva att vidarebefordras, och det
  gör det sällan.
- **Erbjudandet ber om ett köpbeslut direkt.** "Svara 'pilot' så håller vi
  en plats" och "50 % rabatt första året" förutsätter att mottagaren redan
  vill ha produkten. En rabatt är ett skäl att köpa *nu* för den som redan
  vill köpa, inte ett skäl att bry sig. Det saknas något som gör
  mottagaren nyfiken eller visar att det fungerar.
- **"Vi tar just nu in 20 företag i en pilot"** står i hundratals mejl. Den
  som får två sådana (eller googlar) ser att knappheten inte stämmer. Den
  sänker förtroendet och kan dessutom vara vilseledande marknadsföring om
  platserna inte faktiskt är 20.
- **Inget bevis.** Ingen kund, ingen siffra från verkligheten, inget namn.
  Snajp är okänt för mottagaren, och "AI-agent" läser som ett av tio
  liknande mejl i veckan.
- **Uppföljningarna** är alltid utkast som en människa ska godkänna
  (regel 17). Har de inte godkänts har mottagarna bara fått ett mejl. I
  kalla kampanjer kommer ofta hälften av svaren på uppföljning 1–2. Värt
  att kontrollera i Leads › Utkast hur många uppföljningar som faktiskt gått.

**Åtgärder:**

1. **Byt mål med första mejlet: från "köp" till "svara".** En
   intressebaserad avslutning med ett konkret, gratis resultat:
   - Supportagenten: "Jag lät agenten läsa er webbplats och svara på tre
     frågor era kunder sannolikt ställer. Vill ni se svaren?"
   - Kvittohanteraren: behåll "fem kvitton gratis", den är bäst av de tre.
   - Iris: "Jag har tre bolag i [ort] som matchar era kunder. Ska jag skicka
     namnen?" (det kan Iris faktiskt leverera, och det är beviset).

   Det kräver att **regeln "aldrig en fråga i slutet"**
   (`agent-core/prompts/leads-erbjudanden.md`) ändras, vilket är Antons
   beslut. Det är den enskilt största textändringen.
2. **Spara pilotrabatten till svaret**, när mottagaren visat intresse.
3. **Ta bort "20 företag" ur villkoren** om det inte är en verklig gräns som
   hålls.
4. **Ett bevis per mejl** när det finns: en pilotkund, en siffra
   ("svarade på 70 % av frågorna utan människa hos X").
5. **Prioritera personliga adresser** i fördelningen och skriv mejlet så
   att det går att vidarebefordra när det går till info@ ("Om det är någon
   annan än du som har hand om …").

## 3. Texten

Facit (`docs/UTKASTKEDJAN-REFERENS-2026-10-16.md`) är välskrivet: kort,
sakligt, ingen slentrian, inga säljord. Svagheterna är strukturella:

- **Ingången speglar bolagets egen säljtext tillbaka till dem.** "Ni hjälper
  era kunder att styra ekonomin i byggprojekt" berättar inget mottagaren inte
  vet, och mottagaren känner igen sin egen hemsida. Det läser som
  maskinpersonalisering. Starkare: något vi *har observerat* som de inte
  skrivit själva, t.ex. "ni svarar på frågor om X i er FAQ men inte om Y",
  "ni har tre lediga tjänster ute", "ni öppnade i Mölndal i våras".
- **Samma tre-styckesmall i alla 600 mejl** (ingång, produkt + villkor,
  "Svara 'pilot'"). Varierade ord, samma rörelse, och spamfilter och
  människor känner igen en mall på strukturen.
- **Foten är lika lång som mejlet.** Fyra meningar GDPR-text ("din adress
  är hämtad ur offentliga företagsuppgifter …") plus avregistreringslänk
  gör att varje mejl ser ut som ett massutskick. Art. 14-texten krävs bara
  vid en personlig adress (send_guard regel 4). Till info@ räcker
  avsändare, org.nr och en kort avregistreringsrad.
- **Ämnesraderna** ("Byggekonomin och kvittona", "Relationen med
  föreningen") är abstrakta. Det som får folk att öppna är något som ser ut
  att komma från en människa: kort, specifikt, gärna i gemener ("fråga om
  era kvitton").

**Åtgärder:** observation i stället för spegling i ingången, kortare fot
till funktionsadresser, ämnesrader som en människa skriver, och mindre
mall (variera även styckeantalet: ibland två meningar räcker).

## Mät först (innan något byggs)

1. **Resends instrumentpanel:** studs, klagomål och leveranser per dag för
   de 600. Hög studs → adresskvaliteten. Klagomål → stoppa direkt.
2. **Placeringstest:** skicka facit-mejlet till mail-tester.com och några
   testlådor (Gmail, Outlook.com, M365) och se var det hamnar, med och utan
   logotyp.
3. **Fördela svaren på adresstyp:** personlig adress kontra info@, och
   Iris kontra Supportagent kontra Kvittohanterare.
4. **Räkna uppföljningar som gått** jämfört med som väntar på godkännande.

## Prioritet

| # | Åtgärd | Effekt | Kräver |
|---|---|---|---|
| 1 | Mät leveransen (Resend + placeringstest) | avgör allt annat | 30 min, Sebbe |
| 2 | Pausa volymen, separat utskicksdomän, flack kurva, ren text | hög | kod + DNS |
| 3 | Intressebaserad avslutning med gratis resultat, rabatten till svaret | hög | **Antons beslut** (regeln "aldrig en fråga") |
| 4 | Ta bort "20 företag" om den inte är verklig | förtroende, juridik | Antons beslut |
| 5 | Kort fot till funktionsadresser | medel | kod (send_guard tillåter det) |
| 6 | Observation i ingången, mindre mall, mänskliga ämnesrader | medel | skrivstil + facit (Antons ja) |
| 7 | Godkänn och skicka uppföljningar | medel | granskning |
