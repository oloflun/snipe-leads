import { getToken } from "next-auth/jwt";
import { NextResponse, type NextRequest } from "next/server";
import { isAuthRoute, isProtectedRoute } from "@/lib/routes";

/**
 * Proxyn läser Auth.js sessions-JWT i stället för Supabases cookie.
 *
 * Den gjorde förut TVÅ databasfrågor per skyddad request för att avgöra om
 * användaren var onboardad. Den frågan ställs numera i layouten i stället, där
 * svaret är färskt, och proxyn gör noll frågor. Det är också vad som gör att
 * den kan köra på Edge, där `pg` inte finns.
 */
export async function proxy(request: NextRequest) {
  const { pathname } = request.nextUrl;

  // Utan AUTH_SECRET finns ingen session att validera — men det betyder INTE
  // att skyddade routes ska stå öppna. Tvärtom: utan secret är ALLA oinloggade,
  // så skyddade routes redirectas till /login i stället för att släppas igenom.
  // Publika produktsidor fortsätter rendera. Att kasta här tog förut ner varenda
  // route inklusive marknadsföringssidorna; en redirect bara för skyddade routes
  // har inte det problemet. Det här är fail-CLOSED, inte fail-open.
  if (!process.env.AUTH_SECRET) {
    if (isProtectedRoute(pathname)) {
      const loginUrl = request.nextUrl.clone();
      loginUrl.pathname = "/login";
      loginUrl.searchParams.set("next", pathname);
      return NextResponse.redirect(loginUrl);
    }
    return NextResponse.next({ request });
  }

  const token = await getToken({
    req: request,
    secret: process.env.AUTH_SECRET,
    secureCookie: request.nextUrl.protocol === "https:"
  });

  if (isProtectedRoute(pathname) && !token) {
    const loginUrl = request.nextUrl.clone();
    loginUrl.pathname = "/login";
    loginUrl.searchParams.set("next", pathname);
    return NextResponse.redirect(loginUrl);
  }

  if (token && pathname === "/login") {
    const dashboardUrl = request.nextUrl.clone();
    dashboardUrl.pathname = "/dashboard";
    dashboardUrl.search = "";
    return NextResponse.redirect(dashboardUrl);
  }

  // Onboardingdirigeringen bor INTE här. Den låg här och läste ett anspråk ur
  // sessions-token, vilket gav en loop i drift: raden skrevs, cookien sa
  // fortfarande false. Proxyn avgör numera bara EN sak — finns det en session —
  // och det är den enda frågan vars svar inte kan hinna bli inaktuellt.
  // Se lib/auth/onboarding-gate.ts.

  if (token && isAuthRoute(pathname) && pathname !== "/login") {
    return NextResponse.next({ request });
  }

  return NextResponse.next({ request });
}

// Namnet är inte valfritt: Next läser matchern från en export som heter `config`
// (parseMiddlewareConfig i next/dist/build/analysis/get-page-static-info.js).
// Som `proxyConfig` ignorerades den, och proxyn körde auth-anrop på varenda
// request — inklusive anonym trafik på marknadsföringssidorna.
export const config = {
  // Only the authenticated surface. The old matcher still listed /leads, /companies,
  // /emails and friends, which are now either public product pages or 308s into
  // /dashboard, so the proxy was running on anonymous marketing traffic.
  matcher: [
    "/dashboard/:path*",
    "/settings/:path*",
    "/onboarding/:path*",
    // /admin är tredje lagret, inte det bärande. Grinden som räknas är
    // getPlatformAdmin() i app/admin/layout.tsx, som svarar 404 — och
    // /api/admin, som proxyn medvetet INTE täcker (en redirect till /login
    // är fel svarsform för ett API-anrop och skulle dölja 404:an).
    "/admin/:path*",
    "/login"
  ]
};
