# Support Objection Library (svenska)

Skilt från `mk:sales-enablement/references/objection-library.md`. Det
biblioteket möter någon som INTE köpt än ("för dyrt", "ingen budget", "vi
använder X"). Det här biblioteket möter någon som REDAN köpt och är besviken
— annan situation, andra svar. Se plan Del A2.

Varje kategori följer svarsramverket från SKILL.md: bekräfta → fastställ →
vad vi gör → när → vem äger det. Inget svar nedan är en färdig fras att
citera ordagrant — det är strukturen ett grundat svar ska följa, fyllt med
fakta ur ärendet och kundens retentionsplaybook.

## 1. Brutet löfte — "Ni sa att det skulle fungera med X"

**Vad som egentligen pågår:** Förväntansglapp — ofta ett sälj- eller
marknadsföringslöfte som inte matchar produktens faktiska begränsningar,
sällan ett supportfel i sig.

**Bekräfta:** Att det finns ett glapp mellan vad kunden förväntade sig och
vad de fick, utan att i förväg avgöra vems "fel" det är.

**Fastställ:** Vad exakt sades (om kunden kan citera var/när), och vad
produkten faktiskt gör idag. Fråga inte "är du säker på att vi sa det" —
utgå från kundens version.

**Vad vi gör:** Om KB/retentionsplaybooken har en dokumenterad lösning eller
ett godkänt gottgörelseerbjudande för den här typen av glapp: erbjud det. Om
inte: eskalera — ett brutet löfte kan kräva ett beslut ingen agent har
mandat att ta (kompensation, avtalsändring).

**Vem äger det:** Om det eskaleras, säg vem som tar över och att kunden inte
behöver upprepa sig.

## 2. Upprepat fel — "Det här är tredje gången"

**Vad som egentligen pågår:** Förtroendeerosion. Varje återfall kostar mer
förtroende än det förra, oavsett hur litet felet tekniskt sett är.

**Bekräfta:** Att detta INTE är kundens första kontakt om samma problem —
slå upp historiken (`cs:customer-research`) innan du svarar, inte efter.

**Fastställ:** Vad som gjordes de förra gångerna och varför problemet är
tillbaka. Om du inte vet varför det återkommer: säg det rakt i stället för
att gissa en orsak.

**Vad vi gör:** Ett tredje (eller senare) återfall av samma problem
eskaleras som regel — mönstret i sig är signalen, inte allvarlighetsgraden
i detta enskilda tillfälle.

**Vem äger det:** Namnge en specifik mottagare, inte "vi tittar på det".

## 3. Tvivel på värdet — "Vi använder det knappt"

**Vad som egentligen pågår:** Aktiveringsmiss, inte ett produktfel. Kunden
har inte hittat vägen till värdet, inte att värdet saknas.

**Bekräfta:** Att lågt nyttjande är en giltig anledning att ifrågasätta
kostnaden — bagatellisera inte det.

**Fastställ:** Vilka delar av produkten kunden faktiskt använder idag, om
möjligt via kontot/historiken, inte genom att fråga kunden att bevisa det.

**Vad vi gör:** Om retentionsplaybooken har en aktiveringsåtgärd (t.ex.
en introduktionsgenomgång) för den här situationen: erbjud den. Detta är
KATEGORIN där en pausmånad eller en genomgång ofta finns i playbooken
(jämför `mk:churn-prevention`s "Pause subscription" / "Feature unlock" —
men bara om just DEN HÄR kundens playbook faktiskt listar det).

**Vem äger det:** Om åtgärden kräver schemaläggning (t.ex. en genomgång):
var tydlig med att TIDPUNKTEN bestäms i nästa steg, inte nu (regel 4).

## 4. Pris mot värde — "För dyrt för vad vi får ut"

**Vad som egentligen pågår:** Värdeuppfattning, inte nödvändigtvis fel pris.
Kopplar till värdeekvationens fyra spakar (se `mk:offers` och plan Del H) —
kunden upplever att `Drömutfall × Sannolikhet` inte överväger
`Tidsfördröjning × Möda`.

**Bekräfta:** Att prisfrågan är legitim, utan att direkt gå i försvar för
priset.

**Fastställ:** Vad kunden jämför mot — ett konkurrenterbjudande, en intern
budget, eller en allmän känsla. Detta avgör om något i playbooken faktiskt
adresserar det.

**Vad vi gör:** Ett prisrelaterat erbjudande (rabatt, nedgradering) finns
ENDAST om retentionsplaybooken listar det för den här kundens segment. Utan
det: eskalera — pris är ett beslut agenten aldrig tar själv.

**Vem äger det:** Var tydlig med att prisbeslut tas av en människa, inte av
dig, oavsett hur rimligt kundens argument låter.

## 5. Ansträngning — "Det tar för lång tid att få hjälp"

**Vad som egentligen pågår:** Vår egen process är problemet, inte kunden.

**Bekräfta:** Väntetiden utan att förklara bort den ("vi har haft mycket att
göra" hjälper inte kunden).

**Fastställ:** Hur länge kunden faktiskt väntat, enligt ärendehistoriken.

**Vad vi gör:** Om det här samtalet KAN lösa saken nu: gör det, utan att
först fråga om lov. Om det inte kan: var ärlig om det i stället för att
antyda att det går snabbare än det gör (regel 4).

**Vem äger det:** Om det krävt eskalering tidigare utan uppföljning, säg
konkret vad som är annorlunda den här gången.

## 6. Ultimatum — "Fixa detta annars säger vi upp"

**Vad som egentligen pågår:** Verklig uppsägningsrisk. **Går alltid till
människa** (regel 3) — det här är den enda kategorin utan ett
agent-hanterat lägre steg.

**Bekräfta:** Att kunden är beredd att lämna om det inte löses — ta det på
allvar, argumentera inte emot det.

**Fastställ:** Vad exakt kunden kräver för att stanna, så eskaleringen
kommer med en konkret fråga, inte bara "kunden är arg".

**Vad vi gör:** `escalate_to_human` med anledningen "ultimatum" oavsett hur
enkelt kravet ser ut att uppfylla. Agenten förhandlar aldrig sitt eget
motbud.

**Vem äger det:** Säg till kunden att en människa tar över specifikt för
det här beslutet, med en tidsram för när de hör något (inte en tidpunkt för
LÖSNINGEN — bara för nästa kontakt, se regel 4).
