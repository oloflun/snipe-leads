import type { CopyKey, Localized } from "@/lib/i18n";

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
  /** Mock-driven surface: routen finns, men den står inte i kundens meny. */
  preview?: boolean;
};

/**
 * The workspace lives entirely under /dashboard. The bare /leads and /support
 * paths are the public product pages and are deliberately not app routes.
 */
/**
 * `preview: true` betyder att routen finns och fungerar, men INTE står i
 * kundens navigation. Alla fem sådana renderar `lib/mock-data.ts` — för en
 * riktig kund är de alltså tomma skal som ser ut som produkten men inte är
 * det, och nio menyposter där fem inte gör något är värre än fyra som gör det.
 *
 * Ingen fil raderas. De nås fortfarande direkt, och entitlement-grinden i
 * dispatchern gäller som förut — det här styr bara vad som visas i menyn.
 */
export const appRoutes: AppRoute[] = [
  { href: "/dashboard", labelKey: "nav.dashboard", product: "shared" },
  { href: "/dashboard/leads", labelKey: "nav.leads", product: "leads" },
  { href: "/dashboard/emails", labelKey: "nav.emails", product: "leads" },
  { href: "/dashboard/leads/kontroll", labelKey: "nav.leadsControl", product: "leads" },
  { href: "/dashboard/companies", labelKey: "nav.companies", product: "leads", preview: true },
  { href: "/dashboard/contacts", labelKey: "nav.contacts", product: "leads", preview: true },
  { href: "/dashboard/inbox", labelKey: "nav.inbox", product: "leads", preview: true },
  { href: "/dashboard/analytics", labelKey: "nav.analytics", product: "leads", preview: true },
  { href: "/dashboard/assistant", labelKey: "nav.assistant", product: "leads", preview: true },
  { href: "/dashboard/support", labelKey: "nav.support", product: "support" },
  { href: "/settings", labelKey: "nav.settings", product: "shared" }
];

export function routesForProducts(
  products: readonly ProductKey[],
  { includePreview = false }: { includePreview?: boolean } = {}
): AppRoute[] {
  return appRoutes.filter(
    (route) =>
      (includePreview || !route.preview) &&
      (route.product === "shared" || products.includes(route.product))
  );
}

/**
 * Inställningarna, GRUPPERADE PER AGENT.
 *
 * Listan var tidigare platt och — vilket är värre — helt oanvänd: inget
 * renderade den, och /settings hade därför ingen flikrad alls. Sex sidor fanns
 * men gick bara att nå genom att skriva adressen. En navigationslista som
 * ingen läser blir också en lista ingen håller uppdaterad.
 *
 * `product` styr vem som ser gruppen. En arbetsyta som bara äger Support ska
 * inte se leads-agentens röstdokument — samma fail-closed-regel som resten av
 * menyn, och den enda grinden som räknas sitter ändå i sidan själv.
 */
export type SettingsGroup = {
  label: Localized;
  product: ProductKey | "shared";
  routes: { href: string; label: Localized }[];
};

export const settingsGroups: SettingsGroup[] = [
  {
    label: { sv: "Allmänt", en: "General" },
    product: "shared",
    routes: [
      { href: "/settings", label: { sv: "Arbetsytan", en: "Workspace" } },
      { href: "/settings/team", label: { sv: "Team", en: "Team" } },
      { href: "/settings/billing", label: { sv: "Fakturering", en: "Billing" } },
      { href: "/settings/addons", label: { sv: "Tillägg", en: "Add-ons" } }
    ]
  },
  {
    label: { sv: "Kundtjänstagenten", en: "Support agent" },
    product: "support",
    routes: [{ href: "/settings/mailboxes", label: { sv: "Inkorgar", en: "Mailboxes" } }]
  },
  {
    // SOUL styr TON, ICP styr URVAL. Gränsen står utskriven i LeadsControls och
    // hör hemma här också: läggs urvalskriterier i röstdokumentet slutar båda
    // fungera som de ska.
    label: { sv: "Leads-agenten", en: "Leads agent" },
    product: "leads",
    routes: [
      { href: "/settings/soul", label: { sv: "Röst och tonläge", en: "Voice and tone" } },
      { href: "/dashboard/leads/kontroll", label: { sv: "Målgrupp och autonomi", en: "Audience and autonomy" } }
    ]
  }
];

export function settingsGroupsForProducts(products: readonly ProductKey[]): SettingsGroup[] {
  return settingsGroups.filter(
    (group) => group.product === "shared" || products.includes(group.product)
  );
}

/**
 * Public marketing surfaces. `/leads` and `/support` render the same shell with a
 * different product selected, so both are linkable and crawlable.
 */
export const publicProductRoutes = ["/", "/leads", "/support"] as const;

// Auth route guards (pure, no server dependencies — safe for middleware).
// /leads and /support are NOT listed: they are public product pages, and guarding
// them would bounce every visitor to /login.
export const protectedRoutePrefixes = ["/dashboard", "/settings", "/onboarding"] as const;

// /auth/callback är BORTA sedan Auth.js ersatte Supabase Auth (e376e71).
// Routen raderades men stod kvar här och i proxyns matcher — en matcher som
// listar en route som inte finns kostar en Edge-invokation per träff och gör
// listan opålitlig att läsa. Auth.js egna vägar ligger under /api/auth/*.
export const authRoutes = ["/login"] as const;

export function isProtectedRoute(pathname: string): boolean {
  return protectedRoutePrefixes.some(
    (prefix) => pathname === prefix || pathname.startsWith(`${prefix}/`)
  );
}

export function isAuthRoute(pathname: string): boolean {
  return authRoutes.some((route) => pathname === route || pathname.startsWith(`${route}/`));
}
