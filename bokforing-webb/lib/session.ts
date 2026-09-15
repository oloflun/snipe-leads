/**
 * Sessionskakan för lösenordsväggen — delad mellan proxyn (som kontrollerar)
 * och inloggningsroutens handler (som utfärdar).
 *
 * Värdet är SHA-256 av lösenordet med ett fast prefix: ingen databas, inga
 * sessioner att städa, och kakan blir automatiskt ogiltig i samma stund som
 * BOKFORING_LOSEN byts. Web Crypto och inte node:crypto, eftersom proxyn kan
 * köra i edge-runtimen där node-modulen inte finns.
 *
 * Det här är fortfarande ett driftskydd för en icke lanserad yta, inte en
 * produktlogin — samma roll som Basic Auth-väggen den ersätter, men med en
 * riktig sida i stället för webbläsarens nativa ruta (som visade sig studsa
 * för användaren utan felmeddelande).
 */

export const SESSION_KAKA = "bk_session";

export async function sessionsvarde(losen: string): Promise<string> {
  const data = new TextEncoder().encode(`snajp-bokforing-session:${losen}`);
  const hash = await crypto.subtle.digest("SHA-256", data);
  return Array.from(new Uint8Array(hash))
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("");
}

/**
 * Publika basadressen — ur x-forwarded-headrarna, INTE request.url.
 * Bakom Railways proxy är request.url i en route handler den interna
 * adressen (http://localhost:8080); en redirect byggd på den skickade
 * webbläsaren till localhost. Uppmätt live 2026-09-15.
 */
export function basUrl(request: { headers: Headers }): string {
  const proto = request.headers.get("x-forwarded-proto") ?? "https";
  const host = request.headers.get("x-forwarded-host") ?? request.headers.get("host") ?? "";
  return `${proto}://${host}`;
}

/** Bara interna sökvägar får vara mål efter inloggning — en öppen redirect
 *  är en nätfiskekomponent, även bakom en vägg. */
export function saneraNasta(nasta: string | null | undefined): string {
  if (!nasta || !nasta.startsWith("/") || nasta.startsWith("//") || nasta.startsWith("/logga-in")) {
    return "/";
  }
  return nasta;
}
