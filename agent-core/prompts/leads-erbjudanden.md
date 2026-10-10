# Erbjudanden i kalla mejl

> **Om filen:** Katalogen över erbjudanden som Iris kan bära i ett kallt mejl, ett avsnitt per erbjudande med nyckeln som rubrik. Koden (`app/leads/erbjudanden.py`) läser avsnitten, och kunden väljer vilka som är aktiva och skriver villkoren per produkt. Erbjudandet bär stycke 2 och 3 i skrivstilen (`leads-skrivstil.md`): vad mottagaren får och den enkla handlingen. Villkoren skrivs ALDRIG här: de står i kundens inställningar, ordagrant, och är det enda mejlet får lova. Omgjord 2026-10-10 efter Antons omgång 3: tre kärnerbjudanden i stället för sex (exempel: https://claude.ai/artifact/AvqAtFiVf7h3Rupe5E6Ryz). Grunden är Hormozis $100M Offers och $100M Leads, se `docs/hormozi-erbjudanden-2026-10-10.md`.

Gemensamt för alla erbjudanden:
- Grundkänslan: erbjudandet är skrivet just för dem, löser det som skaver i ingången och är för bra att ignorera. Kort, konkret och utan förklaringar av hur tekniken fungerar.
- Erbjudandet sägs med villkorens innehåll och siffror och inget annat. Står något inte under "Villkor för erbjudandet" i ärendet får det inte stå i mejlet, inte ens omskrivet.
- Ett erbjudande per mejl, och det gäller produkten mejlet handlar om.
- Mejlet slutar med villkorens handling (svara "ja", följ länken, vidarebefordra, svara så bokar vi), aldrig med en fråga.
- Sakligt, utan utropstecken och utan säljord ("unikt", "exklusivt", "missa inte").

## gratis_prov

**Namn:** Testa gratis
**Hävstång:** tidsfördröjning och upplevd sannolikhet. Mottagaren får ett färdigt resultat innan något är bestämt, och resultatet är beviset.
**Kräver villkor:** ja, per produkt: vad provet innehåller (till exempel fem kvalificerade leads med färdiga mejl, fem kvitton klara att ladda ned, eller en demolänk där de lägger in sina vanligaste frågor och villkor och testar själva) och handlingen som ger dem det.
**Så bär mejlet erbjudandet:** Efter meningen om vad agenten gör åt dem kommer provet, med villkorens antal och innehåll, och "utan kostnad". Sedan handlingen.
**Undvik:** att lova vad provet kommer att visa, och att kalla det "demo" eller "test" när villkoren beskriver ett färdigt resultat.

## garanti

**Namn:** Garanti
**Hävstång:** upplevd sannolikhet. Avsändaren tar risken: når de inte resultatet får de mer tid utan kostnad.
**Kräver villkor:** ja, per produkt: det utlovade resultatet med siffra och tidsram, vad som händer om det inte nås, och vad mottagaren ska ha gjort.
**Så bär mejlet erbjudandet:** En mening med löftet och siffran ("Vi lovar att …"), direkt följd av en mening om vad som händer annars. Båda med villkorens ord och siffror. Sedan handlingen.
**Undvik:** "garanterat", "100 %", och varje siffra eller tidsram som inte står i villkoren.

## pilot

**Namn:** Begränsad pilot
**Hävstång:** knapphet och pris. Ett fåtal platser, ett pris som inte erbjuds igen, och ett ärligt skäl till att platserna är få.
**Kräver villkor:** ja, per produkt: antalet platser, pilotpriset (till exempel rabatt första året och så länge de stannar) och skälet till att platserna är få.
**Så bär mejlet erbjudandet:** Säg vad agenten gör åt dem, sedan att platserna är få och varför, och pilotpriset med villkorens siffror. Sedan handlingen som håller en plats åt dem.
**Undvik:** "bara några platser kvar" eller andra uppgifter om hur många som är tagna, om de inte står i villkoren, och varje deadline som inte står där.
