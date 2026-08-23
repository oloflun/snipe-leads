import type { CopyKey, Localized } from "@/lib/i18n";

/**
 * Snajp ships two products. A workspace may own either or both; the server
 * decides, and the nav only ever renders what the workspace owns.
 */
/**
 * Vad LÄGET visar just nu, inom det arbetsytan har rätt till.
 *
 * Typen bor här och inte i DashboardContext för att servern måste kunna läsa
 * den: läget ligger i en cookie, och `resolveDashboardState` avgör startvärdet
 * innan något renderas. En typ i en "use client"-modul går att importera men
 * signalerar fel hemvist.
 */
export type Scope = ProductKey | "both";

/**
 * Cookien läget bor i. Låg tidigare i localStorage, vilket gjorde den osynlig
 * för servern — och därmed kunde `/settings/*` och `/admin/*`, som renderas på
 * servern, aldrig grinda på annat än rättighet. Att klicka "Support" ändrade
 * alltså bara arbetsytans flikar, inte inställningarna bakom dem.
 *
 * Inte httpOnly: klienten skriver den när flikarna klickas. Den är ett
 * visningsval, inte ett behörighetsval — grinden som räknar är `products`.
 */
export const SCOPE_COOKIE = "snajp.scope";

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
 *
 * `preview: true` betyder att routen finns och fungerar, men INTE står i
 * kundens navigation. Alla fem sådana renderar `lib/mock-data.ts` — för en
 * riktig kund är de alltså tomma skal som ser ut som produkten men inte är
 * det, och nio menyposter där fem inte gör något är värre än fyra som gör det.
 *
 * Ingen fil raderas. De nås fortfarande direkt, och entitlement-grinden i
 * dispatchern gäller som förut — det här styr bara vad som visas i menyn.
 */

/**
 * `duoOnly` är BORTA, och det är inte en förenkling utan en följd.
 *
 * Flaggan fanns för att `/dashboard` VAR leads-vyn för en leads-kund och
 * kundtjänstvyn för en supportkund — två flikar till samma sida är inte
 * navigation utan en gissningslek. Sedan `/dashboard` blivit en ÖVERSIKT (se
 * StartView) gäller det inte längre: översikten sammanfattar arbetet, den är
 * inte arbetet. Med flaggan kvar hade en enproduktskund inte kunnat nå sin
 * arbetsvy alls — varken "Leads" eller "Kundtjänst" hade renderats, och
 * `/dashboard` hade slutat vara den.
 */
