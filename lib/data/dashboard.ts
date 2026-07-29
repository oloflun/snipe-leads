import { getWorkspaceContext } from "@/lib/workspace";
import { hasServerSupabaseEnv } from "@/lib/supabase/env";
import { isProductKey, type ProductKey } from "@/lib/routes";

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
  /** Products this workspace is entitled to. Never empty. */
  products: ProductKey[];
  /** "fresh" = nothing in the workspace yet. "demo" = seeded, render the dataset. */
  variant: "fresh" | "demo";
  workspaceName: string | null;
  signedIn: boolean;
};

const ALL_PRODUCTS: ProductKey[] = ["leads", "support"];

/**
 * Anonymous and unconfigured environments both land here: the demo dataset with
 * both products, which is what /dashboard has always shown without auth.
 */
const ANONYMOUS: DashboardState = {
  products: ALL_PRODUCTS,
  variant: "demo",
  workspaceName: null,
  signedIn: false
};

export async function resolveDashboardState(): Promise<DashboardState> {
  if (!hasServerSupabaseEnv()) {
    return ANONYMOUS;
  }

  const context = await getWorkspaceContext();
  if (!context) {
    return ANONYMOUS;
  }

  const entitled = (context.workspace.products ?? []).filter(isProductKey);
  const products = entitled.length > 0 ? entitled : ALL_PRODUCTS;

  return {
    products,
    variant: (await workspaceHasData(context.workspace.id)) ? "demo" : "fresh",
    workspaceName: context.workspace.name,
    signedIn: true
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
