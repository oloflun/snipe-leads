import type { Metadata } from "next";
import { ProductPage } from "@/components/marketing/ProductPage";
import { notFoundOnTenant } from "@/lib/tenants/server";

/**
 * Kvittohanterarens marknadssida. Samma skal som /leads och /support.
 *
 * Produkten läser kundens inkorg (read-only), plockar ut kvitton och
 * sammanställer — den bokför ingenting, och beskrivningen säger det.
 * Interna produktnyckeln är fortfarande "bookkeeping" (databasens värde).
 */
export const metadata: Metadata = {
  title: "Snajp Kvittohanteraren — kvittona i mejlen, utplockade åt dig",
  description:
    "Kvittohanteraren läser din inkorg med read-only-åtkomst, identifierar kvitton och utlägg, läser av belopp, moms, datum och kategori och sammanställer perioden. Dubbletter räknas aldrig två gånger.",
  alternates: { canonical: "/kvitton" }
};

export default async function Page() {
  await notFoundOnTenant();
  return <ProductPage initial="bookkeeping" />;
}
