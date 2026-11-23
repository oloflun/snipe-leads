/**
 * Beskedet ur en felkropp, alltid en sträng eller null. Aldrig ett objekt.
 *
 * FastAPI svarar `{"detail": ...}`, och `detail` är en sträng för våra egna
 * HTTPException men en LISTA av objekt när pydantic fäller indata (en för lång
 * kunskapsbastext, en för kort rubrik). Mönstret `kropp?.detail ?? kropp?.error`
 * skickade listan vidare: i `new Error(...)` blev den "[object Object]" i rött
 * hos kunden, och i en `setFel(...)` som renderas direkt fällde den hela vyn
 * (React ritar inte objekt).
 *
 * Proxyn (app/api/snajp-support/_lib.ts) har redan skrivit en läsbar `error`
 * bredvid en sådan lista, så ordningen är: `detail` om den är text, annars
 * `detail.message`, annars `error`. Pydantics engelska fältmeddelanden visas
 * aldrig: de är skrivna för utvecklare.
 */
export function kroppsbesked(kropp: unknown): string | null {
  if (!kropp || typeof kropp !== "object") return null;
  const k = kropp as { detail?: unknown; error?: unknown };
  if (typeof k.detail === "string" && k.detail.trim()) return k.detail;
  if (k.detail && typeof k.detail === "object" && !Array.isArray(k.detail)) {
    const besked = (k.detail as { message?: unknown }).message;
    if (typeof besked === "string" && besked.trim()) return besked;
  }
  if (typeof k.error === "string" && k.error.trim()) return k.error;
  if (Array.isArray(k.detail) && k.detail.length > 0) {
    return "Uppgifterna gick inte att läsa. Kontrollera det du fyllt i och försök igen.";
  }
  return null;
}
