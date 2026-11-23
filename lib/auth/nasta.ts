/**
 * Vart användaren skickas efter inloggningen. Bara vägar på den egna sajten.
 *
 * `?next=` kommer ur adressfältet och gick förut oprövad in i `redirect()`.
 * En länk som `/login?next=https://annan-sajt.se` loggade då in användaren
 * hos oss och lämnade av den på en främmande sajt, med vår domän som
 * avsändare (öppen omdirigering). `//annan-sajt.se` och `/\annan-sajt.se`
 * läser webbläsaren också som en annan värd.
 */
const STANDARD = "/dashboard";

export function sakerNasta(nasta: string | null | undefined, standard: string = STANDARD): string {
  if (typeof nasta !== "string") return standard;
  const vag = nasta.trim();
  if (!vag.startsWith("/")) return standard;
  if (vag.startsWith("//") || vag.startsWith("/\\")) return standard;
  // Styrtecken (radbrytning, tabb) skalas bort av webbläsaren och kan göra
  // "/\n/annan-sajt.se" till "//annan-sajt.se".
  if (/[\u0000-\u001f\u007f]/.test(vag)) return standard;
  return vag;
}
