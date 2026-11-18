# Rutin: begäran från en registrerad (art. 15–21)

Gäller från: [FYLL: datum]. Handläggare: Anton. Ersättare: [FYLL]. Följer G04 (`ramverk/gdpr/policyer/04-…`).

## 1. Ta emot (samma arbetsdag)

- Begäran kommer till [FYLL: integritet@snajp.se]. Tills den brevlådan finns gäller `kontakt@snajp.se`. Kommer en begäran någon annanstans (Gmail-kontot, en chatt, ett svar på ett kallmejl) räknas den ändå från den dagen.
- Skriv en rad i begäransloggen (`loggar/begaranden.md`, mall i `b-begaranslogg.md`). Fristen räknas från dagen begäran kom in.
- Bekräfta mottagandet till avsändaren.

## 2. Ansvarig eller biträde?

| Uppgifterna gäller | Snajps roll | Gör så här |
|---|---|---|
| Snajps egna kallmejl, prospekt, demoförfrågningar, Snajps egna kunder och konton | **Ansvarig** | Handlägg enligt avsnitt 3–5 |
| Kundmejl, chattar, kvitton eller utskick som en kund gjort via Snajp | **Biträde** | Vidarebefordra till kunden inom [FYLL: antal; pub-avtalet 7.2 föreslår 2] arbetsdagar. Svara personen att begäran gått till kunden och vem det är. Svara inte i sak utan kundens instruktion. Utdrag eller radering på kundens begäran inom [FYLL: antal; 7.3 föreslår 10] dagar |

Är det oklart, handlägg båda delarna.

## 3. Kontrollera identiteten

Utdrag och svar skickas bara till den adress uppgifterna gäller. Kommer begäran från en annan adress: skicka en kontrollfråga till den registrerade adressen och vänta på svar. Begär inte mer uppgifter än som behövs; aldrig personnummer eller legitimation för en mejladress.

## 4. Sök, ta ut och radera

**Verktyget `scripts/gdpr_radera.py` har aldrig körts mot någon databas**, varken lokalt eller i drift, och ändringarna i det är inte committade. Kör det första gången mot den lokala stacken (`python scripts/lokal_stack.py --apply`) med en testadress innan det används på en verklig begäran. Det läser anslutningen ur `.env.deploy`.

| Steg | Kommando |
|---|---|
| Sök var adressen finns | `python scripts/gdpr_radera.py --env railway-main --epost <adress>` |
| Sök också i löptext (promptar, loggar, mejltexter) | lägg till `--fritext` |
| Registerutdrag (art. 15) och portabilitet (art. 20), som JSON | lägg till `--export` |
| Radera (art. 17) | `python scripts/gdpr_radera.py --env railway-main --epost <adress> --radera` (frågar efter adressen en gång till) |

- Utdraget skrivs till skärmen. Spara det i en fil bara för att skicka det, radera filen samma dag, och skriv överföringen i `loggar/overforingar.md` (P24).
- Visar sökningen "FEL: kolumn": radera inte. Kartan stämmer inte med schemat.
- Rättelse (art. 16): inget verktyg. Rätta fältet i adminytan; skriv vad som ändrades i loggen.
- Ett **konto** (`auth.users`) raderas inte av verktyget, och inget annat skript gör det heller. Det kräver en manuell åtgärd eller ny kod.

**Det verktyget inte raderar, och vad du gör:**

| Kopia | Hantering |
|---|---|
| Spärrlistan | Behålls med flit. Säg det i svaret |
| Kvitton (`bk_underlag`) | Kundens bokföringsunderlag. Begäran går till kunden |
| Raderna under "Kräver manuellt beslut" och träffarna i löptext (`agent_runs` m.fl.) | Anton beslutar per rad. Skriv beslutet i loggen |
| `development`-spegeln | Kör sökningen med `--env railway-development` efter nästa synk. Finns träffar kvar: radera där också |
| Redis hos Railway | Jobb och cache lever högst en timme. Vänta en timme |
| Gamla Redis Cloud | Har kvar cache tills databasen är raderad. Löses av brev e |
| Gamla Supabase | Får aldrig skrivas till (CLAUDE.md). Löses av att projektet raderas (brev d) |
| Säkerhetskopior hos Railway | Finns inte i dag. När de finns: nämn dem i svaret, och gör om raderingen efter en återställning |
| Resend | Mejlinnehåll och loggar ligger 30 dagar i USA. Enskilda mejl kan raderas via Resends support |
| GitHub Actions | Synkens logg sparas 14 dagar som artefakt |

## 5. Svara (inom en månad)

- Förlängning med högst två månader meddelas inom första månaden, med skäl.
- **Utdrag:** JSON-filen, vilka ändamål och mottagare som gäller (ur registerförteckningen), hur länge uppgifterna sparas, och rätten att klaga hos IMY.
- **Radering:** vad som raderades, vad som finns kvar och varför (spärrlistan, bokföring), och att kvarvarande kopior försvinner inom [FYLL] dagar.
- **Invändning mot kallmejl:** avregistrera adressen (se avsnitt 6) och bekräfta.
- Skriv svarsdatum och utfall i loggen.

## 6. Rätten till begränsning (art. 18), manuellt

Begränsning betyder att uppgifterna får lagras men inte användas, tills frågan är avgjord. Det finns ingen kod för det. Så här gör du utan kod:

1. Skriv begäran, skälet (art. 18.1 a–d) och slutdatum i begäransloggen.
2. Stoppa utskick: öppna avregistreringslänken i det senaste utskicket till adressen, eller låt personen klicka den. Adressen hamnar då på spärrlistan.
3. Lägg en anteckning på prospektet i Leads: "BEGRÄNSAD enligt art. 18, [datum], rör inte, se begäranslogg". Har leadet telefon, sätt utfallet "Kontakta inte" i återkopplingslistan.
4. Under tiden får ingen: exportera uppgifterna, lägga dem i en lista, köra research på bolaget, använda dem i ett utkast, eller radera dem (om personen behöver dem för ett rättsligt anspråk).
5. Meddela personen innan begränsningen hävs (art. 18.3).

**Kräver kod:** en flagga som stoppar all behandling av en person, så att leadskörningar, webbpoolen, synken till `development` och det kommande gallringsjobbet hoppar över raden. Utan den hänger rutinen på att någon läser anteckningen.
