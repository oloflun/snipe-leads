import NextAuth, { CredentialsSignin, type DefaultSession } from "next-auth";
import Credentials from "next-auth/providers/credentials";
import Google from "next-auth/providers/google";
import MicrosoftEntraID from "next-auth/providers/microsoft-entra-id";

import { arSparrad, nollstallEpost, registreraForsok } from "@/lib/auth/inloggningsforsok";
import { SPARRKOD, TVAFAKTOR_FEL, TVAFAKTOR_KRAVS } from "@/lib/auth/sparrkod";
import { loggaIn } from "@/lib/auth/inloggningssteg";
import { lasTvafaktor, provaOchForbruka } from "@/lib/auth/tvafaktor";
import { hasDatabase, sql, sqlAsUser } from "@/lib/db";
import { verifyPassword } from "@/lib/password";

/**
 * Inloggningen är tillfälligt spärrad (för många försök). Koden hamnar i
 * `?code=` när någon postar direkt till Auth.js, och läses av
 * `signInWithPassword`; den säger bara "vänta", aldrig om kontot finns.
 */
export class ForMangaForsok extends CredentialsSignin {
  code = SPARRKOD;
}

/** Lösenordet stämde och kontot har tvåstegsverifiering: koden behövs. */
export class TvafaktorKravs extends CredentialsSignin {
  code = TVAFAKTOR_KRAVS;
}

/** Koden i andra steget var fel eller redan använd. */
export class TvafaktorFel extends CredentialsSignin {
  code = TVAFAKTOR_FEL;
}

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
    /** `tvafaktor`: inloggningen gick igenom andra steget (se jwt nedan). */
    user: { id: string; tvafaktor?: boolean } & DefaultSession["user"];
  }
  interface User {
    tvafaktor?: boolean;
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
    credentials: { email: {}, password: {}, totp: {} },
    async authorize(credentials, request) {
      const email = String(credentials?.email ?? "");
      const password = String(credentials?.password ?? "");
      const kod = String(credentials?.totp ?? "").trim();
      if (!email || !password) {
        return null;
      }

      // Spärren mot upprepade försök (migration 125, lib/auth/inloggningsregler.ts).
      // Den sitter HÄR och inte i server actionen, så att den också gäller den
      // som postar direkt till /api/auth/callback/credentials. Ett spärrat
      // försök prövar aldrig lösenordet, och spärren räknas likadant för en
      // adress utan konto: beskedet avslöjar inte vilka adresser som finns.
      //
      // Andra steget, tvåstegsverifiering (migration 128), gäller bara konton
      // som aktiverat den och omfattas av SAMMA spärr: en fel eller redan
      // använd kod räknas som ett misslyckat försök på adressen och IP:t, och
      // räknaren nollställs först när båda stegen gått igenom. Ordningen och
      // reglerna står i lib/auth/inloggningssteg.ts (testad utan databas).
      const headers = request?.headers ?? null;
      let user: UserRow | null = null;
      const utfall = await loggaIn(kod, {
        arSparrad: async () => Boolean(await arSparrad("inloggning", email, headers)),
        // Direkt SQL mot auth.users (scrypt). GoTrue-adaptern från
        // Supabase-tiden är borttagen 2026-11-18 (docs/BESLUT.md).
        hittaKonto: async () => {
          user = await findUserByEmail(email);
          return user ? { id: user.id, losenordshash: user.encrypted_password } : null;
        },
        // Verifiera ALLTID, även när kontot saknas: ett tidigt `return null`
        // gör svarstiden till ett orakel för vilka adresser som finns.
        provaLosenord: (hash) => verifyPassword(password, hash),
        registreraMisslyckat: async () => Boolean(await registreraForsok("inloggning", email, headers)),
        nollstall: () => nollstallEpost("inloggning", email),
        // Ett uppslagsfel kastar (fail closed, lib/auth/tvafaktor.ts).
        lasTvafaktor,
        provaKod: provaOchForbruka
      });

      switch (utfall.typ) {
        case "sparrad":
          throw new ForMangaForsok();
        case "tvafaktor_kravs":
          throw new TvafaktorKravs();
        case "tvafaktor_fel":
          throw new TvafaktorFel();
        case "fel":
          return null;
      }
      const rad = user as UserRow | null;
      return {
        id: utfall.konto.id,
        email: rad?.email ?? email,
        name: (rad?.raw_user_meta_data?.full_name as string | undefined) ?? null,
        tvafaktor: utfall.tvafaktor
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
      // Ett konto med tvåstegsverifiering loggar in med lösenord och kod. Google
      // och Microsoft hade annars varit en väg runt andra steget.
      if ((await lasTvafaktor(row.id))?.aktiv) {
        return false;
      }
      user.id = row.id;
      return true;
    },
    async jwt({ token, user }) {
      // Identiteten, och om inloggningen gick igenom andra steget. Allt annat
      // läses färskt där det används. Markeringen sätts bara vid inloggningen
      // (då `user` finns) och kan inte läggas till i efterhand: en session som
      // utfärdats före tvåfaktorns aktivering, eller via Google/Microsoft,
      // saknar den för alltid (Codex-granskningen 2026-11-19).
      if (user?.id) {
        token.sub = user.id;
        token.tvafaktor = user.tvafaktor === true;
        await ensureWorkspace(user.id);
      }
      return token;
    },
    async session({ session, token }) {
      session.user.id = token.sub ?? "";
      session.user.tvafaktor = token.tvafaktor === true;
      return session;
    }
  }
});

export type SessionUser = { id: string; email: string | null; name: string | null; tvafaktor?: boolean };

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
    name: session.user.name ?? null,
    tvafaktor: session.user.tvafaktor === true
  };
}

export async function requireUser(): Promise<SessionUser> {
  const user = await getUser();
  if (!user) {
    throw new Error("Unauthorized");
  }
  return user;
}
