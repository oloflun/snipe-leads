/**
 * Notisernas former och standardvärden — utan "use server".
 *
 * Delningen är inte kosmetisk. En `"use server"`-modul får ENDAST exportera
 * asynkrona funktioner; en `export const STANDARD` där fäller bygget med
 * "Only async functions are allowed to be exported in a use server file". Och
 * växeln i inställningarna är en klientkomponent som behöver just det värdet,
 * eftersom den som aldrig svarat på frågan saknar rad i databasen.
 *
 * Här bor alltså formen. Skrivningarna bor i lib/actions/notiser.ts.
 */

export type Notishandelse = "lead" | "escalation";

export const NOTISHANDELSER: readonly Notishandelse[] = ["lead", "escalation"] as const;

export type Notisinstallningar = {
  /** Huvudströmbrytaren. Av = inga notismejl alls. */
  epost: boolean;
  handelser: Notishandelse[];
};

/**
 * Speglar kolumndefaultarna i migration 043. Ändra båda eller ingen.
 *
 * Dubbleringen är avsiktlig: den som aldrig svarat på frågan har ingen rad,
 * och utan ett värde i koden hade formuläret ritat "av" för någon som i
 * praktiken får notiser — alltså visat motsatsen till vad systemet gör.
 */
export const STANDARD: Notisinstallningar = {
  epost: true,
  handelser: ["lead", "escalation"]
};

/**
 * Filtrerar mot den kända listan i stället för att casta.
 *
 * Check-villkoret i databasen håller redan kolumnen ren, men en rad som
 * skrivits innan ett värde togs bort ur listan skulle annars renderas som en
 * kryssruta utan etikett — och en ruta som inte går att beskriva går inte att
 * svara på.
 */
export function tillHandelser(varden: readonly string[]): Notishandelse[] {
  return NOTISHANDELSER.filter((h) => varden.includes(h));
}
