/**
 * Felkoden för spärren mot upprepade inloggningsförsök. Egen fil utan importer,
 * så att inloggningsformuläret (klientkod) kan läsa den utan att dra med
 * `node:crypto` från `lib/auth/inloggningsregler.ts`. Koden säger bara "vänta",
 * aldrig om kontot finns.
 */
export const SPARRKOD = "for_manga_forsok";

/**
 * Tvåstegsverifieringen (migration 128). Ges BARA efter ett rätt lösenord, så
 * de avslöjar inget om vilka adresser som finns.
 *  - `tvafaktor_kravs`: lösenordet stämde, kontot har tvåfaktor, ingen kod gavs.
 *  - `tvafaktor_fel`: koden var fel eller redan använd.
 */
export const TVAFAKTOR_KRAVS = "tvafaktor_kravs";
export const TVAFAKTOR_FEL = "tvafaktor_fel";
