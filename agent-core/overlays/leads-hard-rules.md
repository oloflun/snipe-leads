# Hårda regler för leads-utskick (G4)

Dessa regler ÅSIDOSÄTTER skillens standardbeteende där de krockar.

- Producera ALDRIG LinkedIn-kopia eller anslutningsmeddelande, oavsett vad
  skillen säger om att alltid inkludera det. E-post är enda kanalen. Finns
  ingen verifierad e-postadress: eskalera, föreslå inte LinkedIn som fallback.
- Ren text. Aldrig markdown, asterisker, fetstil eller punktlistor.
- Skriv på det språk som anges under "Språkläge" i ärendekontexten. Det är
  trådens faktiska tillstånd, inte ett antagande — härled det aldrig ur
  bolagsnamn, webbplats eller en gissning om mottagaren.

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
