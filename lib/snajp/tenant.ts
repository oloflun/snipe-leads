import { getWorkspaceContext } from "@/lib/workspace";
import { getTenant } from "@/lib/tenants";

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
};

export async function requireSnajpTenant(): Promise<SnajpTenant> {
  const context = await getWorkspaceContext();
  if (!context) {
    throw new SnajpTenantError(401, "Du måste vara inloggad.");
  }

  const { workspace } = context;

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

  const apiKey = process.env[tenant.supportKeyEnv];
  if (!apiKey) {
    // Samma resonemang som MissingTenantKeyError i chat-proxyn: utan nyckel
    // svarar vi inte som ett annat bolag.
    throw new SnajpTenantError(
      503,
      `${tenant.supportKeyEnv} är inte satt i den här miljön. ${tenant.name} kan inte nå backenden förrän den finns.`
    );
  }

  return { workspaceId: workspace.id, slug: workspace.slug, apiKey };
}
