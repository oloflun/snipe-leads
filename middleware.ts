import { createServerClient, type CookieOptions } from "@supabase/ssr";
import { NextResponse, type NextRequest } from "next/server";
import { isAuthRoute, isProtectedRoute } from "@/lib/routes";
import { getServerSupabaseKey, getSupabaseUrl } from "@/lib/supabase/env";

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

// Demo-deployen (snajp.vercel.app) saknar Supabase-variabler helt. Utan den här
// grinden kastar getSupabaseUrl() och /snajp-support ger 500 i stället för demon.
// Saknas auth-lagret finns ingen inloggning att tala om: alla besökare är
// utloggade, och den enda vettiga åtgärden är att visa den publika demon.
function authIsConfigured(): boolean {
  return Boolean(
    process.env.NEXT_PUBLIC_SUPABASE_URL &&
      (process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || process.env.SUPABASE_SERVICE_ROLE_KEY)
  );
}

function demoRedirect(request: NextRequest) {
  const demoUrl = request.nextUrl.clone();
  demoUrl.pathname = "/demo/snajp";
  demoUrl.search = "";
  return NextResponse.redirect(demoUrl);
}

function isSnajpWorkspace(pathname: string): boolean {
  return pathname === "/snajp-support" || pathname.startsWith("/snajp-support/");
}

export async function middleware(request: NextRequest) {
  if (!authIsConfigured()) {
    return isSnajpWorkspace(request.nextUrl.pathname)
      ? demoRedirect(request)
      : NextResponse.next({ request });
  }

  let supabaseResponse = NextResponse.next({ request });

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

  const {
    data: { user }
  } = await supabase.auth.getUser();

  const { pathname } = request.nextUrl;

  if (isProtectedRoute(pathname) && !user) {
    // Snajp-Support är också en publik säljdemo. En utloggad besökare — ofta
    // via en marknadsföringslänk — ska landa i demon, inte i en inloggningsruta.
    if (isSnajpWorkspace(pathname)) {
      return demoRedirect(request);
    }

    const loginUrl = request.nextUrl.clone();
    loginUrl.pathname = "/login";
    loginUrl.searchParams.set("next", pathname);
    return NextResponse.redirect(loginUrl);
  }

  if (user && pathname === "/login") {
    const dashboardUrl = request.nextUrl.clone();
    dashboardUrl.pathname = "/dashboard";
    dashboardUrl.search = "";
    return NextResponse.redirect(dashboardUrl);
  }

  if (user && isProtectedRoute(pathname) && pathname !== "/onboarding") {
    const onboarded = await hasBusinessContext(supabase, user.id);

    if (!onboarded) {
      const onboardingUrl = request.nextUrl.clone();
      onboardingUrl.pathname = "/onboarding";
      onboardingUrl.search = "";
      return NextResponse.redirect(onboardingUrl);
    }
  }

  if (user && pathname === "/onboarding") {
    const onboarded = await hasBusinessContext(supabase, user.id);

    if (onboarded) {
      const dashboardUrl = request.nextUrl.clone();
      dashboardUrl.pathname = "/dashboard";
      dashboardUrl.search = "";
      return NextResponse.redirect(dashboardUrl);
    }
  }

  if (user && isAuthRoute(pathname) && pathname !== "/login") {
    return supabaseResponse;
  }

  return supabaseResponse;
}

export const config = {
  matcher: [
    "/dashboard/:path*",
    "/assistant/:path*",
    "/leads/:path*",
    "/companies/:path*",
    "/contacts/:path*",
    "/campaigns/:path*",
    "/emails/:path*",
    "/analytics/:path*",
    "/inbox/:path*",
    "/settings/:path*",
    "/onboarding/:path*",
    "/kundtjanst/:path*",
    "/snajp-support/:path*",
    "/login",
    "/auth/callback"
  ]
};