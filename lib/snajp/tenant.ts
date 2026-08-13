import { createAdminClient } from "@/lib/supabase/admin";
import { getWorkspaceContext } from "@/lib/workspace";

// SERVER-ONLY. Modulen läser SUPABASE_SERVICE_ROLE_KEY och returnerar tenantens
// API-nyckel i klartext — den får aldrig importeras från en klientkomponent.
//
// Kopplingen mellan snipe-leads-inloggningen och en Snajp-Support-tenant.
//
// Ett workspace = en tenant. Raden i snajp_workspace_tenants skapas lat första
// gången någon i workspacet öppnar Snajp-Support, genom ett anrop till backendens
// POST /api/keys med master-nyckeln. Ingen seed, inga .env-ändringar per kund.
//
// Tabellen har RLS utan policyer och läses bara med service-role-nyckeln —
// tenantens API-nyckel når aldrig webbläsaren.

const SNAJP_SUPPORT_URL = process.env.SNAJP_SUPPORT_URL ?? "http://127.0.0.1:8000";
const MASTER_KEY = process.env.SNAJP_MASTER_API_KEY ?? "";

export type SnajpTenant = {
  tenantId: string;
  tenantSlug: string | null;
  apiKey: string;
};

export class SnajpTenantError extends Error {
  constructor(
    message: string,
    readonly status: number
  ) {
    super(message);
    this.name = "SnajpTenantError";
  }
}

type LinkRow = {
  tenant_id: string;
  tenant_slug: string | null;
  api_key: string;
};

async function readLink(workspaceId: string): Promise<LinkRow | null> {
  const supabase = createAdminClient();
  const { data, error } = await supabase
    .from("snajp_workspace_tenants")
    .select("tenant_id, tenant_slug, api_key")
    .eq("workspace_id", workspaceId)
    .maybeSingle<LinkRow>();

  if (error) {
    throw new SnajpTenantError(
      `Kunde inte läsa arbetsytans koppling: ${error.message}`,
      500
    );
  }
  return data;
}

async function provision(workspaceId: string, workspaceName: string): Promise<LinkRow> {
  if (!MASTER_KEY) {
    throw new SnajpTenantError(
      "SNAJP_MASTER_API_KEY saknas i miljön — kan inte skapa en arbetsyta åt kunden.",
      503
    );
  }

  // Slugen härleds ur workspace-id:t så den är unik även om två bolag heter
  // likadant. Backendens create_tenant är idempotent på slug, så ett omtag
  // efter ett avbrutet anrop återanvänder samma tenant i stället för att skapa en till.
  const slug = `ws-${workspaceId}`;
  const response = await fetch(`${SNAJP_SUPPORT_URL}/api/keys`, {
    method: "POST",
    headers: { "Content-Type": "application/json", "X-API-Key": MASTER_KEY },
    body: JSON.stringify({
      tenant_name: workspaceName.slice(0, 80),
      slug,
      label: "Snipra-inloggning"
    }),
    cache: "no-store"
  });

  if (!response.ok) {
    const detail = await response.text().catch(() => "");
    throw new SnajpTenantError(
      `Backenden kunde inte skapa arbetsytan (${response.status}). ${detail}`.trim(),
      502
    );
  }

  const created = (await response.json()) as {
    api_key: string;
    tenant_id: string;
    tenant_slug: string;
    key_prefix: string;
  };

  const supabase = createAdminClient();
  const { error } = await supabase.from("snajp_workspace_tenants").upsert(
    {
      workspace_id: workspaceId,
      tenant_id: created.tenant_id,
      tenant_slug: created.tenant_slug,
      api_key: created.api_key,
      key_prefix: created.key_prefix,
      updated_at: new Date().toISOString()
    },
    { onConflict: "workspace_id" }
  );

  if (error) {
    // Nyckeln finns nu bara i backenden (som hash) och kan inte visas igen.
    // Hellre ett tydligt fel än en tyst koppling som saknar nyckel.
    throw new SnajpTenantError(
      `Arbetsytan skapades men kopplingen kunde inte sparas: ${error.message}`,
      500
    );
  }

  return {
    tenant_id: created.tenant_id,
    tenant_slug: created.tenant_slug,
    api_key: created.api_key
  };
}

/**
 * Tenanten för den inloggade användarens organisation.
 *
 * Kastar SnajpTenantError(401) när ingen är inloggad — anroparen ska aldrig
 * kunna råka falla tillbaka på demo-tenanten.
 */
export async function requireSnajpTenant(): Promise<SnajpTenant> {
  const context = await getWorkspaceContext();
  if (!context) {
    throw new SnajpTenantError("Du måste vara inloggad.", 401);
  }

  const workspaceId = context.workspace.id;
  const link =
    (await readLink(workspaceId)) ??
    (await provision(workspaceId, context.workspace.name ?? "Arbetsyta"));

  return {
    tenantId: link.tenant_id,
    tenantSlug: link.tenant_slug,
    apiKey: link.api_key
  };
}
