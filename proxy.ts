import { createServerClient, type CookieOptions } from "@supabase/ssr";
import { NextResponse, type NextRequest } from "next/server";
import { isAuthRoute, isProtectedRoute } from "@/lib/routes";
import { getServerSupabaseKey, getSupabaseUrl, hasServerSupabaseEnv } from "@/lib/supabase/env";

async function hasBusinessContext(
  supabase: ReturnType<typeof createServerClient>,
  userId: string
): Promise<boolean> {
  const { data: profile } = await supabase
    .from("profiles")
    .select("workspace_id")
    .eq("id", userId)
    .maybeSingle<{ workspace_id: string }>();

  if (!profile?.workspace_id) {
    return false;
  }

  const { data: businessContext } = await supabase
    .from("business_contexts")
    .select("id")
    .eq("workspace_id", profile.workspace_id)
    .maybeSingle<{ id: string }>();

  return Boolean(businessContext);
}

export async function proxy(request: NextRequest) {
  let supabaseResponse = NextResponse.next({ request });

  // Without Supabase configured there are no sessions to guard. Throwing here
  // took down every route including the public product pages, so stand aside
  // instead: protected routes stay unreachable in practice because they have no
  // data to show.
  if (!hasServerSupabaseEnv()) {
    return supabaseResponse;
  }

  const supabase = createServerClient(getSupabaseUrl(), getServerSupabaseKey(), {
    cookies: {
      getAll() {
        return request.cookies.getAll();
      },
      setAll(cookiesToSet: { name: string; value: string; options: CookieOptions }[]) {
        cookiesToSet.forEach(({ name, value }) => {
          request.cookies.set(name, value);
        });
        supabaseResponse = NextResponse.next({ request });
        cookiesToSet.forEach(({ name, value, options }) => {
          supabaseResponse.cookies.set(name, value, options);
        });
      }
    }
  });


  /**
   * Varje omdirigering MÅSTE bära med sig sessionscookies.
   *
   * `supabase.auth.getUser()` roterar refresh-token och skriver de nya
   * värdena till `supabaseResponse` via setAll(). Ett `NextResponse.redirect()`
   * är ett HELT NYTT svar — utan den här kopieringen kastas de nya cookies
   * bort, och webbläsaren sitter kvar med en förbrukad token.
   *
   * Följden, uppmätt i produktionens Vercel-logg 2026-08-17 13:13:
   *
   *     /login → /dashboard → /onboarding → /login → /dashboard → ...
   *
   * /login såg en användare och skickade vidare; /onboarding såg ingen och
   * skickade tillbaka. Samma session, olika svar, beroende på om just den
   * requesten råkade komma före eller efter rotationen. Symptomen var
   * "Internal Server Error", "Sidan finns inte" och en inloggning som verkade
   * lyckas utan att leda någonstans — tre olika felbilder ur samma orsak.
   *
   * Detta är den dokumenterade fällan i Supabases SSR-mellanvara. Lägger någon
   * till en ny redirect här utan att gå via den här funktionen är loopen
   * tillbaka, och den syns inte i något test.
   */
  function redirectMedSession(url: URL): NextResponse {
    const svar = NextResponse.redirect(url);
    supabaseResponse.cookies.getAll().forEach((cookie) => {
      svar.cookies.set(cookie);
    });
    return svar;
  }

  const {
    data: { user }
  } = await supabase.auth.getUser();

  const { pathname } = request.nextUrl;

  if (isProtectedRoute(pathname) && !user) {
    const loginUrl = request.nextUrl.clone();
    loginUrl.pathname = "/login";
    loginUrl.searchParams.set("next", pathname);
    return redirectMedSession(loginUrl);
  }

  if (user && pathname === "/login") {
    const dashboardUrl = request.nextUrl.clone();
    dashboardUrl.pathname = "/dashboard";
    dashboardUrl.search = "";
    return redirectMedSession(dashboardUrl);
  }

  if (user && isProtectedRoute(pathname) && pathname !== "/onboarding") {
    const onboarded = await hasBusinessContext(supabase, user.id);

    if (!onboarded) {
      const onboardingUrl = request.nextUrl.clone();
      onboardingUrl.pathname = "/onboarding";
      onboardingUrl.search = "";
      return redirectMedSession(onboardingUrl);
    }
  }

  if (user && pathname === "/onboarding") {
    const onboarded = await hasBusinessContext(supabase, user.id);

    if (onboarded) {
      const dashboardUrl = request.nextUrl.clone();
      dashboardUrl.pathname = "/dashboard";
      dashboardUrl.search = "";
      return redirectMedSession(dashboardUrl);
    }
  }

  if (user && isAuthRoute(pathname) && pathname !== "/login") {
    return supabaseResponse;
  }

  return supabaseResponse;
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
