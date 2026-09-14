import "server-only";

import { SNAJP_SUPPORT_URL } from "@/app/api/snajp-support/_lib";
import { readJsonBody } from "@/lib/http/json";

/**
 * En egen backend-tenant per arbetsyta, skapad i DRIFT.
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
 * migration 040 ger det. Alltså: inget nytt kodberoende per konto, ingen
 * deploy, ingen configfil.
 *
 * ## Riktiga kunder går samma väg sedan migration 061
 *
 * Tidigare stod här att riktiga kunder går via `scripts/onboard_tenant.py`, med
 * motiveringen att en människa väljer slug och kontrollerar organisationsnumret.
 * Priset visade sig vara för högt: en kund som registrerade sig fick INGEN
 * tenant alls, `workspaces.slug` blev null, och `requireSnajpTenant()` svarade
 * 409 på varje inloggad yta tills någon av oss körde skriptet för hand.
 * Produkten var alltså oanvändbar för varje ny kund fram till nästa gång vi
 * tittade.
 *
 * Slugmönstren hålls isär (`testkund-` respektive `kund-`) därför att
 * databasfunktionerna gör det: `link_test_tenant` sätter `is_demo` och tar bara
 * det första, `link_workspace_tenant` tar bara det andra. Mönstren måste stämma
 * med regexarna i migration 040 och 061 — ändras det ena utan det andra avvisas
 * varje koppling tyst.
 *
 * Vad som fortfarande kräver en människa: den PUBLIKA chatten på kundens egen
 * domän. Den läser `lib/tenants/<slug>.ts` (logotyp, palett, startfrågor) och
 * finns inte för en arbetsyta som kopplats automatiskt — se TENANTS.md steg 4.
 * Det är rätt gräns: kundens inloggade arbetsyta ska fungera direkt, kundens
 * publika varumärkessida ska inte skapas av en gissning.
 */

export type Backendtenant = {
  slug: string;
  tenantId: string;
  apiKey: string;
};

/** Bakåtkompatibelt namn. Testarbetsytorna kallade den så innan riktiga kunder fick samma väg. */
export type Testtenant = Backendtenant;

/** `<prefix><8 tecken ur workspace-id>`. Måste matcha regexarna i migration 040/061. */
function tenantSlug(prefix: string, workspaceId: string): string {
  const rent = workspaceId.replace(/[^a-z0-9]/gi, "").toLowerCase();
  return `${prefix}${rent.slice(0, 8)}`;
}

/** `testkund-<8>`. Måste matcha regexen i migration 040. */
export function testtenantSlug(workspaceId: string): string {
  return tenantSlug("testkund-", workspaceId);
}

/** `kund-<8>`. Måste matcha regexen i migration 061. */
export function kundtenantSlug(workspaceId: string): string {
  return tenantSlug("kund-", workspaceId);
}

/**
 * Skapar (eller återanvänder) tenanten och utfärdar en nyckel.
 *
 * Backendens `create_tenant` är en upsert på slug, så ett omtag efter ett
 * avbrutet försök ger samma tenant och en ny nyckel — inte en andra tenant med
 * halva kundens data. `ss_api_keys` är additiv, så en omkörning roterar
 * ingenting: den gamla nyckeln fortsätter gälla tills den skrivs över.
 */
export async function utfardaTenantnyckel(
  slug: string,
  namn: string,
  /**
   * Uppstarten har råd att vänta ut en kallstart; en sidladdning har inte det.
   *
   * Defaulten gäller onboardingen, där ett avbrutet försök lämnar arbetsytan
   * halvkopplad. Läkningsvägarna i `requireSnajpTenant()` skickar ett kortare
   * tak: där sitter någon och väntar på en sida, och 60 sekunders tystnad är
   * värre än ett fel som säger vad som hände.
   */
  timeoutMs = 60_000
): Promise<Backendtenant> {
  const masterKey = process.env.SNAJP_MASTER_API_KEY;
  if (!masterKey) {
    throw new Error(
      "SNAJP_MASTER_API_KEY saknas i den här miljön — arbetsytan kan inte få en egen tenant."
    );
  }

  const response = await fetch(`${SNAJP_SUPPORT_URL}/api/keys`, {
    method: "POST",
    headers: { "Content-Type": "application/json", "X-API-Key": masterKey },
    body: JSON.stringify({ tenant_name: namn, slug }),
    signal: AbortSignal.timeout(timeoutMs)
  });

  if (!response.ok) {
    throw new Error(`Backenden avvisade tenantskapandet (${response.status}).`);
  }

  // readJsonBody och inte .json(): en instans som vaknar ur viloläge svarar
  // HTML, och ett rått .json() kastar då "Unexpected end of JSON input" mitt i
  // onboardingen (INV-API-001).
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

/** Testarbetsytans tenant. Sluggen är `testkund-<8>` och `link_test_tenant` tar den. */
export async function skapaTesttenant(
  workspaceId: string,
  namn: string
): Promise<Backendtenant> {
  return utfardaTenantnyckel(testtenantSlug(workspaceId), namn);
}

/** En riktig kunds tenant. Sluggen är `kund-<8>` och `link_workspace_tenant` tar den. */
export async function skapaKundtenant(
  workspaceId: string,
  namn: string,
  timeoutMs?: number
): Promise<Backendtenant> {
  return utfardaTenantnyckel(kundtenantSlug(workspaceId), namn, timeoutMs);
}
