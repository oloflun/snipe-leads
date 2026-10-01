import { PAKET, PRODUKTER_FOR_PAKET, type Paket } from "@/lib/pricing";

/**
 * Baklängesuppslaget products → paket. Bor i en EGEN modul utan "use client":
 * både serversidan (paketflikens nyckeltal) och klientsidan (radernas
 * paketkolumn) behöver samma svar, och en funktion som exporteras ur en
 * klientmodul går inte att ANROPA från en server component — exporten blir
 * en klientreferens, inte en funktion.
 */

/** Exakt paketmatchning mot products-kolumnen. Null = inget känt paket. */
export function paketForProdukter(products: string[] | null | undefined): Paket | null {
  if (!products || products.length === 0) return null;
  const mangd = [...products].sort().join(",");
  const id = (Object.keys(PRODUKTER_FOR_PAKET) as Paket["id"][]).find(
    (kandidat) => [...PRODUKTER_FOR_PAKET[kandidat]].sort().join(",") === mangd
  );
  return id ? (PAKET.find((p) => p.id === id) ?? null) : null;
}
