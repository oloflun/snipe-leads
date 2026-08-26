/**
 * Teamet på /vart-team.
 *
 * ## Namnen är bekräftade, inte härledda
 *
 * De två stod som `[Namn Efternamn]` fram till 2026-08-25. Git-historiken
 * visade visserligen två återkommande författare, och efternamnen gick att
 * gissa ur mejladresserna — men en gissad stavning av en verklig persons namn,
 * på just den sida som ska svara på frågan "vem köper vi av", är sämre än en
 * tom ruta. Uppgifterna nedan är därför inhämtade och inte uträknade.
 *
 * ## Titeln är "Grundare" på båda, med flit
 *
 * Ingen funktionsuppdelning i vd, teknikchef eller säljansvarig. Det finns
 * inget i kodbasen som belägger en sådan uppdelning, och en titel som ser
 * proffsig ut men inte stämmer är precis den sortens detalj en köpare
 * kontrollerar. Två grundare i ett litet bolag som gör allting tillsammans
 * är dessutom sant, vilket är den bättre egenskapen hos en titel.
 *
 * ## Bioraderna beskriver ARBETE, inte bakgrund
 *
 * Ingen kan skriva någon annans livshistoria åt dem, så meningarna nedan
 * påstår inget om utbildning, tidigare jobb eller varför bolaget startade.
 * De säger vad var och en faktiskt har byggt, och det går att kontrollera i
 * git-loggen: Anton står för 423 av 424 filändringar i `agent-core`, alltså
 * färdighetsregistret som styr vad agenterna kan; Sebastian har tyngdpunkten
 * i `snajp-support/app`, `components`, `lib` och `supabase`, alltså backend,
 * gränssnitt och schema.
 *
 * FORMULERINGEN UNDVIKER "ansvarar för" med flit. Titlarna är neutrala just
 * för att ingen funktionsuppdelning är bestämd, och en biorad som delar upp
 * ansvaret hade återinfört uppdelningen genom bakdörren. "Har byggt" är ett
 * påstående om vad som gjorts; "ansvarar för" är ett påstående om en
 * organisation som inte finns.
 *
 * Tom sträng är fortfarande giltig och betyder "utelämnas" — kortet renderar
 * då utan biorad, och utkastnotisen bryr sig inte om fältet.
 *
 * ## Mejladresserna står INTE här
 *
 * De personliga adresserna används för att veta vem som är vem i git-loggen,
 * inte för att publiceras. En privat adress på en publik sida är en
 * spamfälla, och kontaktvägen till bolaget finns redan i sidfoten
 * (KONTAKT_MEJL i components/marketing/copy.ts).
 *
 * Foton: lägg dem i public/images/team/ och peka `foto` dit. Saknas fotot
 * ritas en initialbubbla i stället — aldrig en trasig bildikon.
 */

export type Teammedlem = {
  /** Stabil nyckel för React och för ankare. Ändra inte när fälten fylls i. */
  id: string;
  namn: string;
  roll: string;
  /** Tom sträng = utelämnas. Se resonemanget ovan. */
  bio: string;
  /** Sökväg under /public, eller null för initialbubbla. */
  foto: string | null;
};

export const TEAM: Teammedlem[] = [
  {
    id: "sebastian-bergman",
    namn: "Sebastian Bergman",
    roll: "Grundare",
    bio:
      "Har byggt det mesta av plattformen: agenternas backend, databasen och " +
      "gränssnittet kunderna arbetar i.",
    foto: null
  },
  {
    id: "anton-lundin",
    namn: "Anton Lundin",
    roll: "Grundare",
    bio:
      "Har byggt agenternas färdighetsregister — spelböckerna som avgör vad de " +
      "kan och hur de resonerar.",
    foto: null
  }
];

/**
 * Initialerna för bubblan när foto saknas.
 *
 * Hakparenteser rensas först: en platshållare som "[Namn Efternamn]" hade gett
 * "[N" som initialer, vilket är sämre än ingenting. Blir det inget kvar
 * returneras en punkt, som fyller bubblan utan att påstå ett namn.
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

/**
 * Om sidan är publicerbar.
 *
 * Mäter NAMN och ROLL, inte bio. Bion är valfri (se ovan), och att låta en
 * utelämnad bio hålla kvar utkastnotisen hade gjort notisen permanent —
 * alltså en varning som ingen kan släcka och därför ingen läser.
 */
export function teametArIfyllt(): boolean {
  return TEAM.every((m) => ![m.namn, m.roll].some((f) => f.includes("[")));
}
