import type { CopyKey } from "@/lib/i18n";

/**
 * Snajp ships two products. A workspace may own either or both; the server
 * decides, and the nav only ever renders what the workspace owns.
 */
export type ProductKey = "leads" | "support";

export const productKeys = ["leads", "support"] as const;

export function isProductKey(value: string): value is ProductKey {
  return (productKeys as readonly string[]).includes(value);
}

export type AppRoute = {
  href: string;
  labelKey: CopyKey;
  /** "shared" renders for every workspace regardless of entitlement. */
  product: ProductKey | "shared";
};

/**
 * The workspace lives entirely under /dashboard. The bare /leads and /support
 * paths are the public product pages and are deliberately not app routes.
 */
export const appRoutes: AppRoute[] = [
  { href: "/dashboard", labelKey: "nav.dashboard", product: "shared" },
  { href: "/dashboard/leads", labelKey: "nav.leads", product: "leads" },
  { href: "/dashboard/companies", labelKey: "nav.companies", product: "leads" },
  { href: "/dashboard/contacts", labelKey: "nav.contacts", product: "leads" },
  { href: "/dashboard/campaigns", labelKey: "nav.campaigns", product: "leads" },
  { href: "/dashboard/emails", labelKey: "nav.emails", product: "leads" },
  { href: "/dashboard/inbox", labelKey: "nav.inbox", product: "leads" },
  { href: "/dashboard/analytics", labelKey: "nav.analytics", product: "leads" },
  { href: "/dashboard/assistant", labelKey: "nav.assistant", product: "leads" },
  { href: "/dashboard/support", labelKey: "nav.support", product: "support" },
  { href: "/settings", labelKey: "nav.settings", product: "shared" }
];

export function routesForProducts(products: readonly ProductKey[]): AppRoute[] {
  return appRoutes.filter(
    (route) => route.product === "shared" || products.includes(route.product)
  );
}

export const settingsRoutes = [
  { href: "/settings/mailboxes", label: { sv: "Mailboxar", en: "Mailboxes" } },
  { href: "/settings/team", label: { sv: "Team", en: "Team" } },
  { href: "/settings/billing", label: { sv: "Fakturering", en: "Billing" } }
] as const;

/**
 * Public marketing surfaces. `/leads` and `/support` render the same shell with a
 * different product selected, so both are linkable and crawlable.
 */
export const publicProductRoutes = ["/", "/leads", "/support"] as const;

// Auth route guards (pure, no server dependencies — safe for middleware).
// /leads and /support are NOT listed: they are public product pages, and guarding
// them would bounce every visitor to /login.
export const protectedRoutePrefixes = ["/dashboard", "/settings", "/onboarding"] as const;

export const authRoutes = ["/login", "/auth/callback"] as const;

export function isProtectedRoute(pathname: string): boolean {
  return protectedRoutePrefixes.some(
    (prefix) => pathname === prefix || pathname.startsWith(`${prefix}/`)
  );
}

export function isAuthRoute(pathname: string): boolean {
  return authRoutes.some((route) => pathname === route || pathname.startsWith(`${route}/`));
}