export const appRoutes: AppRoute[] = [
  { href: "/dashboard", labelKey: "nav.dashboard", product: "shared" },
  { href: "/dashboard/leads", labelKey: "nav.leads", product: "leads" },
  { href: "/dashboard/support", labelKey: "nav.support", product: "support" },
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
  return appRoutes.filter(
    (route) =>
      (includePreview || !route.preview) &&
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
 * Inställningarna, grupperade efter VILKEN FRÅGA de svarar på.
 *
 * ## Vad som var fel med den förra grupperingen
 *
 * Fyra grupper — Arbetsytan / Kunskap / Leads-agenten / Kundtjänstagenten —
 * blandade tre sorters inställning i den första och delade upp resten efter
 * agent. Tre följder, alla uppmätta i skärmdump:
 *
 *  1. "Min arbetsyta" var en LEADS-sammanfattning som visades även för en
 *     supportkund, eftersom gruppen var `shared`.
 *  2. "Röst och tonläge" låg under Leads-agenten, fast SOUL är ett
 *     `agent_context_docs`-dokument som styr hur BÅDA agenterna låter. En
 *     duo-kund fick alltså leta rösten under leads.
 *  3. Kundtjänstens motsvarighet till "Målgrupp och autonomi" — reglerna per
 *     fack — låg inte här alls, utan i en utfällbar panel inuti inkorgen.
 *     Samma fråga, två helt olika ställen.
 *
 * ## Fyra grupper, ordnade efter hur ofta de rörs
 *
 *  1. **Vad agenten vet** — underlaget. Fylls i en gång och läses av båda
 *     agenterna. En duo-kund gör det inte två gånger.
 *  2. **Dina inställningar** — notiser och tema. Den enda gruppen som är
 *     PERSONLIG: svaren gäller den inloggade, inte arbetsytan.
 *  3. **Vad agenten får göra** — befogenheterna, en rad per agent, i samma
 *     grupp så att symmetrin syns.
 *  4. **Kontot** — bolaget och pengarna. Inget av det handlar om agenten.
 *
 * ## Varför `product` sitter på POSTEN och inte på gruppen
 *
 * Grupp 2 innehåller både leads- och supportposter. Med produktflaggan kvar på
 * gruppen hade den behövt delas i två — alltså tillbaka till gruppering per
 * agent, som är precis det vi tar bort. Gruppen renderas när minst en av dess
 * poster överlever filtret.
 */
export type SettingsRoute = {
  href: string;
  label: Localized;
  /** Saknas = delad. Annars renderas posten bara för den produkten. */
  product?: ProductKey;
  /**
   * Döljs i demovyn OCH i kundläge. Gäller idag bara Team, och skälet är
   * konkret: sidan listar arbetsytans riktiga medlemsadresser, alltså Snajps
   * egna, och demovyn visas för utomstående.
   */
  doldIDemo?: boolean;
};

export type SettingsGroup = {
  label: Localized;
  routes: SettingsRoute[];
};

export const settingsGroups: SettingsGroup[] = [
  {
    // Underlaget, inte agenten. Det är också därför dokumentuppladdningen hör
    // hemma här och inte per agent.
    label: { sv: "Vad agenterna vet", en: "What the agents know" },
    routes: [
      { href: "/settings/affarskontext", label: { sv: "Affärskontext", en: "Business context" } },
      { href: "/settings/kunskapsbas", label: { sv: "Kunskapsbas", en: "Knowledge base" } },
      // SOUL styr TON, ICP styr URVAL. Gränsen står utskriven i LeadsControls.
      // Rösten är delad: samma dokument formar både utskick och svar.
      { href: "/settings/soul", label: { sv: "Röst och tonläge", en: "Voice and tone" } }
    ]
  },
  {
    /**
     * En EGEN grupp, direkt under röstdokumentet.
     *
     * Notiser och tema hör inte till "Vad agenterna vet" — de är inget agenten
     * läser — och inte heller till "Kontot", som handlar om bolaget och
     * pengarna. Båda handlar om DIG: när du vill bli störd, och vad du vill
     * titta på medan du jobbar.
     *
     * Det är också den enda grupp vars innehåll är personligt och inte delat.
     * Notisraden ligger per användare (migration 043) och temat i en cookie i
     * den här webbläsaren — två kollegor i samma arbetsyta ser alltså olika
     * svar här, vilket är rätt och värt att veta innan man ändrar något.
     */
    label: { sv: "Dina inställningar", en: "Your preferences" },
    routes: [
      { href: "/settings/notiser", label: { sv: "Notiser", en: "Notifications" } },
      { href: "/settings/tema", label: { sv: "Tema", en: "Theme" } }
    ]
  },
  {
    label: { sv: "Vad agenterna får göra", en: "What the agents may do" },
    routes: [
      {
        href: "/settings/leads",
        label: { sv: "Leads: målgrupp och autonomi", en: "Leads: audience and autonomy" },
        product: "leads"
      },
      {
        href: "/settings/regler",
        label: {
          sv: "Kundtjänst: fack och autosvar",
          en: "Support: categories and auto-replies"
        },
        product: "support"
      },
      { href: "/settings/mailboxes", label: { sv: "Inkorgar", en: "Mailboxes" }, product: "support" }
    ]
  },
  {
    label: { sv: "Kontot", en: "Account" },
    routes: [
      { href: "/settings", label: { sv: "Företaget", en: "Company" } },
      { href: "/settings/team", label: { sv: "Team", en: "Team" }, doldIDemo: true },
      { href: "/settings/billing", label: { sv: "Plan och fakturering", en: "Plan and billing" } },
      { href: "/settings/addons", label: { sv: "Tillägg", en: "Add-ons" } }
    ]
  }
];

/**
 * Menyn, filtrerad på tre oberoende saker.
 *
 *  * `products`   — vad arbetsytan får använda. Rättighet, serverbeslut.
 *  * `visar`      — vad LÄGET visar just nu (Duo / Leads / Support). Menyn
 *                   listade tidigare bara på rättighet, så den som smalnade av
 *                   vyn till Support fick fortfarande se leads-agentens
 *                   inställningar i sidokolumnen — vilket motsäger kontrollen
 *                   användaren precis rörde.
 *  * `vy`         — demovyn döljer poster som avslöjar VÅR arbetsyta.
 *
 * `visar` är valfri av en anledning: `Vy`-typen bor i lib/vy.ts som är
 * server-only, och den här filen importeras av klientkomponenter.
 */
export function settingsGroupsForProducts(
  products: readonly ProductKey[],
  options: {
    visar?: (product: ProductKey) => boolean;
    vy?: "admin" | "demo" | "kund";
  } = {}
): SettingsGroup[] {
  const { visar, vy } = options;
  return settingsGroups
    .map((group) => ({
      ...group,
      routes: group.routes.filter((route) => {
        // Även i kundläge. Posten döljs för att den listar VÅR arbetsytas
        // medlemsadresser, och en admin som tittar hos en kund tittar just då
        // inte på sin egen arbetsyta — raden hade alltså visat fel bolags
        // adresser i fel sammanhang.
        if (route.doldIDemo && vy !== "admin") return false;
        if (!route.product) return true;
        if (!products.includes(route.product)) return false;
        return visar ? visar(route.product) : true;
      })
    }))
    .filter((group) => group.routes.length > 0);
}

/** Sektioner demovyn inte visar. Speglar `doldIDemo` ovan — grinden sitter i SettingsSection. */
const demoDoldaSektioner = new Set(["team"]);

export function sektionDoldIDemo(section: string): boolean {
  return demoDoldaSektioner.has(section);
}

/**
 * Vilken inställningssida en /settings-adress pekar ut.
 *
 * EN dispatcher, precis som WorkspaceSection. Sidorna låg tidigare som sex
 * nästan identiska page.tsx-filer, och varje ny inställning krävde en sjunde.
 * Okänd slug ger null, som anroparen översätter till 404.
 *
 * `arbetsyta` är BORTA. Sidan var en mock-sammanfattning av arbetsytan, och
 * sammanfattningen är numera startsidan (se StartView). Två sammanfattningar
 * av samma sak är en för många, och den som låg i inställningarna var den som
 * ingen hittade.
 */
export type SettingsSectionKey =
  | "foretaget"
  | "team"
  | "billing"
  | "addons"
  | "affarskontext"
  | "kunskapsbas"
  | "soul"
  | "leads"
  | "regler"
  | "mailboxes"
  | "notiser"
  | "tema";

const settingsSections: Record<string, SettingsSectionKey> = {
  "": "foretaget",
  team: "team",
  billing: "billing",
  addons: "addons",
  affarskontext: "affarskontext",
  kunskapsbas: "kunskapsbas",
  soul: "soul",
  leads: "leads",
  regler: "regler",
  mailboxes: "mailboxes",
  notiser: "notiser",
  tema: "tema"
};

/**
 * Vilken produkt en inställningssida kräver. Saknas den är sidan delad.
 *
 * Det här är grinden, inte menyfiltret: att gruppen inte RENDERAS för en
 * supportkund hindrar ingen från att skriva /settings/leads i adressfältet.
 *
 * `soul` står inte längre här. Röstdokumentet är delat — se settingsGroups.
 */
const settingsSectionProduct: Partial<Record<SettingsSectionKey, ProductKey>> = {
  leads: "leads",
  regler: "support",
  mailboxes: "support"
};

export function settingsSectionForSlug(slug: readonly string[]): SettingsSectionKey | null {
  if (slug.length > 1) return null;
  return settingsSections[slug[0] ?? ""] ?? null;
}

/**
 * Vilken produkt inställningssidan på `pathname` tillhör, eller null.
 *
 * Tar båda ytorna: `/settings/leads` och `/admin/installningar/leads` är samma
 * sida. Finns för att skalet ska kunna dirigera bort den som smalnat av läget
 * medan de står på en sida läget inte längre visar — utan att varje anropsplats
 * behöver känna till vilken yta den renderas på.
 */
export function produktForInstallningsvag(pathname: string): ProductKey | null {
  const rot = pathname.startsWith("/admin/installningar")
    ? "/admin/installningar"
    : pathname.startsWith("/settings")
      ? "/settings"
      : null;
  if (rot === null) return null;

  const rest = pathname.slice(rot.length).replace(/^\//, "");
  if (!rest) return null;

  const section = settingsSectionForSlug([rest]);
  return section ? productForSettingsSection(section) : null;
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
