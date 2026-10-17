import { redirect } from "next/navigation";

/**
 * Kvittohanterarens marknadssida finns inte längre (Sebbe 2026-10-17).
 * Kvittohanteraren är ett tillägg till Support som står på is och inte säljs
 * (lib/routes.ts: VILANDE_PRODUKTER, lib/pricing.ts: KVITTO_TILLAGG), så
 * länkar och bokmärken hit landar på Supports sida. Sidans innehåll
 * (copy.ts, UspSection, ProduktBilder, KvittoDemo) står kvar för en
 * kommande lansering.
 */
export default function Page() {
  redirect("/support");
}
