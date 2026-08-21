import { sqlAsUser } from "@/lib/db";
import { getWorkspaceContext } from "@/lib/workspace";
import { getTenant } from "@/lib/tenants";
import { DEMO_TENANT_SLUG, aktivVy } from "@/lib/vy";

/**
 * Arbetsytans egen backend-nyckel, för tenants utan configfil.
 *
 * Går genom en security definer-funktion och inte en SELECT: tabellen
 * `workspace_tenant_keys` har RLS utan policies, alltså noll rader för appen.
 * Funktionen tar heller ingen workspace_id — med en parameter hade den varit en
 * uppslagsbok över alla arbetsytors nycklar, och en bugg i en anropsplats hade
 * räckt för att läsa fel kunds.
 */
async function tenantApiKeyForWorkspace(userId: string): Promise<string | undefined> {
  const rows = await sqlAsUser<{ nyckel: string | null }>(
    userId,
    "select public.tenant_api_key_for_current_workspace() as nyckel"
  );
  return rows[0]?.nyckel ?? undefined;
}

/**
 * Vilken kund ett inloggat anrop mot Snajp-Support-backenden gäller.
 *
 * Tenanten härleds ur SESSIONEN, aldrig ur något klienten skickar. Det är hela
 * poängen: den tidigare catch-all-proxyn skickade ingen tenant alls, föll
 * tillbaka på demonyckeln, och varje inloggad kunds inkorg, kunskapsbas och
 * röstdokument pekade därmed på demo-tenanten Nordlys Handel. Två kunder hade
 * skrivit i samma SOUL.
 *
 * Den publika chatten (chat/ och jobs/) går INTE genom den här modulen. Den är
 * anonym med flit — kunden publicerar länken själv — och skyddas av rate limit,
 * inte av inloggning.
 */

export class SnajpTenantError extends Error {
  constructor(
    readonly status: number,
    message: string
  ) {
    super(message);
    this.name = "SnajpTenantError";
  }
}

export type SnajpTenant = {
  workspaceId: string;
  slug: string;
  apiKey: string;
  /**
   * auth.users.id. Går vidare till backenden som X-Snajp-User och används
   * enbart till timtaket per användare (migration 019). Backenden behandlar
   * det som ett ogenomskinligt id — den slår aldrig upp det mot auth.users,
   * och en förfalskad rubrik kan därför bara ge en SNÄVARE kvot, aldrig en
   * vidare. Tenant-taket sitter kvar oavsett vad som står här.
   */
  userId: string;
  /** Demo-workspace — går till backenden som X-Snajp-Demo för ett lägre löptak. */
  isDemo: boolean;
};

export async function requireSnajpTenant(): Promise<SnajpTenant> {
  const context = await getWorkspaceContext();
  if (!context) {
    throw new SnajpTenantError(401, "Du måste vara inloggad.");
  }

  const { workspace, user } = context;

  /**
   * Demovyn — plattformsadmin, och ENBART plattformsadmin, mot demokontot.
   *
   * Grenen ligger före arbetsytans slug med flit: i demoläget ska ingen del av
   * adminens egen tenant nås, inte heller om den råkar vara felkonfigurerad.
   *
   * `aktivVy()` slår upp `platform_admins` och failar stängt (se lib/vy.ts),
   * så cookien i sig är inte ett tenant-byte. Det är hela skillnaden mot den
   * bugg filens docstring ovan beskriver: där föll varje inloggad kund tillbaka
   * på demonyckeln, här kan bara den som redan når /admin göra det, och bara
   * mot en enda hårdkodad tenant.
   *
   * Nyckeln är demonyckeln. `SNAJP_INTERNAL_API_KEY` är samma sträng i den här
   * miljön (se app/api/snajp-support/_lib.ts) och står kvar som reserv för att
   * en saknad variabel annars gör demovyn oöppningsbar utan att säga varför.
   */
  if ((await aktivVy()) === "demo") {
    const apiKey = process.env.SNAJP_DEMO_API_KEY || process.env.SNAJP_INTERNAL_API_KEY;
    if (!apiKey) {
      throw new SnajpTenantError(
        503,
        "SNAJP_DEMO_API_KEY är inte satt i den här miljön. Demovyn kan inte nå backenden förrän den finns."
      );
    }
    return {
      workspaceId: workspace.id,
      slug: DEMO_TENANT_SLUG,
      apiKey,
      userId: user.id,
      // Se lib/data/dashboard.ts: demovyn ska köra skarpt, inte med sänkt tak.
      isDemo: false
    };
  }

  // Ingen slug betyder att workspacet aldrig kopplats till en kund i
  // ss_tenants. Att då tyst låna demo-tenantens data är precis felet vi
  // stänger — ett begripligt fel är alltid bättre än fel kunds svar.
  if (!workspace.slug) {
    throw new SnajpTenantError(
      409,
      "Arbetsytan är inte kopplad till någon kund ännu. Sätt workspaces.slug och ss_tenant_id."
    );
  }

  const tenant = getTenant(workspace.slug);
  if (!tenant) {
    throw new SnajpTenantError(
      409,
      `Ingen configfil för "${workspace.slug}" i lib/tenants. Se TENANTS.md steg 4.`
    );
  }

  /**
   * Två nyckelvägar, och ordningen mellan dem är inte utbytbar.
   *
   * En kund med configfil har sin nyckel i en miljövariabel. En testarbetsyta
   * har en EGEN tenant som skapades i drift (migration 040) och vars nyckel
   * ligger i databasen — för den är miljövariabeln fel svar: `SNAJP_KEY_TESTKUND`
   * pekar på den GAMLA delade tenanten, alltså en delad kunskapsbas. Att låta
   * env vinna hade tyst återinfört precis det vi byggde bort.
   */
  const apiKey = tenant.perWorkspaceKey
    ? await tenantApiKeyForWorkspace(user.id)
    : process.env[tenant.supportKeyEnv];

  if (!apiKey && tenant.perWorkspaceKey) {
    throw new SnajpTenantError(
      409,
      "Testarbetsytan har ingen egen backend-nyckel sparad. Kör onboardingen igen " +
        "eller koppla arbetsytan med scripts/railway_tenant_keys.py."
    );
  }

  if (!apiKey) {
    // Samma resonemang som MissingTenantKeyError i chat-proxyn: utan nyckel
    // svarar vi inte som ett annat bolag.
    throw new SnajpTenantError(
      503,
      `${tenant.supportKeyEnv} är inte satt i den här miljön. ${tenant.name} kan inte nå backenden förrän den finns.`
    );
  }

  return {
    workspaceId: workspace.id,
    slug: workspace.slug,
    apiKey,
    userId: user.id,
    isDemo: workspace.is_demo
  };
}
