"use server";

import { revalidatePath } from "next/cache";
import { sqlAsUser } from "@/lib/db";
import { isProductKey, type ProductKey } from "@/lib/routes";
import { aktivVy } from "@/lib/vy";
import { getWorkspaceContext } from "@/lib/workspace";

/**
 * Kunden byter paket själv.
 *
 * ## Vad ett paketbyte ÄR i det här systemet
 *
 * `workspaces.products` — samma kolumn som grindar varje flik, varje
 * inställningssida och varje agentvy. Det finns ingen separat "plan"; paketet
 * ÄR entitlementen. Därför kan sidan inte visa ett paket som inte gäller: det
 * som står på faktureringssidan är exakt det som styr produkten.
 *
 * ## Varför en RPC och inte en UPDATE
 *
 * `workspaces` är läsbar men inte skrivbar under RLS, och det ska den förbli.
 * En UPDATE-policy gäller raden, inte kolumnen, och hade öppnat `slug` — som
 * binder arbetsytan till en backend-tenant. Se migration 044.
 *
 * ## Varför demovyn OCH kundbesök nekas
 *
 * I demovyn OCH i ett kundbesök (`aktivVy().vy === "kund"`) är arbetsytan
 * fortfarande ADMINENS egen medan tenanten är demokontots eller den
 * namngivna kunden. Ett paketbyte där hade alltså ändrat Snajps eget
 * entitlement från en yta som ser ut som en kunds. Samma fälla som
 * affärskontexten hade (lib/actions/affarskontext.ts) — och kundbesöks-
 * grenen av just DEN fällan upptäcktes först i drift 2026-09-02. Den här
 * funktionen blockerade redan demo men inte kund; samma missade gren.
 */

export type Planbyte = { success: boolean; error?: string; products?: ProductKey[] };

/** Paketen kunden kan välja mellan, och vad de ger. Speglar `PAKET` i lib/pricing.ts. */
const PRODUKTER_FOR_PAKET: Record<string, ProductKey[]> = {
  leads: ["leads"],
  support: ["support"],
  bookkeeping: ["bookkeeping"],
  duo: ["leads", "support"],
  trio: ["leads", "support", "bookkeeping"]
};

export async function bytPlan(paketId: string): Promise<Planbyte> {
  const context = await getWorkspaceContext();
  if (!context) {
    return { success: false, error: "Du måste vara inloggad." };
  }

  if ((await aktivVy()).vy !== "admin") {
    return {
      success: false,
      error:
        "Paketbyte är avstängt i demo- och kundvy. Arbetsytan bakom vyn är vår egen, och bytet hade ändrat den — inte kundens."
    };
  }

  const nya = PRODUKTER_FOR_PAKET[paketId];
  if (!nya) {
    return { success: false, error: `Okänt paket: ${paketId}.` };
  }

  let rader: { set_workspace_products: string[] }[];
  try {
    rader = await sqlAsUser<{ set_workspace_products: string[] }>(
      context.user.id,
      "select public.set_workspace_products($1::text[])",
      [nya]
    );
  } catch (error) {
    return { success: false, error: (error as Error).message };
  }

  // Läses tillbaka ur SVARET och inte ur `nya`. Funktionen returnerar det som
  // faktiskt står i kolumnen, och om de två någonsin skiljer sig är det den i
  // databasen som gäller — en vy som ritar det den skickade in kan visa ett
  // paket kunden inte har.
  const skrivna = (rader[0]?.set_workspace_products ?? []).filter(isProductKey);

  // Menyn, flikarna och grindarna renderas på servern ur samma kolumn. Utan
  // det här står "Kundtjänst" kvar i navigationen efter en nedgradering tills
  // användaren råkar ladda om sidan.
  revalidatePath("/", "layout");

  return { success: true, products: skrivna };
}
