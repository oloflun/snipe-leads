import { NextResponse } from "next/server";
import { LASROLL, LASROLL_FEL } from "@/lib/auth/lasroll";
import { requireSnajpTenant, SnajpTenantError, snajpIdentitet, svarForTenantfel } from "@/lib/snajp/tenant";
import { proxyWithApiKey } from "./_lib";

/** Svarshuvudet som säger vilken identitet svaret gäller (INV-SEC-014). */
export const IDENTITET_HUVUD = "X-Snajp-Identitet";

/**
 * Varje svar bär identiteten, även felsvaren: en utgången session svarar 401,
 * och det är just då en gammal flik ska märka bytet och ladda om
 * (components/dashboard/DashboardContext.tsx). Ett fel i uppslaget ger ett
 * tomt värde, som klienten läser som "okänt" och inte laddar om för.
 */
export async function proxyAsTenant(path: string, init: RequestInit) {
  const svar = await vidarebefordra(path, init);
  svar.headers.set(IDENTITET_HUVUD, await snajpIdentitet().catch(() => ""));
  return svar;
}

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
async function vidarebefordra(path: string, init: RequestInit) {
  try {
    const tenant = await requireSnajpTenant();

    let begaran: RequestInit = init;

    let backendPath = path;
    const metod = String(begaran.method ?? "GET").toUpperCase();
    const arSkrivning = metod !== "GET" && metod !== "HEAD";

    // Läsrollen (lib/auth/lasroll.ts): en viewer läser varje tenant-scopad
    // yta men skriver ingenting. Spärren sitter HÄR för att varje inloggad
    // backend-skrivning (kunskapsbas, inkorgsåtgärder, testchatt,
    // inställningar, leads) passerar den här punkten — en dold knapp i UI:t
    // är hövlighet, det här är skyddet.
    if (arSkrivning && tenant.roll === LASROLL) {
      return NextResponse.json({ error: LASROLL_FEL, kod: "lasroll" }, { status: 403 });
    }

    // CRM:et har inget testläge: en skrivning där hade ändrat kundens riktiga
    // register. Den som tittar som kund läser därför bara. Utan den här grinden
    // lade raderna nedan `is_test` i kroppen, och CRM-API:t (som vägrar okända
    // fält) svarade 422 utan att säga varför.
    if (tenant.impersonerar && arSkrivning && backendPath.startsWith("/api/crm/")) {
      return NextResponse.json(
        {
          detail: {
            code: "impersonation_read_only",
            message: "You are viewing as the customer. Nothing is written to the CRM in that mode.",
            meddelande: "Du tittar som kunden. I det läget skrivs ingenting till CRM:et."
          }
        },
        { status: 403 }
      );
    }

    if (tenant.impersonerar && arSkrivning) {
      // Admin som tittar som kund: allt som SKRIVS är test. Läsning måste
      // visa kundens riktiga inkorg — annars gömmer `?is_test=true` på GET
      // de skarpa ärendena och admin tror att profilen är tom.
      // Query-parametern täcker leads/prospects; JSON-kroppen chat, batch, mock.
      if (!backendPath.includes("is_test=")) {
        backendPath += (backendPath.includes("?") ? "&" : "?") + "is_test=true";
      }
      if (typeof begaran.body === "string" && begaran.body.length > 0) {
        try {
          const parsed: unknown = JSON.parse(begaran.body);
          if (parsed && typeof parsed === "object" && !Array.isArray(parsed)) {
            begaran = { ...begaran, body: JSON.stringify({ ...parsed, is_test: true }) };
          }
        } catch {
          // Inte JSON — lämna kroppen orörd.
        }
      }
    }

    return await proxyWithApiKey(backendPath, begaran, tenant.apiKey, tenant.userId, tenant.isDemo);
  } catch (error) {
    if (error instanceof SnajpTenantError) {
      // `kod` går med, så att gränssnittet kan skilja "inte aktiverad ännu"
      // från "något gick sönder" utan att tolka svensk text.
      return NextResponse.json(
        svarForTenantfel(error),
        { status: error.status }
      );
    }
    throw error;
  }
}
