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
    workspaceName: context.workspace.name,
    signedIn: true,
    isDemo: context.workspace.is_demo,
    isPlatformAdmin: Boolean(await getPlatformAdmin())
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
