import { getPlatformAdmin } from "@/lib/auth/admin";
import { getWorkspaceContext } from "@/lib/workspace";
import { hasServerSupabaseEnv } from "@/lib/supabase/env";
import { isProductKey, type ProductKey } from "@/lib/routes";
import { isAddonKey, type AddonKey } from "@/lib/addons";

/**
 * What the dashboard needs to know before it renders anything.
 *
 * Two independent questions:
 *  - Which products may this workspace use?  (entitlement, server-decided)
 *  - Does it have data yet?                  (fresh vs seeded)
 *
 * A brand new signup gets an empty workspace and therefore the fresh dashboard.
 * A workspace seeded with the demo dataset gets the demo dashboard. Seeding is
 * what makes an account a demo, so no schema flag is needed for it.
 */
export type DashboardState = {
  /**
   * Products this workspace is entitled to. MAY be empty since Fas 3 —
   * entitlements är fail-closed, och en felkonfigurerad arbetsyta ska se
   * mindre, inte allt. Varje konsument måste tåla en tom lista.
   */
  products: ProductKey[];
  /** Tillköpta tilläggstjänster (migration 022). Tomt = inga. */
  addons: AddonKey[];
  /** "fresh" = nothing in the workspace yet. "demo" = seeded, render the dataset. */
  variant: "fresh" | "demo";
  workspaceName: string | null;
  signedIn: boolean;
  /**
   * Plattformsadmin — enbart för att kunna VISA vägen till /admin.
   *
   * Grinden är och förblir `requirePlatformAdmin()` i app/admin/layout.tsx, som
   * svarar 404. Det här fältet är en navigationsledtråd, inte ett villkor: sätts
   * det till true i devtools får man en länk som leder till en 404.
   *
   * Fältet finns för att ytan annars var oåtkomlig i praktiken. Vakten släppte
   * igenom rätt person, men INGEN länk till /admin fanns någonstans i UI:t —
   * enda vägen in var att skriva URL:en för hand, vilket ingen gör som inte
   * redan vet att sidan finns.
   */
  isPlatformAdmin: boolean;
};

const ALL_PRODUCTS: ProductKey[] = ["leads", "support"];

/**
 * Anonymous and unconfigured environments both land here: the demo dataset with
 * both products, which is what /dashboard has always shown without auth.
 */
const ANONYMOUS: DashboardState = {
  products: ALL_PRODUCTS,
  addons: [],
  variant: "demo",
  workspaceName: null,
  signedIn: false,
  isPlatformAdmin: false
};

export async function resolveDashboardState(): Promise<DashboardState> {
  if (!hasServerSupabaseEnv()) {
    return ANONYMOUS;
  }

  const context = await getWorkspaceContext();
  if (!context) {
    return ANONYMOUS;
  }

  // Fail-CLOSED. Tidigare föll en tom eller okänd produktlista tillbaka på
  // BÅDA produkterna: en kund med felaktig konfiguration såg alltså MER än
  // den betalat för, och felet var osynligt eftersom resultatet såg normalt
  // ut. En felkonfigurerad kund ska se mindre, inte mer — den varianten
  // upptäcks samma dag av kunden själv.
  //
  // ANONYMOUS ovan behåller sin öppna lista: den är marknadsföringsdemon och
  // innehåller ingen kunddata alls.
  const products = (context.workspace.products ?? []).filter(isProductKey);

  return {
    products,
    addons: (context.workspace.addons ?? []).filter(isAddonKey),
    variant: (await workspaceHasData(context.workspace.id)) ? "demo" : "fresh",
    workspaceName: context.workspace.name,
    signedIn: true,
    isPlatformAdmin: Boolean(await getPlatformAdmin())
  };
}

/**
 * Cheap existence probe, not a count: we only need to know whether the workspace
 * has been filled in at all.
 *
 * Leads still renders from `lib/mock-data.ts`, so today "seeded" means "show the
 * dataset". When Leads is wired to Supabase this function keeps its meaning and
 * only the view's data source changes.
 */
async function workspaceHasData(workspaceId: string): Promise<boolean> {
  try {
    const { createClient } = await import("@/lib/supabase/server");
    const supabase = await createClient();

    const { count, error } = await supabase
      .from("companies")
      .select("id", { count: "exact", head: true })
      .eq("workspace_id", workspaceId);

    if (error) {
      // A failed probe must not decide the user's dashboard. Treat it as fresh:
      // an empty state is recoverable, a demo dataset shown to a real customer
      // is not.
      return false;
    }

    return (count ?? 0) > 0;
  } catch {
    return false;
  }
}
