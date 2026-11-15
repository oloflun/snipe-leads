import { NextResponse, type NextRequest } from "next/server";
import { sql } from "@/lib/db";
import { appBasUrl } from "@/lib/mail";

/**
 * Den spårade demolänken i utskicken: `/prova/<token>` (Antons beställning
 * 2026-11-15, se docs/BESLUT.md).
 *
 * ## Två nivåer: klick och besök
 *
 * GET loggar ett KLICK och skickar vidare till demon. Ett klick bevisar inte
 * att en människa varit där: e-postskydd (Safe Links, Mimecast, Gmails proxy)
 * följer länkar i inkommande mejl innan mottagaren ser dem. Därför får
 * demosidan en `besok=<token>` i adressen, och klientkomponenten
 * components/demo/DemoBesok.tsx skickar ett POST hit vid första riktiga
 * interaktionen (skroll, klick, tangent). Det är ett BESÖK, och det är det
 * listan "Vilka har besökt demon" räknar som besökt.
 *
 * ## Varför mottagaren aldrig får ett fel
 *
 * Länken står i ett säljmejl. Ett 500 eller en okänd token ska ändå landa på
 * demon, så varje fel blir en redirect till `/demo`. Token är ogenomskinlig,
 * precis som avregistreringslänken (app/avregistrera/[token]), och inlösen
 * sker i security definer-funktioner (migration 116) så att den oinloggade
 * besökaren aldrig får läsa tabellerna.
 */

const TOKEN = /^[A-Za-z0-9_-]{6,64}$/;

const HUVUDEN = {
  "Cache-Control": "no-store",
  "X-Robots-Tag": "noindex, nofollow"
} as const;

function varden(host: string | null | undefined): string {
  return (host ?? "").trim().toLowerCase().replace(/^www\./, "");
}

/**
 * Sajtens publika origin, ur appBasUrl (SITE_URL eller Railways domän) och
 * aldrig ur requesten: bakom Railways proxy är request.nextUrl.origin
 * containerns interna adress, och en redirect dit hade landat mottagaren på
 * en död länk.
 */
function publikOrigin(request: NextRequest): string {
  try {
    return new URL(appBasUrl()).origin;
  } catch {
    return request.nextUrl.origin;
  }
}

/** Sajtens egna värdnamn: den publika basens och proxyns. */
function egnaVardar(request: NextRequest): Set<string> {
  const vardar = new Set<string>();
  vardar.add(varden(new URL(publikOrigin(request)).host));
  vardar.add(varden(request.headers.get("x-forwarded-host")?.split(",")[0]));
  vardar.delete("");
  return vardar;
}

function demoAdress(request: NextRequest): URL {
  return new URL("/demo", publikOrigin(request));
}

/** Målet som absolut URL, med `besok` bara när målet är vår egen sajt. */
function malAdress(request: NextRequest, mal: string, token: string): URL {
  const url = new URL(mal, publikOrigin(request));
  if (url.protocol !== "https:" && url.protocol !== "http:") {
    return demoAdress(request);
  }
  // Token går aldrig till en främmande domän: där säger den ingenting, och
  // den knyter mottagaren till ett utskick.
  if (egnaVardar(request).has(varden(url.host))) {
    url.searchParams.set("besok", token);
  }
  return url;
}

function vidare(url: URL): NextResponse {
  return NextResponse.redirect(url, { status: 302, headers: HUVUDEN });
}

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ token: string }> }
): Promise<NextResponse> {
  const { token } = await params;
  if (!TOKEN.test(token)) return vidare(demoAdress(request));
  try {
    const ua = (request.headers.get("user-agent") ?? "").slice(0, 300);
    const rader = await sql<{ mal: string | null }>("select public.demolank_klick($1, $2) as mal", [token, ua]);
    const mal = rader[0]?.mal;
    return vidare(mal ? malAdress(request, mal, token) : demoAdress(request));
  } catch {
    return vidare(demoAdress(request));
  }
}

/** Länkskannrar frågar ofta med HEAD först: vidare utan att logga något. */
export async function HEAD(request: NextRequest): Promise<NextResponse> {
  return vidare(demoAdress(request));
}

/** Besöket, från DemoBesok.tsx. Alltid 204: beaconen läser aldrig svaret. */
export async function POST(
  _request: NextRequest,
  { params }: { params: Promise<{ token: string }> }
): Promise<NextResponse> {
  const { token } = await params;
  if (TOKEN.test(token)) {
    try {
      await sql("select public.demolank_besok($1)", [token]);
    } catch {
      // Ett tappat besök är bättre än ett fel i besökarens konsol.
    }
  }
  return new NextResponse(null, { status: 204, headers: HUVUDEN });
}
