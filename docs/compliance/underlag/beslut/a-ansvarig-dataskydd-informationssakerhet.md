## [FYLL: datum] (Anton) — Ansvarig för dataskydd, informationssäkerhet och AI-styrning

**Bakgrund.** Snajp har två personer med full åtkomst till kod, drift och kunddata, men ingen skriven ansvarsfördelning. I praktiken bedömer Anton incidenter och kontaktar kunder (`INCIDENT_RESPONSE.md` §1 och §5), och han är ensam code owner på `main`. Sebbes roll, befogenheter och avtal är inte dokumenterade. Kundmejl gick till TypeSafe utan att någon beslutat det, eftersom ingen hade ansvaret för att stoppa det. Kunderna kräver ett biträdesavtal som visar vem som svarar för säkerheten.

**Beslut.**
1. Anton är ansvarig för dataskydd, informationssäkerhet och AI-styrning hos Snajp. Han godkänner policyer, risker, undantag, nya leverantörer och modeller, bedömer incidenter och är kontaktperson mot kunder och IMY.
2. Sebbe är medutvecklare. Hans formella ställning är [FYLL: anställd / uppdragstagare / delägare], enligt avtal daterat [FYLL].
3. Sebbe får:
   - utveckla och driftsätta till `development`, och lämna PR mot `main` som Anton granskar;
   - stoppa en pågående skada utan att fråga: rotera en nyckel, stänga av en tjänst eller en brytare, dra in en åtkomst;
   - granska Antons egna PR:er innan Anton mergar dem (P19);
   - vara systemägare för [FYLL: Iris och Jev / inget] enligt P27 avsnitt 5.
4. Sebbe får inte ensam: slå på en ny leverantör eller modell som får kunddata, ändra en autonominivås standard, bedöma om en händelse är en personuppgiftsincident, eller kontakta IMY.
5. Ersättare när Anton är borta mer än två arbetsdagar: [FYLL: Sebbe / ingen]. Utan ersättare fattas inga säkerhetsbeslut under tiden, utom att stoppa en pågående incident.
6. Rollerna bekräftas varje år och när någon börjar eller slutar. Sebbe bekräftar sin roll med signatur nedan.

**I praktiken.** Det här är den post som P07 (Roller), P27 (avsnitt 5) och G01 hänvisar till. Från datumet nedan har varje beslut om leverantör, modell eller incident en namngiven ägare. Ingen kod ändras. Det som fortfarande saknas är Sebbes skriftliga avtal med sekretess (A.6.2, A.6.5, A.6.6), som inte ersätts av den här posten.

Krav: GDPR AG-1; ISO 27001 5.3, A.5.2; ISO 42001 5.3, A.3.2.

Datum: ____________________

Anton, ansvarig: ____________________

Sebbe, bekräftar sin roll: ____________________
