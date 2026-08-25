/**
 * Teamet på /vart-team.
 *
 * ## Fälten är PLATSHÅLLARE, och det ska synas
 *
 * Namnen nedan är `[Namn Efternamn]`, inte påhittade personer. Det är ett
 * medvetet val och inte lättja: en uppfunnen medarbetare på en sida som ska
 * bygga förtroende är en lögn om vilka man köper av, och den sortens text
 * upptäcks sist av alla av den som skrev den.
 *
 * `arPlatshallare` i lib/bolag.ts känner igen dem på hakparentesen, precis som
 * bolagsuppgifterna. Skillnaden mot sidfoten är att här ska platshållaren
 * SYNAS: sidan är inte publicerbar förrän någon fyllt i den, och en tom sida
 * hade inte sagt vad som fattas. Sidan visar därför en tydlig notis så länge
 * något fält står kvar.
 *
 * Fyll i: byt ut texten, lägg fotot i public/images/team/ och peka `foto` dit.
 * Saknas fotot ritas en initialbubbla i stället — ingen trasig bildikon.
 */

export type Teammedlem = {
  /** Stabil nyckel för React och för ankare. Ändra inte när namnet fylls i. */
  id: string;
  namn: string;
  roll: string;
  bio: string;
  /** Sökväg under /public, eller null för initialbubbla. */
  foto: string | null;
};

export const TEAM: Teammedlem[] = [
  {
    id: "medlem-1",
    namn: "[Namn Efternamn]",
    roll: "[Roll]",
    bio: "[Kort bio: en mening om bakgrund och vad personen ansvarar för i Snajp.]",
    foto: null
  },
  {
    id: "medlem-2",
    namn: "[Namn Efternamn]",
    roll: "[Roll]",
    bio: "[Kort bio: en mening om bakgrund och vad personen ansvarar för i Snajp.]",
    foto: null
  },
  {
    id: "medlem-3",
    namn: "[Namn Efternamn]",
    roll: "[Roll]",
    bio: "[Kort bio: en mening om bakgrund och vad personen ansvarar för i Snajp.]",
    foto: null
  }
];

/**
 * Initialerna för bubblan när foto saknas.
 *
 * En platshållare som "[Namn Efternamn]" ger inga vettiga initialer — "[N["
 * är sämre än ingenting. Hakparenteser rensas därför bort först, och blir det
 * inget kvar returneras en punkt som fyller bubblan utan att påstå ett namn.
 */
export function initialer(namn: string): string {
  const rent = namn.replace(/[[\]]/g, "").trim();
  const delar = rent.split(/\s+/).filter(Boolean);
  if (!delar.length) return "·";
  return delar
    .slice(0, 2)
    .map((d) => d[0]?.toUpperCase() ?? "")
    .join("");
}

/** Om något fält på sidan fortfarande är ifyllt med en platshållare. */
export function teametArIfyllt(): boolean {
  return TEAM.every(
    (m) => ![m.namn, m.roll, m.bio].some((f) => f.includes("["))
  );
}
