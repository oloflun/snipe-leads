/**
 * Utkastens struktur A/B (Sebbe 2026-11-05, snajp-support/app/leads/utkaststruktur.py).
 *
 * A är dagens mejl; B det korta som slutar med en fråga om vad agenten kan ge
 * mottagaren. Valet görs vid Kör Iris och vid varje "Skapa utkast", och det
 * senaste valet minns per webbläsare (en bekvämlighet: utan lagring gäller A).
 */

export type Struktur = "a" | "b";

const NYCKEL = "snajp:leads-struktur";

export function lasStruktur(): Struktur {
  try {
    return window.localStorage.getItem(NYCKEL) === "b" ? "b" : "a";
  } catch {
    return "a";
  }
}

export function sparaStruktur(v: Struktur): void {
  try {
    window.localStorage.setItem(NYCKEL, v);
  } catch {
    /* privat läge: valet gäller bara den här gången */
  }
}

/**
 * Är mejlet skrivet i struktur B? Brödtexten (utan hälsningsrad och
 * hälsningsfras) är högst 70 ord och slutar med en fråga. Ett A-mejl slutar
 * aldrig med en fråga (stilgrinden fäller det), så det skiljer dem åt utan att
 * strukturen behöver lagras på utkastet.
 */
export function arStrukturB(text: string): boolean {
  const rader = String(text || "")
    .trim()
    .split(/\n+/)
    .map((r) => r.trim())
    .filter(Boolean);
  if (rader.length && /^(hej|hejsan|hallå|hi|hello)\b[^.?!]*,?$/i.test(rader[0])) rader.shift();
  const fras = (r: string) => /^(vänliga|bästa|med vänlig|hälsningar|mvh|best|kind)\b/i.test(r);
  // Namnraden efter hälsningsfrasen ("Anna, Hjärtsäker AB") hör till
  // signaturen: kort, utan meningsslut. Demons utkast bär den i texten.
  const namnrad = (r: string) => r.split(/\s+/).length <= 6 && !/[.?!:]$/.test(r);
  while (rader.length) {
    const sist = rader[rader.length - 1];
    if (fras(sist)) rader.pop();
    else if (rader.length >= 2 && namnrad(sist) && fras(rader[rader.length - 2])) rader.splice(-2);
    else break;
  }
  const brod = rader.join(" ");
  return brod.length > 0 && brod.endsWith("?") && brod.split(/\s+/).length <= 70;
}
