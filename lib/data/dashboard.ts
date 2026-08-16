import { getPlatformAdmin } from "@/lib/auth/admin";
import { getWorkspaceContext } from "@/lib/workspace";
import { hasDatabase } from "@/lib/db";
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
   * svarar 404. Det här fältet är en navigationsledtråd, inte ett villkor.
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
  if (!hasDatabase()) {
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
    variant: (await workspaceHasData(context.workspace.id, context.user.id)) ? "demo" : "fresh",
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
 * dataset". When Leads is wired to the database this function keeps its meaning
 * and only the view's data source changes.
 */
async function workspaceHasData(workspaceId: string, userId: string): Promise<boolean> {
  try {
    const { sqlAsUser } = await import("@/lib/db");
    // `exists` i stället för `count`: frågan är om det finns någon rad alls, och
    // en räkning över hela tabellen för att jämföra med noll är arbete ingen
    // ville ha.
    const rows = await sqlAsUser<{ present: boolean }>(
      userId,
      "select exists (select 1 from public.companies where workspace_id = $1) as present",
      [workspaceId]
    );
    return Boolean(rows[0]?.present);
  } catch {
    // A failed probe must not decide the user's dashboard. Treat it as fresh:
    // an empty state is recoverable, a demo dataset shown to a real customer
    // is not.
    return false;
  }
}
