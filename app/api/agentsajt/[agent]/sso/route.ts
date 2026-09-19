import { NextResponse, type NextRequest } from "next/server";
import { AGENTSAJTER, arAgentSajt, externUrlFor } from "@/lib/agentsajt";
import { skapaBokforingsBiljett } from "@/lib/bokforing/sso";
import { resolveDashboardState } from "@/lib/data/dashboard";
import { requireSnajpTenant, SnajpTenantError } from "@/lib/snajp/tenant";

/**
 * "Kör Agent"-knapparna pekar hit — EN route för alla agentsajter, styrd av
 * registret i lib/agentsajt.ts. Biljetten skapas VID KLICKET: den lever i
 * 60 sekunder, så en biljett bakad in i sidan hade varit död för kunden som
 * läser en stund innan den klickar. Formatet är detsamma för alla sajter
 * (lib/bokforing/sso.ts — namnet är historiskt, bokföringen var först).
 *
 * Grinden är bokföringsproxyns: 404 utan inloggning eller utan agentens
 * produkt — ett 403 hade bekräftat att ytan finns. Utan tenantnyckel eller
 * SSO-hemlighet skickas kunden till sajten UTAN biljett och möter dess
 * inloggningssida: sämre, men aldrig fel data.
 */

export const runtime = "nodejs";

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ agent: string }> }
) {
  const { agent } = await params;
  const { products, signedIn, workspaceName } = await resolveDashboardState();
  if (!arAgentSajt(agent)) {
    return NextResponse.json({ error: "Hittades inte." }, { status: 404 });
  }
  const externUrl = externUrlFor(agent);
  if (!externUrl || !signedIn || !products.includes(AGENTSAJTER[agent].produkt)) {
    return NextResponse.json({ error: "Hittades inte." }, { status: 404 });
  }

  let mal = externUrl;
  const hemlighet = process.env.AGENTSAJT_SSO_SECRET ?? process.env.BOKFORING_SSO_SECRET;
  const backend = process.env.SNAJP_SUPPORT_URL;
  if (hemlighet && backend) {
    try {
      const tenant = await requireSnajpTenant();
      // Läsrollen stannar i huvudappen: support-webb-portalen har ingen
      // rollmodell (en biljett ger full redigeringsrätt där), så en viewer
      // som fick biljetten hade kunnat skriva bakvägen. Journalen och
      // inkorgen finns i huvudappens läsytor.
      if (tenant.roll === "viewer") {
        return NextResponse.json({ error: "Hittades inte." }, { status: 404 });
      }
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
