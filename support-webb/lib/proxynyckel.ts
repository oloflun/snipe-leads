/**
 * Vems nyckel får ett anrop genom /api/ag?
 *
 * Ren funktion med flit: beslutet avgör vilken kunds data en begäran når, och
 * ska gå att pröva utan en server (lib/supportwebb-proxynyckel.test.ts i
 * roten). Inga importer, så att rotens testkörare kan läsa filen.
 *
 * Reglerna (Fas 0-fyndet H13, 2026-11-09):
 *
 * 1. En kundkaka som finns men inte håller (utgången, oläslig, pekar på en
 *    backend som inte är tillåten) ger ALDRIG den delade nyckeln. Förut föll
 *    den tyst dit, och kunden arbetade då i en annan kunds data.
 * 2. Utan kundkaka används miljöns delade nyckel bara bakom inloggningsväggen
 *    (AGENTSAJT_LOSEN) eller i lokal utveckling. En driftsatt sajt utan vägg
 *    gav annars den delade kundens data till vem som helst.
 */

export type Kundnyckel = { apiKey?: string; backendUrl?: string; utfardad?: number };

export type Nyckelval =
  | { slag: "kund"; nyckel: string; bas: string }
  | { slag: "delad" }
  | { slag: "avvisad"; skal: "kundsession" | "oppen" };

export function valjNyckel(indata: {
  /** Finns kundkakan i begäran, oavsett om den gick att läsa? */
  harKundkaka: boolean;
  /** Kakans innehåll, eller null när den inte gick att dekryptera. */
  kund: Kundnyckel | null;
  nu: number;
  maxAlderMs: number;
  tillatna: string[];
  /** Är inloggningsväggen på (AGENTSAJT_LOSEN satt)? */
  vaggPa: boolean;
  /** Driftsatt bygge (NODE_ENV=production)? */
  produktion: boolean;
}): Nyckelval {
  const { harKundkaka, kund, nu, maxAlderMs, tillatna, vaggPa, produktion } = indata;
  if (harKundkaka) {
    if (
      kund &&
      typeof kund.apiKey === "string" &&
      kund.apiKey.length > 0 &&
      typeof kund.backendUrl === "string" &&
      typeof kund.utfardad === "number" &&
      nu - kund.utfardad < maxAlderMs &&
      tillatna.includes(kund.backendUrl)
    ) {
      return { slag: "kund", nyckel: kund.apiKey, bas: kund.backendUrl };
    }
    return { slag: "avvisad", skal: "kundsession" };
  }
  if (produktion && !vaggPa) return { slag: "avvisad", skal: "oppen" };
  return { slag: "delad" };
}
