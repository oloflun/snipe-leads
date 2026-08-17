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

export function hasSupabaseAuthEnv(): boolean {
  return Boolean(
    process.env.NEXT_PUBLIC_SUPABASE_URL && process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY
  );
}

let _client: SupabaseClient | null = null;

export function supabaseAuth(): SupabaseClient {
  if (!_client) {
    _client = createClient(
      process.env.NEXT_PUBLIC_SUPABASE_URL!,
      process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
      { auth: { persistSession: false, autoRefreshToken: false } }
    );
  }
  return _client;
}
