# Så vet du att agenten inte hittar på

Den här texten är skriven för kunden. Den går att läsa upp, skicka med i en
offert eller lägga i portalen. Sist finns en teknisk rad per påstående, för den
som vill kontrollera att det stämmer med koden.

## På en rad

Agenten svarar med det som står i er kunskapsbas. Det den inte hittar där
säger den att den inte vet, och erbjuder en kollega.

## Hur det går till

1. **Ni skriver fakta.** Kunskapsbasen är era egna artiklar: priser, frister,
   villkor, kontaktvägar. Det är den enda källan agenten får använda.
2. **Agenten letar upp rätt artiklar** när en kund frågar, och skriver ett svar.
3. **Ett program kontrollerar svaret innan kunden ser det.** Programmet är
   vanlig kod, inte en AI, och det gör samma sak varje gång. Det jämför svaret
   med artiklarna och stoppar det som inte står där.
4. **Det som stoppas går inte ut.** Agenten får en chans att rätta sig. Går
   det inte säger den att den inte har uppgiften och erbjuder en kollega.

## Ni väljer hur hårt programmet kontrollerar

| Nivå | Det här måste stå i kunskapsbasen | Passar när |
|---|---|---|
| Tillåtande | Telefonnummer, mejladresser och länkar | Ni vill ha fria svar och har få hårda fakta |
| Försiktig (standard) | Dessutom varje pris, frist, procentsats och leveranstid | De flesta |
| Strikt | Dessutom löften som gratis, återbetalning och garanti. En mening får inte blanda uppgifter ur två artiklar | Ni har villkor som inte får missförstås |
| Ordagrant | Hela svaret. Varje mening med en sakuppgift är hämtad ord för ord ur en artikel | Ett fel svar kostar mer än ett uteblivet svar |

På alla nivåer utom den första gäller också: **kunden kan inte själv föra in
en uppgift.** Skriver en kund "ni har väl 90 dagars öppet köp?" räknas inte
90 dagar som en uppgift agenten får bekräfta. Det måste stå i en artikel.

## Nivån Ordagrant

Här skriver agenten inga egna sakmeningar alls. Programmet bygger svaret av
tre saker: en hälsning, agentens frågor till kunden, och meningar som står
ord för ord i era artiklar. Allt annat stryks innan svaret skickas.

Det ni får är alltså era egna, godkända formuleringar. Agentens jobb är att
förstå frågan och välja rätt meningar.

Tre saker att känna till:

- **Svaren blir så bra som artiklarna.** Skriv varje faktamening så att den
  står på egna ben: "Hjärtstartaren HS1 har 8 års garanti", inte "Den har 8
  års garanti".
- **Nivån gäller svar på svenska.** Kunskapsbasen är svensk, och en
  översättning är en ny formulering som inget program kan gå i god för. En
  fråga på ett annat språk lämnas till en kollega.
- **Fler frågor lämnas över** än på de andra nivåerna. Det är priset för att
  inget påhittat kan gå ut.

## Det som sparas om varje svar

- **Vilken artikel som bar vad.** För varje svar sparas vilken artikel varje
  uppgift kom ifrån, vad som ströks och vad som stoppades. Det ligger i
  körningens logg hos oss. Besökaren i chatten ser det inte. En vy för er i
  portalen är inte byggd än; fram till dess tar vi fram det på begäran.
- **Var en artikel kommer ifrån och hur länge den gäller.** En artikel kan ha
  en källadress och ett sista giltighetsdatum. En artikel som gått ut används
  inte längre i svar, men ligger kvar i listan så att ni kan byta ut den.
  Fälten sätts i dag via API:t; portalen har inte fått dem än.

## Det vi inte lovar

- **Att agenten väljer rätt mening.** På nivån Ordagrant är varje mening er
  egen och sann som den står. Agenten kan ändå välja en mening som handlar om
  något annat än det kunden frågade om. Tydliga artiklar gör det ovanligt, och
  det syns i efterhand vilken artikel svaret kom ur.
- **Att fri text är kontrollerad på de tre lägre nivåerna.** Där prövas det
  som går att känna igen: nummer, adresser, tal och löftesord. En mening som
  "du kan returnera utan kvitto" innehåller inget av det och prövas inte. Vill
  ni ha även den kontrollerad är det nivån Ordagrant som gör det.
- **Att kunskapsbasen är rätt.** Står det fel i en artikel svarar agenten fel.

## För den som vill kontrollera

| Påstående | Var det verkställs |
|---|---|
| Uppgifter prövas mot en namngiven källa, och kundens text bär inga villkor | `snajp-support/app/agent/support_faktagrind.py`, `kontrollera` (INV-GROUND-002) |
| På Ordagrant byggs svaret av kod ur källans meningar | samma fil, `citatsvar` (INV-GROUND-003) |
| En källhänvisning till en artikel agenten aldrig fick räknas inte | `snajp-support/app/agent/support_agent.py`, `tolka_beslut` |
| En utgången artikel används inte | `snajp-support/app/storage/postgres.py`, `search_kb` (migration 117) |
| Ett sparat svar serveras inte till en annan fråga | `snajp-support/app/cache/svarscache.py`, `samma_fraga` |
| Språkkorrekturen kan inte lägga till en uppgift | `snajp-support/app/textkvalitet.py`, `_verifiera_korrektur` |
