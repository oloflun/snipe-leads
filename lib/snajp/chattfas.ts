/**
 * Chattens väntläge: vad agenten gör just nu, och hur ofta svaret hämtas.
 *
 * Ett svar är fyra till fem modellanrop i följd. Backenden skriver skedet på
 * jobbet (snajp-support/app/api/chat.py, `fas`), och chattfönstret visar det
 * i stället för en stillastående rad. Skedena är fyra med flit: stegens
 * interna namn lämnar aldrig backenden.
 *
 * Inga importer, så att rotens testkörare kan läsa filen.
 */

type Tvasprakig = { sv: string; en: string };

const ALLMAN: Tvasprakig = { sv: "Agenten arbetar", en: "The agent is working" };

const FASER: Record<string, Tvasprakig> = {
  laser: { sv: "Läser din fråga", en: "Reading your question" },
  soker: { sv: "Söker efter svaret", en: "Looking for the answer" },
  skriver: { sv: "Skriver svaret", en: "Writing the reply" },
  kontrollerar: { sv: "Kontrollerar svaret", en: "Checking the reply" }
};

export function fastext(fas: string | null | undefined): Tvasprakig {
  return (fas && FASER[fas]) || ALLMAN;
}

/** Antal hämtningar innan chatten ger upp. */
export const POLL_FORSOK = 110;

/**
 * Pausen före hämtning nummer `forsok` (0-baserat), i millisekunder.
 *
 * Tätt de första fjorton sekunderna, där ett vanligt svar blir klart; förut
 * var pausen två sekunder redan efter fyra, och ett färdigt svar väntade i
 * snitt en sekund på att hämtas. Därefter glesare: ett svar som tar en minut
 * är ett svar med omförsök, och då gör en halv sekund ingen skillnad.
 * Sammanlagt väntar chatten lika länge som förut (omkring tre minuter).
 */
export function pollpaus(forsok: number): number {
  if (forsok < 20) return 700;
  if (forsok < 50) return 1500;
  return 2500;
}
