/**
 * Felkoden för spärren mot upprepade inloggningsförsök. Egen fil utan importer,
 * så att inloggningsformuläret (klientkod) kan läsa den utan att dra med
 * `node:crypto` från `lib/auth/inloggningsregler.ts`. Koden säger bara "vänta",
 * aldrig om kontot finns.
 */
export const SPARRKOD = "for_manga_forsok";
