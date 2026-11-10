/**
 * Chattens sessionsidentitet, läst ur sessionStorage utan att kunna kasta.
 *
 * Widgeten ligger i en iframe på kundens sajt. Webbläsare som blockerar
 * tredjepartslagring (Safari som standard, Firefox och Chrome i strikt läge)
 * kastar då `SecurityError` redan på `window.sessionStorage`, och före
 * 2026-11-09 föll hela chatten på det: slutkunden såg en felsida i stället för
 * en chatt (Fas 0-fyndet H8). Identiteten är inte värd att fälla chatten för.
 * Går lagringen inte att nå hålls den i minnet, och gäller då så länge sidan
 * är öppen. Samma val som språkväljaren gör i lib/i18n.tsx.
 */

const iMinnet = new Map<string, string>();

function nyttId(): string {
  try {
    return crypto.randomUUID();
  } catch {
    // randomUUID kräver säker kontext. Reserven är inte kryptografisk, men en
    // chattsession utan den vore ingen session alls.
    return `${Date.now().toString(16)}-${Math.random().toString(16).slice(2)}-${Math.random().toString(16).slice(2)}`;
  }
}

export function sessionsId(nyckel: string): string {
  try {
    const sparat = window.sessionStorage.getItem(nyckel);
    if (sparat) return sparat;
    const nytt = nyttId();
    window.sessionStorage.setItem(nyckel, nytt);
    return nytt;
  } catch {
    const sparat = iMinnet.get(nyckel);
    if (sparat) return sparat;
    const nytt = nyttId();
    iMinnet.set(nyckel, nytt);
    return nytt;
  }
}
