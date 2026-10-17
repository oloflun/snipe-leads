import { PAKET, PRODUKTER_FOR_PAKET, utanKvittotillagg, type Paket } from "@/lib/pricing";

/**
 * Baklängesuppslaget products → paket. Bor i en EGEN modul utan "use client":
 * både serversidan (paketflikens nyckeltal) och klientsidan (radernas
 * paketkolumn) behöver samma svar, och en funktion som exporteras ur en
 * klientmodul går inte att ANROPA från en server component — exporten blir
 * en klientreferens, inte en funktion.
 */

/**
 * Exakt paketmatchning mot products-kolumnen. Null = inget känt paket.
 * Kvittohanteraren är ett tillägg (lib/pricing.ts: KVITTO_TILLAGG) och räknas
 * bort före matchningen: leads + support + bookkeeping är Duo med tillägget.
 */
export function paketForProdukter(products: string[] | null | undefined): Paket | null {
  const paketprodukter = utanKvittotillagg(products ?? []);
  if (paketprodukter.length === 0) return null;
  const mangd = [...paketprodukter].sort().join(",");
  const id = (Object.keys(PRODUKTER_FOR_PAKET) as Paket["id"][]).find(
    (kandidat) => [...PRODUKTER_FOR_PAKET[kandidat]].sort().join(",") === mangd
  );
  return id ? (PAKET.find((p) => p.id === id) ?? null) : null;
}
