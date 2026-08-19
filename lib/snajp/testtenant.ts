import "server-only";

import { SNAJP_SUPPORT_URL } from "@/app/api/snajp-support/_lib";
import { readJsonBody } from "@/lib/http/json";

/**
 * En egen backend-tenant per testarbetsyta, skapad i DRIFT.
 *
 * ## Varför
 *
 * Alla testkonton pekade tidigare på den delade tenanten `testkund`. De delade
 * därmed inkorg, kunskapsbas och röstdokument — en kunds villkor kunde grunda
 * ett svar till en annan kunds kund, och kunskapsbasen växte med policys från
 * olika bolag. Grundningsgrinden ser en träff; den kan inte se att artikeln kom
 * från fel företag.
 *
 * ## Varför det går nu
 *
 * Backendens `POST /api/keys` (master-nyckel) skapar tenant och nyckel i drift.
 * Det som saknades var ett ställe för nyckeln som inte är en miljövariabel —
 * migration 040 ger det. Alltså: inget nytt kodberoende per testkonto, ingen
 * deploy, ingen configfil.
 *
 * ## Vad som INTE händer här
 *
 * Riktiga kunder går fortfarande via `scripts/onboard_tenant.py`. Den vägen har
 * en människa som väljer slug, kontrollerar organisationsnumret och sätter en
 * miljövariabel — och den ska ha det. Den här funktionen skapar bara tenants
 * vars slug börjar på `testkund-`, vilket också är vad databasfunktionen
 * `link_test_tenant` accepterar.
 */

export type Testtenant = {
  slug: string;
  tenantId: string;
  apiKey: string;
};

/** `testkund-<8 tecken ur workspace-id>`. Måste matcha regexen i migration 040. */
export function testtenantSlug(workspaceId: string): string {
  const rent = workspaceId.replace(/[^a-z0-9]/gi, "").toLowerCase();
  return `testkund-${rent.slice(0, 8)}`;
}

/**
 * Skapar (eller återanvänder) tenanten och utfärdar en nyckel.
 *
 * Backendens `create_tenant` är en upsert på slug, så ett omtag efter ett
 * avbrutet försök ger samma tenant och en ny nyckel — inte en andra tenant med
 * halva kundens data.
 */
export async function skapaTesttenant(
  workspaceId: string,
  namn: string
): Promise<Testtenant> {
  const masterKey = process.env.SNAJP_MASTER_API_KEY;
  if (!masterKey) {
    throw new Error(
      "SNAJP_MASTER_API_KEY saknas i den här miljön — en testarbetsyta kan inte få en egen tenant."
    );
  }

  const slug = testtenantSlug(workspaceId);
  const response = await fetch(`${SNAJP_SUPPORT_URL}/api/keys`, {
    method: "POST",
    headers: { "Content-Type": "application/json", "X-API-Key": masterKey },
    body: JSON.stringify({ tenant_name: namn, slug }),
    // Render kallstartar på gratisnivån. En onboarding som faller på en
    // uppvaknande backend hade lämnat arbetsytan halvkopplad.
    signal: AbortSignal.timeout(60_000)
  });

  if (!response.ok) {
    throw new Error(`Backenden avvisade tenantskapandet (${response.status}).`);
  }

  // readJsonBody och inte .json(): en Render-instans som vaknar ur viloläge
  // svarar HTML, och ett rått .json() kastar då "Unexpected end of JSON input"
  // mitt i onboardingen (INV-API-001).
  const kropp = await readJsonBody<{
    api_key?: string;
    tenant_id?: string;
    tenant_slug?: string;
  }>(response);

  if (!kropp?.api_key || !kropp.tenant_id) {
    throw new Error("Backenden svarade utan nyckel eller tenant-id.");
  }

  return { slug: kropp.tenant_slug ?? slug, tenantId: kropp.tenant_id, apiKey: kropp.api_key };
}
