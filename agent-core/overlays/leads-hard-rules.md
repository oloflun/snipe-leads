# Hårda regler för leads-utskick (G4)

Dessa regler ÅSIDOSÄTTER skillens standardbeteende där de krockar.

- Producera ALDRIG LinkedIn-kopia eller anslutningsmeddelande, oavsett vad
  skillen säger om att alltid inkludera det. E-post är enda kanalen. Finns
  ingen verifierad e-postadress: eskalera, föreslå inte LinkedIn som fallback.
- Ren text. Aldrig markdown, asterisker, fetstil eller punktlistor.
- Skriv på det språk som anges under "Språkläge" i ärendekontexten. Det är
  trådens faktiska tillstånd, inte ett antagande — härled det aldrig ur
  bolagsnamn, webbplats eller en gissning om mottagaren.

## Tonläge — fyra uttryckliga förbud (DEL 2.4)

`PROJECT_KNOWLEDGE.md` § Voice säger svenskt, konkret, lågmält. Det är en
riktning. Nedan står de fyra sakerna som ALDRIG får förekomma, därför att en
riktning inte går att kontrollera men ett förbud gör det:

- Skriv ALDRIG "Hoppas detta mejl finner dig väl" eller någon variant av den.
  Frasen är en direktöversättning av "I hope this email finds you well" och
  läses i Sverige som ett maskinskrivet mejl innan mottagaren hunnit till
  andra raden.
- ALDRIG utropstecken i ämnesraden. Ett utropstecken där är den enskilt
  starkaste skräppostsignalen i svenska inkorgar.
- Hitta ALDRIG på siffror om mottagarens verksamhet — omsättning, antal
  anställda, tillväxttal, marknadsandel. Står talet inte i researchunderlaget
  existerar det inte. Ett påhittat tal som råkar vara fel är det snabbaste
  sättet att förlora affären; ett som råkar vara rätt är fortfarande en
  gissning vi inte kan stå för.
- Påstå ALDRIG tidigare kontakt som inte skett. Inget "som vi pratade om",
  "när vi hördes senast" eller "jag följer upp mitt förra mejl" om det inte
  finns i tråden.

## Evidens före antagande (ur skarpa körningar 2026-08-09)

Tre regler till, födda ur faktiska utkast som passerade allt utom en
människas blick:

- **Gissa aldrig om mottagarens verksamhet.** Orden "troligen", "brukar",
  "antagligen", "borde", "säkert", "lär" och "som de flesta" är förbjudna i
  påståenden om mottagaren. Researchen har läst deras egna sidor — använd det
  den faktiskt såg, ordagrant eller nära. Ett skarpt utkast skrev "era
  vanligaste kundfrågor handlar troligen om leverans" till ett bolag vars
  sajt researchen just skrapat: gissningen raderade researchens hela värde.
- **Ämnesraden bär något SOM ÄR DERAS.** Ett konkret ord eller faktum ur
  researchen om mottagaren — deras egen formulering slår vår kategori. Ett
  skarpt utkast satte ämnesraden "supportagenten": vår produktkategori, noll
  skäl att öppna. Samma körning hade "365 dagars fri retur" i brödtexten —
  det var ämnesraden.
- **EN uppmaning per mejl.** Ett utkast bad om både pilot och demo — två
  dörrar är ett val, ett val är friktion, friktion är tystnad. Välj den
  minsta uppmaningen och stryk den andra.
- **En referens bär sitt "varför" i samma mening.** Nämner du en kund eller
  ett case (som finns i underlaget) ska samma mening säga vad det betyder
  för MOTTAGAREN — "i drift hos Livrustning" ensamt är ett namn utan
  innehåll; "i drift hos Livrustning, som får samma sorts återkommande
  frågor om garantier som ni" är ett argument.

> Overlays laddas ordagrant, utan `.format()`. Därför står regeln här och
> VÄRDET (`sv` / `en_confirmed`) i ärendekontexten: en overlay som behövde
> interpoleras hade gjort varje `{` i vilken overlay som helst till en
> krasch, och kördata hör ändå inte hemma i ett hashat instruktionslager.

## Varför LinkedIn-förbudet står här och inte i skillen

`sa:draft-outreach` producerar som standard även LinkedIn-kopia ("Copy for
LinkedIn (always)", SKILL.md rad 40). Det krockar med proveniensgrinden
(INV-DATA-002), som tillåter LinkedIn enbart som verifieringskälla — aldrig
som kanal.

Rätt åtgärd är den här overlayen, inte en redigering av `sa:draft-outreach`.
Skillen är vendorad från uppströms; redigerar vi den divergerar vår kopia och
nästa re-vendoring skriver antingen över ändringen eller ger en konflikt som
ingen minns orsaken till. Overlayen ligger utanför `agent-core/skills/`,
träffas inte av INV-SKILL-005, och kan ändras fritt i en PR.
