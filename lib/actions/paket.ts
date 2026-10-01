"use server";

import { revalidatePath } from "next/cache";

import { getPlatformAdmin } from "@/lib/auth/admin";
import { sqlAsUser } from "@/lib/db";
import { PRODUKTER_FOR_PAKET, arPaketId } from "@/lib/pricing";

/**
 * Paketbytet per kund — plattformsadminens skrivyta (fliken Paket).
 *
 * ## Varför en EGEN väg bredvid kundens
 *
 * `set_workspace_products` (044) är kundens självbetjäning och skriver bara
 * den egna arbetsytan, härledd ur app.user_id. Adminen byter en ANNAN kunds
 * paket, och den korsningen sker i `admin_set_workspace_products` (080) som
 * grindar på platform_admins själv — samma mönster, samma skäl, som
 * tilläggens 063.
 *
 * ## Grinden står i funktionen
 *
 * Samma regel som tillagg.ts: en server action är en POST-endpoint med ett
 * genererat id, och att den bara anropas från adminsidan är ett antagande om
 * klienten. Databasfunktionen kontrollerar dessutom platform_admins själv.
 */

export type Paketbyte = {
  success: boolean;
  /** Det som faktiskt står i kolumnen efter skrivningen. */
  products?: string[];
  error?: string;
  /** Funktionen ur migration 080 finns inte i databasen. */
  migrationSaknas?: boolean;
};

/** 42883 är Postgres undefined_function — migrationen är inte körd i miljön. */
function saknarMigration(error: unknown): boolean {
  const fel = error as { code?: string; message?: string } | null;
  if (fel?.code === "42883") return true;
  return /admin_set_workspace_products\b.*does not exist/i.test(fel?.message ?? "");
}

function felText(error: unknown): string {
  if (saknarMigration(error)) {
    return (
      "Paketet kan inte bytas: databasfunktionen från migration 080 " +
      "(supabase/migrations/20261001090000_080_paket_admin.sql) finns inte i " +
      "den här miljön. Kör `python scripts/railway_migrate.py --env development " +
      "--apply` (eller --env main) och ladda om sidan."
    );
  }
  const text = (error as Error)?.message ?? "";
  if (text.includes("arbetsytan finns inte")) {
    // Samma svar som funktionen ger på nekad behörighet, med flit.
    return "Kunden har ingen arbetsyta kopplad till sig, eller så saknas behörighet.";
  }
  if (text.includes("okänd produkt")) {
    return "Paketets produkter finns inte i databasens lista. Kartan och check-villkoret har glidit isär, se lib/pricing.ts.";
  }
  return text || "Paketet kunde inte bytas.";
}

export async function bytPaket(tenantId: string, paketId: string): Promise<Paketbyte> {
  const admin = await getPlatformAdmin();
  if (!admin) {
    return { success: false, error: "Bara plattformsadmin kan byta paket." };
  }

  // Valideras HÄR, inte bara i databasen: ett okänt paket-id ska ge ett
  // begripligt fel innan någon produktlista alls lämnar Next-appen.
  if (!arPaketId(paketId)) {
    return { success: false, error: `Okänt paket: ${paketId}.` };
  }
  const produkter = PRODUKTER_FOR_PAKET[paketId];

  let rader: { admin_set_workspace_products: string[] }[];
  try {
    rader = await sqlAsUser<{ admin_set_workspace_products: string[] }>(
      admin.userId,
      "select public.admin_set_workspace_products($1::uuid, $2::text[])",
      [tenantId, produkter]
    );
  } catch (error) {
    return { success: false, error: felText(error), migrationSaknas: saknarMigration(error) };
  }

  // Läses tillbaka ur SVARET, inte ur kartan — samma regel som sattTillagg:
  // en vy som ritar det den skickade in kan visa ett paket kunden inte har.
  const skrivna = rader[0]?.admin_set_workspace_products ?? produkter;

  // Paketet grindar kundens meny och vyer, renderade på servern.
  revalidatePath("/", "layout");

  return { success: true, products: skrivna };
}
