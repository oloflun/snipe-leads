/**
 * Skriver fram en text tecken för tecken, som när en modell skriver live
 * (Anton 2026-10-19). Takten är ungefär 8 ms per tecken, men hela texten tar
 * aldrig under 0,7 s eller över 2,6 s: ett kort svar ska hinnas se, ett långt
 * ska inte låta besökaren vänta. Returnerar en funktion som avbryter.
 */
export function skrivFram(text: string, steg: (visad: string) => void, klar?: () => void): () => void {
  const total = Math.min(2600, Math.max(700, text.length * 8));
  const start = performance.now();
  let id = requestAnimationFrame(function tick(nu) {
    const n = Math.min(text.length, Math.round(((nu - start) / total) * text.length));
    steg(text.slice(0, n));
    if (n < text.length) id = requestAnimationFrame(tick);
    else klar?.();
  });
  return () => cancelAnimationFrame(id);
}
