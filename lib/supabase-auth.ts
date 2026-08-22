import { createClient, type SupabaseClient } from "@supabase/supabase-js";

/**
 * Supabase-auth som ADAPTER för Auth.js Credentials, på Supabase-stacken.
 *
 * Skillnaden mot direkt SQL: här är det GoTrue som verifierar lösenordet i sitt
 * eget bcrypt-format. auth.users rörs aldrig direkt. Railway-stacken har ingen
 * GoTrue — där är auth.users replikerad och läses via SQL i lib/auth.ts
 * fallback, så den här klienten används bara när NEXT_PUBLIC_SUPABASE_URL är
 * satt (d.v.s. Supabase-stacken).
 */

/**
 * En SATT men trasig URL är inte samma sak som en giltig URL.
 *
 * Den här skillnaden har nu kostat två haverier. Först produktionen
 * 2026-08-17: NEXT_PUBLIC_SUPABASE_URL fanns men var inget
 * createClient() kunde tolka, vakten mätte bara sanningsenlighet, och
 * konstruktorn kastade en rad senare — i proxyn, alltså före varje route.
 * Fixen låg i lib/supabase/env.ts.
 *
 * Sedan igen 2026-08-18, i Preview: Auth.js-migreringen RADERADE den filen,
 * och härdningen försvann med den. Symptomet den här gången var
 * CallbackRouteError — Auth.js egen inpackning av samma kastade undantag:
 *
 *     [auth][cause]: Error: Invalid supabaseUrl: Must be a valid HTTP or HTTPS URL
 *
 * Ett kastat fel i authorize() blir CallbackRouteError, som ser ut som ett
 * konfigurationsfel i Auth.js och skickar felsökningen åt fel håll. Ett fel
 * LÖSENORD returnerar null och ger CredentialsSignin. De två felen betyder
 * helt olika saker, och det är värt att veta vilket man har.
 *
 * Kontrollera formen, inte bara närvaron. Trimningen ingår: en efterföljande
 * radbrytning från en inklistrad variabel är osynlig i varje dashboard.
 */
function giltigHttpUrl(rå: string | undefined): string | null {
  const trimmad = rå?.trim();
  if (!trimmad) return null;
  try {
    const url = new URL(trimmad);
    return url.protocol === "http:" || url.protocol === "https:" ? trimmad : null;
  } catch {
    return null;
  }
}

export function hasSupabaseAuthEnv(): boolean {
  return Boolean(
    giltigHttpUrl(process.env.NEXT_PUBLIC_SUPABASE_URL) &&
      process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY
  );
}

let _client: SupabaseClient | null = null;

export function supabaseAuth(): SupabaseClient {
  if (!_client) {
    const url = giltigHttpUrl(process.env.NEXT_PUBLIC_SUPABASE_URL);
    if (!url) {
      // Tydligt fel i stället för konstruktorns generiska. Anroparen i
      // lib/auth.ts kontrollerar hasSupabaseAuthEnv() först, så hit ska man
      // aldrig komma — men "ska aldrig" är hur det här felet uppstod två gånger.
      throw new Error(
        "NEXT_PUBLIC_SUPABASE_URL är satt men är ingen giltig http(s)-URL"
      );
    }
    _client = createClient(
      url,
      process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
      { auth: { persistSession: false, autoRefreshToken: false } }
    );
  }
  return _client;
}
