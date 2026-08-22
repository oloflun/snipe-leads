import NextAuth, { type DefaultSession } from "next-auth";
import Credentials from "next-auth/providers/credentials";
import Google from "next-auth/providers/google";
import MicrosoftEntraID from "next-auth/providers/microsoft-entra-id";

import { hasDatabase, sql, sqlAsUser } from "@/lib/db";
import { verifyPassword } from "@/lib/password";
import { hasSupabaseAuthEnv, supabaseAuth } from "@/lib/supabase-auth";

/**
 * Auth.js (NextAuth v5) ersätter Supabase Auth.
 *
 * Identiteten bor kvar i `auth.users` — samma tabell, samma uuid:n, samma
 * främmande nycklar från profiles, audit_logs, workspace_invites och
 * platform_admins. Bara SKRIVAREN byts: Auth.js i stället för GoTrue. Triggern
 * `on_auth_user_created` (001/006) fortsätter skapa workspace och profil, så
 * inbjudningsmodellen håller oförändrad.
 *
 * Sessionen är en JWT, inte en databasrad. Det gör att proxyn kan köra på Edge,
 * där `pg` inte finns, och att den inte behöver en databasfråga för att avgöra
 * om någon är inloggad — den gjorde förut TVÅ per skyddad request.
 *
 * Token bär BARA IDENTITET. Onboardingstatus och workspace-tillhörighet låg
 * här först, som anspråk, och gav en loop i drift: onboardingen skrev raden,
 * skickade till /dashboard, och proxyn skickade tillbaka — cookien sa
 * fortfarande false, och `unstable_update` skrev inte om den.
 *
 * En token är en ögonblicksbild, signerad och cachad hos klienten. Identitet
 * hör hemma där för att den inte ändras under sessionen. Föränderligt tillstånd
 * gör det inte: det blir inaktuellt utan att något felar, och felet visar sig
 * som en dirigering som inte går att förklara från koden man läser. Sådant
 * läses färskt — se lib/auth/onboarding-gate.ts.
 */

declare module "next-auth" {
  interface Session {
    user: { id: string } & DefaultSession["user"];
  }
}

type UserRow = {
  id: string;
  email: string;
  encrypted_password: string | null;
  raw_user_meta_data: Record<string, unknown> | null;
};

async function findUserByEmail(email: string): Promise<UserRow | null> {
  const rows = await sql<UserRow>(
    "select id, email, encrypted_password, raw_user_meta_data from auth.users where lower(email) = lower($1)",
    [email]
  );
  return rows[0] ?? null;
}

/** Skapar användaren om den saknas. Används av OAuth, där lösenord inte finns. */
async function upsertOAuthUser(email: string, fullName: string | null): Promise<UserRow> {
  const existing = await findUserByEmail(email);
  if (existing) {
    return existing;
  }
  const rows = await sql<UserRow>(
    `insert into auth.users (email, raw_user_meta_data, email_confirmed_at)
     values ($1, jsonb_build_object('full_name', $2::text), now())
     returning id, email, encrypted_password, raw_user_meta_data`,
    [email, fullName]
  );
  return rows[0];
}

/**
 * Läker konton som saknar profilrad — samma funktion som triggern använder.
 *
 * Anropet går via `ensure_workspace_for_current_user()` och `sqlAsUser`, inte
 * via `ensure_workspace_for_user($1)` och `sql`. Det är inte en stilfråga:
 *
 *   * `ensure_workspace_for_user(uuid, text)` är REVOKED från public, anon och
 *     authenticated i 006_auth_selfheal, med flit — en funktion som tar ett
 *     användar-id som argument låter anroparen läka (och därmed skapa workspace
 *     åt) vem som helst. `snajp_web` har den inte heller. Anropet föll alltså
 *     på `permission denied for function ensure_workspace_for_user` vid VARJE
 *     inloggning på Railway-stacken, tyst: felet fångas nedan.
 *   * `sql()` sätter ingen identitet, så `auth.uid()` hade varit null även om
 *     graden funnits. `sqlAsUser` sätter `app.user_id` i transaktionen, vilket
 *     är exakt vad `ensure_workspace_for_current_user()` läser.
 *
 * Följden av buggen var att självläkningen aldrig körde: ett konto utan
 * profilrad loopade mellan /dashboard och /onboarding, precis det som
 * funktionen finns för att förhindra.
 */
export async function ensureWorkspace(userId: string): Promise<void> {
  try {
    await sqlAsUser(userId, "select public.ensure_workspace_for_current_user()");
  } catch (error) {
    // Inloggningen ska inte falla på detta — proxyn skickar användaren till
    // /onboarding, som försöker igen och visar felet där om det kvarstår.
    console.error("ensure_workspace_for_current_user:", (error as Error).message);
  }
}

const providers = [
  Credentials({
    credentials: { email: {}, password: {} },
    async authorize(credentials) {
      const email = String(credentials?.email ?? "");
      const password = String(credentials?.password ?? "");
      if (!email || !password) {
        return null;
      }

      // Supabase-stacken: låt GoTrue verifiera lösenordet (bcrypt). auth.users
      // rörs aldrig direkt här — det är hela poängen med adaptern.
      if (hasSupabaseAuthEnv()) {
        const { data, error } = await supabaseAuth().auth.signInWithPassword({
          email,
          password
        });
        if (error || !data.user) {
          return null;
        }
        return {
          id: data.user.id,
          email: data.user.email ?? email,
          name: (data.user.user_metadata?.full_name as string | undefined) ?? null
        };
      }

      // Railway: direkt SQL mot replikerad auth.users (scrypt).
      const user = await findUserByEmail(email);
      // Verifiera ALLTID, även när kontot saknas: ett tidigt `return null`
      // gör svarstiden till ett orakel för vilka adresser som finns.
      const ok = await verifyPassword(password, user?.encrypted_password ?? null);
      if (!ok || !user) {
        return null;
      }
      return {
        id: user.id,
        email: user.email,
        name: (user.raw_user_meta_data?.full_name as string | undefined) ?? null
      };
    }
  }),
  ...(process.env.AUTH_GOOGLE_ID ? [Google] : []),
  ...(process.env.AUTH_MICROSOFT_ENTRA_ID_ID ? [MicrosoftEntraID] : [])
];

export const { handlers, auth, signIn, signOut } = NextAuth({
  providers,
  session: { strategy: "jwt" },
  pages: { signIn: "/login", error: "/login" },
  trustHost: true,
  callbacks: {
    async signIn({ user, account }) {
      if (account?.provider === "credentials" || !user.email) {
        return true;
      }
      const row = await upsertOAuthUser(user.email, user.name ?? null);
      user.id = row.id;
      return true;
    },
    async jwt({ token, user }) {
      // Bara identitet. Allt annat läses färskt där det används.
      if (user?.id) {
        token.sub = user.id;
        await ensureWorkspace(user.id);
      }
      return token;
    },
    async session({ session, token }) {
      session.user.id = token.sub ?? "";
      return session;
    }
  }
});

export type SessionUser = { id: string; email: string | null; name: string | null };

/** Samma API som den gamla lib/auth.ts, så anropsställena inte behöver ändras. */
export async function getUser(): Promise<SessionUser | null> {
  if (!hasDatabase()) {
    return null;
  }
  const session = await auth();
  if (!session?.user?.id) {
    return null;
  }
  return {
    id: session.user.id,
    email: session.user.email ?? null,
    name: session.user.name ?? null
  };
}

export async function requireUser(): Promise<SessionUser> {
  const user = await getUser();
  if (!user) {
    throw new Error("Unauthorized");
  }
  return user;
}
