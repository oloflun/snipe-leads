/**
 * En SATT men trasig URL är inte samma sak som en giltig URL.
 *
 * Den här skillnaden tog ner hela den inloggade ytan i produktion 2026-08-17:
 * `NEXT_PUBLIC_SUPABASE_URL` fanns, men var inget `createServerClient()` kunde
 * tolka. Vakten nedan mätte bara sanningsenlighet, släppte igenom värdet, och
 * konstruktorn kastade `Invalid supabaseUrl` en rad senare — i proxyn, alltså
 * FÖRE varje route den täcker. `/login`, `/dashboard`, `/settings`,
 * `/onboarding`, `/admin` och `/auth/callback` svarade 500 med tom body, medan
 * marknadssidorna utanför matchern såg friska ut. Felbilden pekade därför på
 * routingen i stället för på en miljövariabel.
 *
 * Kontrollera formen, inte bara närvaron. En trimning ingår: en efterföljande
 * radbrytning från en inklistrad variabel är osynlig i varje dashboard.
 */
function readHttpUrl(raw: string | undefined): string | null {
  const trimmed = raw?.trim();
  if (!trimmed) {
    return null;
  }
  try {
    const parsed = new URL(trimmed);
    return parsed.protocol === "http:" || parsed.protocol === "https:" ? trimmed : null;
  } catch {
    return null;
  }
}

/**
 * True when a server Supabase client can actually be built. Callers that must
 * degrade rather than fail (public marketing pages, anonymous visitors) check
 * this instead of catching the throws below.
 */
export function hasServerSupabaseEnv(): boolean {
  return Boolean(
    readHttpUrl(process.env.NEXT_PUBLIC_SUPABASE_URL) &&
      (process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || process.env.SUPABASE_SERVICE_ROLE_KEY)
  );
}

export function getSupabaseUrl(): string {
  const url = readHttpUrl(process.env.NEXT_PUBLIC_SUPABASE_URL);
  if (!url) {
    throw new Error(
      process.env.NEXT_PUBLIC_SUPABASE_URL
        ? "NEXT_PUBLIC_SUPABASE_URL är satt men är ingen giltig http(s)-URL"
        : "Missing NEXT_PUBLIC_SUPABASE_URL"
    );
  }
  return url;
}

/** Server-side session client: prefer publishable/anon key (RLS-aware); service role is admin-only. */
export function getServerSupabaseKey(): string {
  const key = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY ?? process.env.SUPABASE_SERVICE_ROLE_KEY;
  if (!key) {
    throw new Error("Missing NEXT_PUBLIC_SUPABASE_ANON_KEY or SUPABASE_SERVICE_ROLE_KEY");
  }
  return key;
}

/** Browser/client key — must be publishable or legacy anon JWT. */
export function getBrowserSupabaseKey(): string {
  const key = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;
  if (!key) {
    throw new Error("Missing NEXT_PUBLIC_SUPABASE_ANON_KEY");
  }
  return key;
}