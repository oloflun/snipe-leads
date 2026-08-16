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
  // Utan AUTH_SECRET finns inga sessioner att vakta. Att kasta här tog ner
  // varenda route inklusive de publika produktsidorna, så stå åt sidan i
  // stället: skyddade rutter är ändå onåbara i praktiken, de har ingen data
  // att visa.
  if (!process.env.AUTH_SECRET) {
    return NextResponse.next({ request });
  }

  const token = await getToken({
    req: request,
    secret: process.env.AUTH_SECRET,
    secureCookie: request.nextUrl.protocol === "https:"
  });
  const { pathname } = request.nextUrl;

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
    // requirePlatformAdmin() i app/admin/layout.tsx, som svarar 404 — och
    // /api/admin, som proxyn medvetet INTE täcker (en redirect till /login
    // är fel svarsform för ett API-anrop och skulle dölja 404:an).
    "/admin/:path*",
    "/login",
    "/auth/callback"
  ]
};
