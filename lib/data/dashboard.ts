import { getPlatformAdmin } from "@/lib/auth/admin";
import { getWorkspaceContext } from "@/lib/workspace";
import { hasDatabase } from "@/lib/db";
import { SCOPE_COOKIE, isProductKey, type ProductKey, type Scope } from "@/lib/routes";
import { isAddonKey, type AddonKey } from "@/lib/addons";
import { DEMO_ARBETSYTA, aktivVy, type Vy } from "@/lib/vy";
import { cookies } from "next/headers";

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
  workspaceName: string | null;
  signedIn: boolean;
  /** Demo-läge: egen instans utan förladdad data, begränsat antal körningar. */
  isDemo: boolean;
  /**
   * Plattformsadmin — enbart för att kunna VISA vägen till /admin.
   *
   * Grinden är och förblir `requirePlatformAdmin()` i app/admin/layout.tsx, som
   * svarar 404. Det här fältet är en navigationsledtråd, inte ett villkor.
   */
  isPlatformAdmin: boolean;
  /**
   * Plattformsadminens aktiva yta. `demo` betyder att hela trädet renderas som
   * en kundinloggning mot demokontot — se lib/vy.ts. Alltid `admin` för alla
   * andra, och avgjort på servern: fältet är resultatet av grinden, inte
   * ingången till den.
   */
  vy: Vy;
  /**
   * Läget vid första renderingen — Duo, bara Leads eller bara Support.
   *
   * Avgörs på servern ur cookien så att `/settings/*` kan grinda på det, och
   * så att klienten slipper rätta sig efter mount. Alltid ett värde arbetsytan
   * faktiskt får se: en cookie som säger "leads" i en support-arbetsyta ger
   * "support", inte en tom vy.
   */
  initialScope: Scope;
};

const ALL_PRODUCTS: ProductKey[] = ["leads", "support"];

/**
 * Anonymous and unconfigured environments both land here: the demo dataset with
 * both products, which is what /dashboard has always shown without auth.
 */
const ANONYMOUS: DashboardState = {
  products: ALL_PRODUCTS,
  addons: [],
  workspaceName: null,
  signedIn: false,
  isDemo: false,
  isPlatformAdmin: false,
  vy: "admin",
  initialScope: "both"
};

/**
 * Läget ur cookien, begränsat till vad arbetsytan äger.
 *
 * En arbetsyta med EN produkt har inget läge att välja: allt annat än den
 * produkten vore en tom skärm med en meny som inte leder någonstans.
 */
async function scopeFranCookie(products: readonly ProductKey[]): Promise<Scope> {
  if (products.length < 2) {
    return products[0] ?? "both";
  }
  const rad = (await cookies()).get(SCOPE_COOKIE)?.value ?? "";
  if (rad === "both") return "both";
  if (isProductKey(rad) && products.includes(rad)) return rad;
  return "both";
}

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
  const vy = await aktivVy();

  // Demovyn ska se ut som demokontots egen inloggning, inte som adminens
  // arbetsyta med annan data i. Namnet i huvudet och produktlistan kommer
  // därför från demokontot — arbetsytans egna värden vore fel bolag och,
  // om arbetsytan bara hade en produkt, fel meny.
  if (vy === "demo") {
    return {
      products: ALL_PRODUCTS,
      addons: [],
      workspaceName: DEMO_ARBETSYTA,
      signedIn: true,
      // Medvetet false. Flaggan går vidare som X-Snajp-Demo och sänker
      // löptaket; demovyn ska kunna köra skarpa testkörningar. Att vyn ÄR en
      // demo syns på `vy`, som är det fältet som faktiskt betyder det.
      isDemo: false,
      isPlatformAdmin: true,
      vy,
      initialScope: await scopeFranCookie(ALL_PRODUCTS)
    };
  }

  return {
    products,
    addons: (context.workspace.addons ?? []).filter(isAddonKey),
    workspaceName: context.workspace.name,
    signedIn: true,
    isDemo: context.workspace.is_demo,
    isPlatformAdmin: Boolean(await getPlatformAdmin()),
    vy,
    initialScope: await scopeFranCookie(products)
  };
}

/**
 * `workspaceHasData` och `variant` är BORTA, och det var inte en förenkling.
 *
 * Sonden frågade `public.companies`. Den tabellen skrivs inte av någon kodväg
 * i appen — den är ett fossil från mock-eran, och den hade noll rader i
 * development medan `prospects` hade 2, `business_contexts` 5 och
 * `ss_knowledge_base` 51. Alltså returnerade den false för VARJE arbetsyta,
 * alltid, och `variant` var permanent "fresh".
 *
 * Följden var mätbar i skärmdump: startsidan kortslöt till "Inget här ännu" för
 * varje inloggad kund, oavsett hur mycket de hade konfigurerat. Översikten
 * bakom den gick aldrig att se.
 *
 * Den ersätts inte av en bättre sond. Översikten ÄR sitt eget tomläge: varje
 * ruta visar sin nolla, varje sektion säger vad som kommer att stå där, och
 * saknas underlaget står det överst. En sida som döljer siffrorna för att de är
 * noll döljer också att de är noll.
 */
