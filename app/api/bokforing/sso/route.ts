import { NextResponse, type NextRequest } from "next/server";
import { skapaBokforingsBiljett } from "@/lib/bokforing/sso";
import { resolveDashboardState } from "@/lib/data/dashboard";
import { requireSnajpTenant, SnajpTenantError } from "@/lib/snajp/tenant";

/**
 * Knappen "Öppna bokföringssajten" pekar hit — biljetten skapas VID KLICKET.
 *
 * Den lever i 60 sekunder, så en biljett bakad in i sidan vid rendering hade
 * varit död för kunden som läser en stund innan den klickar. En GET som
 * skapar färskt och studsar vidare gör livstiden till en icke-fråga, och
 * håller tenantnyckeln borta från sidans HTML.
 *
 * Grinden är bokföringsproxyns (app/api/snajp-support/bookkeeping/): 404
 * utan inloggning eller utan produkten — ett 403 hade bekräftat att ytan
 * finns. Utan tenantnyckel eller SSO-hemlighet skickas kunden till sajten
 * UTAN biljett och möter dess inloggningssida: sämre, men aldrig fel data.
 */

export const runtime = "nodejs";

export async function GET(request: NextRequest) {
  const externUrl = (process.env.BOKFORING_EXTERN_URL ?? "").replace(/\/$/, "");
  const { products, signedIn, workspaceName } = await resolveDashboardState();
  if (!externUrl || !signedIn || !products.includes("bookkeeping")) {
    return NextResponse.json({ error: "Hittades inte." }, { status: 404 });
  }

  let mal = externUrl;
  const hemlighet = process.env.BOKFORING_SSO_SECRET;
  const backend = process.env.SNAJP_SUPPORT_URL;
  if (hemlighet && backend) {
    try {
      const tenant = await requireSnajpTenant();
      const biljett = skapaBokforingsBiljett(
        {
          k: tenant.apiKey,
          b: backend.replace(/\/$/, ""),
          s: tenant.slug,
          n: workspaceName || tenant.slug
        },
        hemlighet
      );
      mal = `${externUrl}/sso?b=${biljett}`;
    } catch (error) {
      if (!(error instanceof SnajpTenantError)) throw error;
      // Arbetsyta utan nyckel: rak länk, sajtens inloggning tar emot.
    }
  }

  // 303 och inte 307: målet ska alltid hämtas med GET, och webbläsaren ska
  // inte cacha ett hopp vars biljett är färskvara.
  return NextResponse.redirect(mal, 303);
}
