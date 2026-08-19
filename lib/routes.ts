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
  /**
   * Flik som bara betyder något för en kund med BÅDA paketen.
   *
   * `/dashboard` ÄR leads-vyn för en leads-kund och kundtjänstvyn för en
   * supportkund (se StartView). För en enproduktskund är "Leads" alltså samma
   * sida som "Översikt", och två flikar till samma vy är inte navigation utan
   * en gissningslek. För en duo-kund är de däremot vägen förbi scope-växeln.
   */
  duoOnly?: boolean;
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
  { href: "/dashboard/leads", labelKey: "nav.leads", product: "leads", duoOnly: true },
  { href: "/dashboard/support", labelKey: "nav.support", product: "support", duoOnly: true },
  { href: "/dashboard/emails", labelKey: "nav.emails", product: "leads" },
  { href: "/dashboard/companies", labelKey: "nav.companies", product: "leads", preview: true },
  { href: "/dashboard/contacts", labelKey: "nav.contacts", product: "leads", preview: true },
  { href: "/dashboard/inbox", labelKey: "nav.inbox", product: "leads", preview: true },
  { href: "/dashboard/analytics", labelKey: "nav.analytics", product: "leads", preview: true },
  { href: "/dashboard/assistant", labelKey: "nav.assistant", product: "leads", preview: true },
  { href: "/settings", labelKey: "nav.settings", product: "shared" }
];

export function routesForProducts(
  products: readonly ProductKey[],
  { includePreview = false }: { includePreview?: boolean } = {}
): AppRoute[] {
  const duo = products.length > 1;
  return appRoutes.filter(
    (route) =>
      (includePreview || !route.preview) &&
      (!route.duoOnly || duo) &&
      (route.product === "shared" || products.includes(route.product))
  );
}

/**
 * Adminytans väg till samma vy.
 *
 * Bodde i AdminShell och gällde bara flikraden. Följden var mätbar: `/settings`
 * lämnades orörd, alltså tog "Inställningar" i adminytan användaren till
 * KUNDENS skal — plattformsraden försvann mitt i ett arbetsmoment, och vägen
 * tillbaka var webbläsarens bakåtknapp.
 *
 * Funktionen bor här för att BÅDA anroparna (AdminShell och `useArbetsvag` i
 * AppShell) ska räkna likadant. Två kartor blir förr eller senare två olika.
 */
export function tillAdminvag(href: string): string {
  if (href === "/dashboard") return "/admin/arbetsyta";
  if (href.startsWith("/dashboard/")) return href.replace("/dashboard", "/admin");
  if (href === "/settings") return "/admin/installningar";
  if (href.startsWith("/settings/")) return href.replace("/settings", "/admin/installningar");
  return href;
}

/**
 * Inställningarna, grupperade efter VAD de är — inte efter vem som råkar
 * använda dem.
 *
 * Den förra grupperingen var per agent (Allmänt / Kundtjänstagenten /
 * Leads-agenten). Det höll tills en kund ägde båda paketen: då låg
 * "Arbetsytan" (som i praktiken var leads-ICP), "Röst och tonläge" (som styr
 * leads-mejl) och "Inkorgar" (som styr supportmail) i tre olika grupper, medan
 * det enda båda agenterna FAKTISKT delar — kunskapsbasen — inte hade någon
 * sida alls.
 *
 * Tre regler bär strukturen:
 *
 *  1. **Underlag skiljs från agentinställning.** Affärskontext och kunskapsbas
 *     är indata som båda agenterna läser, och ligger i en egen grupp. En kund
 *     som lagt in sina villkor en gång ska inte göra om det per agent.
 *  2. **Ingen post pekar ut ur inställningarna.** "Målgrupp och autonomi" låg
 *     på /dashboard/leads/kontroll, alltså en arbetsytesväg — och för en
 *     plattformsadmin skickar app/dashboard/layout.tsx den vägen rakt till
 *     /admin. Länken kunde därför inte bli rätt på båda ytorna samtidigt: det
 *     är hela orsaken till att en inställningsflik "dirigerade till Översikt".
 *  3. **`product` styr vem som ser gruppen.** En supportkund ser varken
 *     leads-agentens röstdokument eller leads-ICP:t — och "Affärskontext" är
 *     numera en egen sida, inte en delad sida som råkade vara leads-ICP.
 */
