# Förslag till Anton: Iris-mejlen öppnar med erbjudandet (2026-10-24)

Sebbes beställning 2026-10-24: "Förbättra utskicken, texten. De ska sälja in
vår produkt bra, konkret, kort och tydligt. Vi måste få mer svar och bli
trovärdiga och attraktiva." Och: "Bygg om Iris-mejlen så att de öppnar med
det konkreta erbjudandet (vilka kunder Iris tar fram åt just dem) … och skriv
ihop det för Anton, inklusive att ta bort pilotens 20 platser."

Allt nedan körs i **development** sedan commit `7508326`. Inget av det är i
main. Det ändrar den form som facit 2026-10-16 (INV-LEADS-UTKAST-002) bygger på,
och därför behövs ditt ja innan det släpps.

## Varför

- **Svaren.** Omkring 600 utskick gav 2 mänskliga svar, båda nej, och 7 autosvar
  ([diagnosen](UTSKICK-SVARSFREKVENS-DIAGNOS-2026-10-24.md)). Största delen är
  troligen leveransen, som är rättad separat: ren text, flack volym och stopp
  vid studs och klagomål. Texten bar också svagheter.
- **Löftesingången fungerar inte för Iris.** Ett Iris-mejl har bara ett moment,
  "hitta nästa kund". Att knyta bolagets löfte till det gav samma konstlade
  mening i mejl efter mejl. I två provvarv 2026-10-24 med skärpta regler och
  grind stod "kräver att ni kan fokusera på varje projekt, inte på att hitta
  nästa" i två av fem mejl båda gångerna, efter två omskrivningsvarv. Det går
  inte att lösa med fler regler i prompten.
- **Det starkaste ett Iris-mejl kan öppna med är det konkreta erbjudandet:**
  vilka kunder Iris tar fram åt just dem, och var.

## Formen (bara när Snajp säljer Iris)

1. **Erbjudandet först:** Iris tar fram [antal ur villkoren] [deras kundtyp ur
   sajten] i [deras ort], med kontaktperson och färdigt första mejl.
2. **Varför just de,** i en mening ur deras sajt.
3. **Resten av villkoren,** och meningen att mejlet självt är skrivet av Iris
   och läst av oss före utskick.
4. **Handlingen,** sist och ensam.

Ämnesraden är kundtypen och orten ("bostadsrättsföreningar i Västra Götaland").
Supportagentens mejl och kundernas egna produkter skrivs som förut, och facit
2026-10-16 passerar oförändrat i testerna.

Kod: `_IRIS_FORM` och `erbjudande_forst` i `app/agent/leads_research_v2.py`.
Undantagen i grinden heter `_ERBJUDANDE_FORST_UNDANTAG`: varje Iris-mejl öppnar
med erbjudandets ord, som handlingen redan gör.

## Före och efter (verkliga utkast ur Snajps kö i development, anonymiserade)

**Gratisprov, före:**
> Hej,
>
> Hur hinner ni hitta nästa företag att köpa en lastbil av, eller sälja en till, när varje affär kräver full uppmärksamhet för att gå i lås?
>
> Vår agent Iris hittar nya företagskunder åt er. Ni får fem kvalificerade leads i er region, med kontaktperson och ett färdigt första mejl till var och en, helt utan kostnad eller åtaganden.
>
> Svara "ja" på det här mejlet, så kommer de inom två arbetsdagar.

**Gratisprov, efter.** Ämne: *bostadsrättsföreningar i Västra Götaland*
> Hej [förnamn],
>
> Iris kan ta fram fem bostadsrättsföreningar eller företag i Västra Götaland som behöver fasadrenovering, fönsterbyte eller andra byggtjänster, med kontaktperson och ett färdigt första mejl till var och en. Det är helt utan kostnad och binder dig inte till något.
>
> Du servar alla kundkategorier i Västra Götaland med entreprenader och konsulttjänster. […]
>
> Svara "ja" på mejlet, så skickar vi de fem inom två arbetsdagar.

**Gratisprov, efter.** Ämne: *lastbilshandlare i Göteborg*
> Hej,
>
> Iris kan ta fram fem lastbilshandlare i Göteborg som söker lastbilar, med kontaktperson och ett färdigt första mejl till var och en. […]
>
> Detta erbjudande är helt utan kostnad och binder er inte till något. Det här mejlet är skrivet av Iris, som hittade er och läste er webbplats, och vi läste det innan det skickades.
>
> Svara "ja" på mejlet, så skickar vi de fem inom två arbetsdagar.

## Vad provet visar som inte är bra än

Fyra provvarv på fem leads vardera. Det fjärde med Iris-formen gav:

- **Gratisprovet blir bäst:** konkret, under 90 ord och utan påhitt.
- **Garantin driver:** "Iris tar fram **tio** byggföretag …" står inte i
  villkoren, som lovar tio kunddialoger, inte tio företag. Kundtypen blev
  bolagets egen bransch, och mejlet blev 111 ord.
- **Piloten blir lång:** 102–105 ord.
- **Beviset skrivs ibland om:** en gång blev det "Iris … är byggd för att hitta
  nya kunder till företag som ditt", vilket är utfyllnad och en mallfras.

Grinden fäller nu "Iris har hittat" (de tas fram efter ett ja), "Vi såg att",
"kan hjälpa er att", säljklyschor, "effektivt" och abstrakta ämnesrader.
Formen säger att kundtypen är deras kunder, inte företag som liknar dem själva.

## Beslut som behövs från dig

1. **Iris-formen,** att Iris-mejlen öppnar med erbjudandet. Den avviker från
   strukturen i facit 2026-10-16. Ja betyder att den släpps till main med nästa
   release och att ett nytt Iris-facit tas fram ur gratisprov-mejlen.
2. **Pilotens 20 platser bort.** Samma knapphet stod i hundratals mejl, och den
   som fick två såg att den inte stämde. Nytt villkor (i development):
   "I piloten för Iris sätter vi upp varje företag personligen.
   Pilotföretagen får 50 % rabatt första året om de vill fortsätta, och 25 % så
   länge de stannar. Handling: svara 'pilot' på mejlet, så sätter vi upp Iris
   åt er."
3. **Gratisprovet som Iris enda (eller tyngsta) erbjudande.** Ditt beslut
   2026-10-10 var tre lika viktade. Provet visar att garantin och piloten ger
   längre mejl och att garantins siffror driver. Gratisprovet är dessutom det
   enda där mottagaren får ett resultat innan hen bestämt något.
4. **Beviset i Iris villkor:** "Det här mejlet är skrivet av Iris, som hittade
   er och läste er webbplats, och vi läste det innan det skickades." Det är
   sant (en människa godkänner varje utskick). Säg till om du hellre vill att
   mejlet inte nämner AI.

## Hur det släpps

- Villkoren och Iris-instruktionen ligger i `scripts/snajp_malgrupp.py` och
  körs med `--env development` (gjort) eller `--env main --apply` efter ditt ja.
- Koden följer med nästa release `development` → `main`.
- Släpp texten först när leveransen är på plats i main: migration 113 och
  Resend-webhooken. Annars mäter vi texten genom samma skräpfilter som förut.
