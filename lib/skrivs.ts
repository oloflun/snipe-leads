/**
 * Skriver fram en text tecken för tecken, som när en modell skriver live
 * (Anton 2026-10-19). Takten är ungefär 8 ms per tecken, men hela texten tar
 * aldrig under 0,7 s eller över 2,6 s: ett kort svar ska hinnas se, ett långt
 * ska inte låta besökaren vänta. Returnerar en funktion som avbryter.
 */
export function skrivFram(text: string, steg: (visad: string) => void, klar?: () => void): () => void {
  const total = Math.min(2600, Math.max(700, text.length * 8));
  const start = performance.now();
  let sist = -1;
  let senast = -Infinity;
  let id = requestAnimationFrame(function tick(nu) {
    const n = Math.min(text.length, Math.round(((nu - start) / total) * text.length));
    // Texten uppdateras högst var trettionde millisekund. Varje uppdatering ritar om
    // rutan, och i sextio uppdateringar i sekunden stod skrivningen för 1 200 målningar
    // under en skroll av startsidan (uppmätt 2026-11-23). Tecknen kommer i samma takt
    // och texten är klar i samma ögonblick; det är bara färre mellanlägen som ritas.
    if (n !== sist && (nu - senast >= SKRIVTAKT_MS || n >= text.length)) {
      sist = n;
      senast = nu;
      steg(text.slice(0, n));
    }
    if (n < text.length) id = requestAnimationFrame(tick);
    else klar?.();
  });
  return () => cancelAnimationFrame(id);
}

/** Minsta tid mellan två uppdateringar av en text som skrivs eller räknas fram. */
export const SKRIVTAKT_MS = 30;