export type SettingsGroup = {
  label: Localized;
  product: ProductKey | "shared";
  routes: { href: string; label: Localized }[];
};

export const settingsGroups: SettingsGroup[] = [
  {
    label: { sv: "Arbetsytan", en: "Workspace" },
    product: "shared",
    routes: [
      { href: "/settings", label: { sv: "Företaget", en: "Company" } },
      { href: "/settings/arbetsyta", label: { sv: "Min arbetsyta", en: "My workspace" } },
      { href: "/settings/team", label: { sv: "Team", en: "Team" } },
      { href: "/settings/billing", label: { sv: "Plan och fakturering", en: "Plan and billing" } },
      { href: "/settings/addons", label: { sv: "Tillägg", en: "Add-ons" } }
    ]
  },
  {
    // Underlaget, inte agenten. Båda agenterna läser härifrån, och det är
    // också därför dokumentuppladdningen hör hemma här och inte per agent.
    label: { sv: "Kunskap", en: "Knowledge" },
    product: "shared",
    routes: [
      { href: "/settings/affarskontext", label: { sv: "Affärskontext", en: "Business context" } },
      { href: "/settings/kunskapsbas", label: { sv: "Kunskapsbas", en: "Knowledge base" } }
    ]
  },
  {
    // SOUL styr TON, ICP styr URVAL. Gränsen står utskriven i LeadsControls och
    // hör hemma här också: läggs urvalskriterier i röstdokumentet slutar båda
    // fungera som de ska.
    label: { sv: "Leads-agenten", en: "Leads agent" },
    product: "leads",
    routes: [
      { href: "/settings/leads", label: { sv: "Målgrupp och autonomi", en: "Audience and autonomy" } },
      { href: "/settings/soul", label: { sv: "Röst och tonläge", en: "Voice and tone" } }
    ]
  },
  {
    label: { sv: "Kundtjänstagenten", en: "Support agent" },
    product: "support",
    routes: [{ href: "/settings/mailboxes", label: { sv: "Inkorgar", en: "Mailboxes" } }]
  }
];

export function settingsGroupsForProducts(products: readonly ProductKey[]): SettingsGroup[] {
  return settingsGroups.filter(
    (group) => group.product === "shared" || products.includes(group.product)
  );
}

/**
 * Vilken inställningssida en /settings-adress pekar ut.
 *
 * EN dispatcher, precis som WorkspaceSection. Sidorna låg tidigare som sex
 * nästan identiska page.tsx-filer, och varje ny inställning krävde en sjunde.
 * Okänd slug ger null, som anroparen översätter till 404.
 */
export type SettingsSectionKey =
  | "foretaget"
  | "arbetsyta"
  | "team"
  | "billing"
  | "addons"
  | "affarskontext"
  | "kunskapsbas"
  | "leads"
  | "soul"
  | "mailboxes";

const settingsSections: Record<string, SettingsSectionKey> = {
  "": "foretaget",
  arbetsyta: "arbetsyta",
  team: "team",
  billing: "billing",
  addons: "addons",
  affarskontext: "affarskontext",
  kunskapsbas: "kunskapsbas",
  leads: "leads",
  soul: "soul",
  mailboxes: "mailboxes"
};

/**
 * Vilken produkt en inställningssida kräver. Saknas den är sidan delad.
 *
 * Det här är grinden, inte menyfiltret: att gruppen inte RENDERAS för en
 * supportkund hindrar ingen från att skriva /settings/soul i adressfältet.
 */
const settingsSectionProduct: Partial<Record<SettingsSectionKey, ProductKey>> = {
  leads: "leads",
  soul: "leads",
  mailboxes: "support"
};

export function settingsSectionForSlug(slug: readonly string[]): SettingsSectionKey | null {
  if (slug.length > 1) return null;
  return settingsSections[slug[0] ?? ""] ?? null;
}

export function productForSettingsSection(section: SettingsSectionKey): ProductKey | null {
  return settingsSectionProduct[section] ?? null;
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
