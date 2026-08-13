import { NextResponse } from "next/server";
import { requireSnajpTenant, SnajpTenantError } from "@/lib/snajp/tenant";
import { proxyToBackend } from "./_lib";

// Gemensam grind för alla /api/snajp-support-routes: ingen inloggning, ingen data.
// Tenantens nyckel hämtas server-side och sätts som X-API-Key mot backenden, så
// backendens tenant-separation gör att en kund bara kan nå sin egen arbetsyta.

export async function proxyAsTenant(path: string, init: RequestInit) {
  try {
    const tenant = await requireSnajpTenant();
    return await proxyToBackend(path, init, tenant.apiKey);
  } catch (error) {
    if (error instanceof SnajpTenantError) {
      return NextResponse.json({ error: error.message }, { status: error.status });
    }
    throw error;
  }
}
