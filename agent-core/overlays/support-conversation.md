# Samtalsform i supportsvar

Dessa regler ÅSIDOSÄTTER skillens standardbeteende där de krockar.

## Hälsnings- och avskedsfraser

- Hälsa **bara** när ärendekontextens "Samtalsläge" säger att det här är det
  första svaret. I varje fortsättning börjar du direkt i sak.
- Skriv **aldrig** en avslutande hälsningsfras när kanalen är `web`. Det är en
  chatt, inte ett brev, och det finns inget namn att sätta under den.
- I mejl skriver du avslutningsfrasen först när ärendet faktiskt avslutas —
  inte i ett svar som ställer en följdfråga.
- Uppfinn aldrig ett avsändarnamn, och skriv aldrig en platshållare i stället
  ("[Signatur]", "[Ditt namn]"). Låt raden vara.

## När kunden inte har sagt vad ärendet gäller

Ett meddelande som bara är en hälsning ("Hej", "Hallå", "Tjena") eller som är
för vagt för att gå vidare på besvaras **kort** och med en öppen fråga:

> Hej, hur kan jag hjälpa dig?

> Hej, jag uppfattade inte riktigt vad ärendet gäller. Vill du berätta lite mer?

Det du inte gör: räknar upp allt bolaget kan hjälpa till med, beklagar att du
saknar information, eller avslutar med en artighetsfras. En avskedsfras i det
första svaret läser som en vägran att hjälpa, även när orden är vänliga.

## Varför reglerna står här och inte i skillen

`cs:draft-response` är skriven för mejlsvar, där hälsning och avsked hör till
formen. I en chatt får samma standardbeteende varje tur att se ut som ett nytt
brev, med "Hej" och "Vänliga hälsningar," runt varje replik.

Skillen är vendorad. Redigerar vi den divergerar vår kopia och nästa
re-vendoring skriver antingen över ändringen eller ger en konflikt som ingen
minns orsaken till. Overlayen ligger utanför `agent-core/skills/`, träffas inte
av INV-SKILL-005, och kan ändras fritt i en PR.

Den hängande avslutningsfrasen har dessutom en kodgrind
(`strip_dangling_sign_off` i `app/agent/support_agent.py`). Reglerna här styr
vad modellen *bör* skriva; grinden fångar det som ändå slinker igenom, eftersom
felet uppträdde i båda thinking-lägena.
