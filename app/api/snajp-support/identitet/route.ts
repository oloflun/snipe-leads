import { NextResponse } from "next/server";
import { requireSnajpTenant, SnajpTenantError, snajpIdentitet } from "@/lib/snajp/tenant";
import { IDENTITET_HUVUD } from "../_auth";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

/**
 * Vem är inloggad i den här webbläsaren just nu (INV-SEC-014).
 *
 * DashboardProvider frågar här vid varje navigering, vid fokus och när fliken
 * blir synlig, och laddar om när svaret skiljer sig från layoutens identitet.
 * Kunddemon 2026-11-24 visade varför: en gammal flik med kundens skal hämtade
 * paneler med adminens session, eftersom inget i klienten märkte bytet.
 *
 * Kör samma `requireSnajpTenant` som proxyn, så att identiteten räknas i samma
 * läge som proxyns svar. Utan session svarar den 401, med identiteten för
 * "utloggad": just det fall fliken ska märka. Övriga tenantfel (en arbetsyta
 * som inte är aktiverad än) gäller panelerna, inte frågan om vem som är
 * inloggad, och ger 200 här; panelerna visar dem själva.
 */
export async function GET() {
  let status = 200;
  try {
    await requireSnajpTenant();
  } catch (error) {
    if (!(error instanceof SnajpTenantError)) throw error;
    if (error.status === 401) status = 401;
  }
  const identitet = await snajpIdentitet();
  return NextResponse.json(
    { identitet },
    {
      status,
      headers: {
        [IDENTITET_HUVUD]: identitet,
        "Cache-Control": "private, no-store",
        Vary: "Cookie"
      }
    }
  );
}
