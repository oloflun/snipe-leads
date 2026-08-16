import NextAuth, { type DefaultSession } from "next-auth";
import Credentials from "next-auth/providers/credentials";
import Google from "next-auth/providers/google";
import MicrosoftEntraID from "next-auth/providers/microsoft-entra-id";

import { hasDatabase, sql } from "@/lib/db";
import { verifyPassword } from "@/lib/password";

/**
 * Auth.js (NextAuth v5) ersätter Supabase Auth.
 *
 * Identiteten bor kvar i `auth.users` — samma tabell, samma uuid:n, samma
 * främmande nycklar från profiles, audit_logs, workspace_invites och
 * platform_admins. Bara SKRIVAREN byts: Auth.js i stället för GoTrue. Triggern
 * `on_auth_user_created` (001/006) fortsätter skapa workspace och profil, så
 * inbjudningsmodellen håller oförändrad.
 *
 * Sessionen är en JWT, inte en databasrad. Skälet är proxyn: den kördes förut
 * på varje skyddad request och gjorde TVÅ databasfrågor för att avgöra om
 * användaren var onboardad. Med workspace-id och onboardingstatus i token
 * blir det noll — och middleware kan köra på Edge, där `pg` inte finns.
 */

declare module "next-auth" {
  interface Session {
    user: { id: string; workspaceId: string | null; onboarded: boolean } & DefaultSession["user"];
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
 * Workspace + onboardingstatus i en enda fråga.
 *
 * getWorkspaceContext() gjorde fyra PostgREST-anrop och skapade fyra klienter
 * per anrop. Det här är samma svar för ett tur och retur.
 */
export async function workspaceClaims(
  userId: string
): Promise<{ workspaceId: string | null; onboarded: boolean }> {
  const rows = await sql<{ workspace_id: string | null; onboarded: boolean }>(
    `select p.workspace_id,
            (bc.id is not null) as onboarded
       from public.profiles p
       left join public.business_contexts bc on bc.workspace_id = p.workspace_id
      where p.id = $1
      limit 1`,
    [userId]
  );
  return {
    workspaceId: rows[0]?.workspace_id ?? null,
    onboarded: Boolean(rows[0]?.onboarded)
  };
}

/** Läker konton som saknar profilrad — samma funktion som triggern använder. */
export async function ensureWorkspace(userId: string): Promise<void> {
  try {
    await sql("select public.ensure_workspace_for_user($1)", [userId]);
  } catch (error) {
    // Inloggningen ska inte falla på detta — proxyn skickar användaren till
    // /onboarding, som försöker igen och visar felet där om det kvarstår.
    console.error("ensure_workspace_for_user:", (error as Error).message);
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
    async jwt({ token, user, trigger }) {
      if (user?.id) {
        token.sub = user.id;
        await ensureWorkspace(user.id);
      }
      // Onboardingen sätter business_context EFTER inloggningen, så anspråken
      // måste kunna räknas om utan att användaren loggar ut och in.
      if (token.sub && (user || trigger === "update" || token.workspaceId === undefined)) {
        const claims = await workspaceClaims(token.sub);
        token.workspaceId = claims.workspaceId;
        token.onboarded = claims.onboarded;
      }
      return token;
    },
    async session({ session, token }) {
      session.user.id = token.sub ?? "";
      session.user.workspaceId = (token.workspaceId as string | null) ?? null;
      session.user.onboarded = Boolean(token.onboarded);
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
