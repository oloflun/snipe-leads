import { NextResponse } from "next/server";
import { cookies } from "next/headers";
import { requireSnajpTenant, SnajpTenantError } from "@/lib/snajp/tenant";
import { SKV_TOKEN_COOKIE } from "@/lib/skatteverket/oauth";
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

    // Skatteverket-tokenen följer med NÄR den finns, och bara på den inloggade
    // vägen. Den bärs av en httpOnly-kaka (se app/api/skatteverket/callback),
    // så klientens JavaScript kan varken läsa eller sätta den — headern kan
    // alltså inte förfalskas av en sida i webbläsaren.
    //
    // Organisationsnumret skickas MEDVETET INTE: backenden läser det ur sin
    // egen tenantrad. Ett orgnr som kommer utifrån är ett fält någon kan byta
    // ut, och det är exakt vad INV-SEC-002 finns för att förhindra.
    const skvToken = (await cookies()).get(SKV_TOKEN_COOKIE)?.value;
    let medToken: RequestInit = skvToken
      ? { ...init, headers: { ...(init.headers ?? {}), "X-Skatteverket-Token": skvToken } }
      : init;

    let backendPath = path;
    const metod = String(medToken.method ?? "GET").toUpperCase();
    const arSkrivning = metod !== "GET" && metod !== "HEAD";
    if (tenant.impersonerar && arSkrivning) {
      // Admin som tittar som kund: allt som SKRIVS är test. Läsning måste
      // visa kundens riktiga inkorg — annars gömmer `?is_test=true` på GET
      // de skarpa ärendena och admin tror att profilen är tom.
      // Query-parametern täcker leads/prospects; JSON-kroppen chat, batch, mock.
      if (!backendPath.includes("is_test=")) {
        backendPath += (backendPath.includes("?") ? "&" : "?") + "is_test=true";
      }
      if (typeof medToken.body === "string" && medToken.body.length > 0) {
        try {
          const parsed: unknown = JSON.parse(medToken.body);
          if (parsed && typeof parsed === "object" && !Array.isArray(parsed)) {
            medToken = { ...medToken, body: JSON.stringify({ ...parsed, is_test: true }) };
          }
        } catch {
          // Inte JSON — lämna kroppen orörd.
        }
      }
    }

    return await proxyWithApiKey(backendPath, medToken, tenant.apiKey, tenant.userId, tenant.isDemo);
  } catch (error) {
    if (error instanceof SnajpTenantError) {
      // `kod` går med, så att gränssnittet kan skilja "inte aktiverad ännu"
      // från "något gick sönder" utan att tolka svensk text.
      return NextResponse.json(
        { error: error.message, kod: error.kod },
        { status: error.status }
      );
    }
    throw error;
  }
}
