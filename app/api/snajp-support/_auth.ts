import { NextResponse } from "next/server";
import { requireSnajpTenant, SnajpTenantError } from "@/lib/snajp/tenant";
import { proxyWithApiKey } from "./_lib";

/**
 * Vidarebefordran för INLOGGAD trafik: inkorg, utkast, regler, kunskapsbas,
 * leads och röstdokument.
 *
 * Före det här lagret gjorde ingen route under app/api/ någon sessionskontroll,
 * och proxy.ts-matchern täcker inte /api. Följden var mätbar mot produktion:
 * GET /api/snajp-support/leads/soul svarade 200 med innehåll utan cookie, och
 * en PUT nådde ända fram till backendens typvalidering. Vem som helst kunde
 * skriva demo-agentens röstdokument.
 *
 * Matchern i proxy.ts utökas medvetet INTE till /api: den svarar med en
 * omdirigering till /login, vilket är fel form för ett API-anrop och skulle
 * dölja 401:an nedan. Grinden hör hemma i routen.
 */
export async function proxyAsTenant(path: string, init: RequestInit) {
  try {
    const tenant = await requireSnajpTenant();
    return await proxyWithApiKey(path, init, tenant.apiKey, tenant.userId);
  } catch (error) {
    if (error instanceof SnajpTenantError) {
      return NextResponse.json({ error: error.message }, { status: error.status });
    }
    throw error;
  }
}
