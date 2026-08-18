"use server";

import { redirect } from "next/navigation";
import { AuthError } from "next-auth";

import { randomBytes, randomUUID } from "node:crypto";

import { auth, ensureWorkspace, signIn, signOut as authSignOut } from "@/lib/auth";
import { sql } from "@/lib/db";
import { hashPassword } from "@/lib/password";
import { hasSupabaseAuthEnv, supabaseAuth } from "@/lib/supabase-auth";

export type AuthActionResult = {
  success: boolean;
  error?: string;
  message?: string;
};

// De svenska felmeddelandena är skrivna FÖR ANVÄNDAREN och överlever bytet av
// auth-leverantör med flit. Supabase svarade på engelska med utvecklartexter;
// Auth.js svarar med feltyper. Nycklarna nedan är därför både de gamla
// Supabase-strängarna (så inget tappas om något fortfarande kastar dem) och
// Auth.js egna typnamn. Okända fel går fram i original hellre än att sväljas.
const errorMessages: Record<string, string> = {
  // Meddelandet säger medvetet INTE om det var adressen eller lösenordet som
  // var fel. Att skilja dem åt hade gjort inloggningen till ett verktyg för
  // att ta reda på vilka adresser som har konton hos oss.
  //
  // Men "fel e-postadress eller lösenord" ensamt är en återvändsgränd för den
  // som glömt sitt lösenord — och det är det vanligaste skälet till att man
  // ser meddelandet. Uppmätt i produktionens auth-loggar 2026-08-17: fyra
  // misslyckade inloggningar i rad mot ett konto som fanns, med ett lösenord
  // satt två månader tidigare. Vägen ut fanns på sidan hela tiden, i en flik
  // användaren inte tittade i.
  "credentialssignin": "Fel e-postadress eller lösenord.",
  "invalid login credentials":
    "Fel e-postadress eller lösenord. Har du glömt lösenordet? Välj Glömt lösenordet? "
    + "ovan.",
  "email not confirmed":
    "Adressen är inte verifierad än. Klicka på länken i mailet vi skickade — kolla skräpposten om det inte kommit fram.",
  "user already registered":
    "Det finns redan ett konto med den adressen. Logga in, eller använd magic link om du glömt lösenordet.",
  "password should be at least 6 characters": "Lösenordet är för kort.",
  "unable to validate email address: invalid format": "Kontrollera e-postadressen — formatet ser fel ut.",
  "email rate limit exceeded":
    "För många mail har skickats till den adressen den senaste timmen. Vänta en stund och försök igen.",
  "over_email_send_rate_limit":
    "För många mail har skickats till den adressen den senaste timmen. Vänta en stund och försök igen.",
  "signups not allowed for this instance":
    "Registrering är avstängd för den här sajten. Be om en inbjudan istället.",
  "oauthaccountnotlinked":
    "Adressen finns redan med ett annat inloggningssätt. Logga in på det sätt du använde första gången."
};

function authErrorMessage(message: string): string {
  return errorMessages[message.trim().toLowerCase()] ?? message;
}

// Minimilängden står här nu, inte i Supabase. Åtta i stället för sex: när talet
// ändå flyttar in i kodbasen finns ingen anledning att ärva den svagare gränsen.
const MIN_PASSWORD_LENGTH = 8;

export async function signInWithPassword(
  email: string,
  password: string,
  nextPath = "/dashboard"
): Promise<AuthActionResult> {
  // Utan databas finns ingen att logga in. Det här är en tydlig konfig-felsträng
  // i stället för en generisk 500 "This page couldn't load" som inte säger något
  // om orsaken — den slog till i varje deploy där DATABASE_URL saknades.
  const { hasDatabase } = await import("@/lib/db");
  if (!hasDatabase()) {
    return {
      success: false,
      error: "Inloggningen är inte konfigurerad i den här miljön (DATABASE_URL saknas). Kontakta support."
    };
  }

  try {
    await signIn("credentials", { email, password, redirect: false });
  } catch (error) {
    if (error instanceof AuthError) {
      return { success: false, error: authErrorMessage(error.type) };
    }
    // Saknad AUTH_SECRET kastar inte AuthError. Samma princip som ovan: en
    // tydlig sträng i stället för en generisk 500.
    if (!process.env.AUTH_SECRET) {
      return {
        success: false,
        error: "Inloggningen är inte konfigurerad i den här miljön (AUTH_SECRET saknas). Kontakta support."
      };
    }
    throw error;
  }

  // Konton som skapades innan signup-triggern lagades saknar profilrad. Utan
  // detta hamnar de i en oändlig loop mellan /dashboard och /onboarding.
  const session = await auth();
  if (session?.user?.id) {
    await ensureWorkspace(session.user.id);
  }

  redirect(nextPath);
}

export async function signUpWithPassword(
  email: string,
  password: string,
  fullName: string
): Promise<AuthActionResult> {
  if (password.length < MIN_PASSWORD_LENGTH) {
    return { success: false, error: "Lösenordet är för kort." };
  }

  // Supabase-stacken: GoTrue skapar användaren (bcrypt) och triggern skapar
  // workspacen. Ingen direkt SQL mot auth.users.
  if (hasSupabaseAuthEnv()) {
    const { error } = await supabaseAuth().auth.signUp({
      email,
      password,
      options: { data: { full_name: fullName } }
    });
    if (error) {
      return { success: false, error: authErrorMessage(error.message) };
    }
    return signInWithPassword(email, password, "/onboarding");
  }

  // Railway: direkt SQL (scrypt).
  const existing = await sql<{ id: string }>(
    "select id from auth.users where lower(email) = lower($1)",
    [email]
  );
  if (existing.length > 0) {
    return { success: false, error: authErrorMessage("user already registered") };
  }

  // Insert i auth.users fyrar triggern on_auth_user_created, som skapar
  // workspace + profil och löser in en eventuell inbjudan (006_auth_selfheal).
  // Hela inbjudningsmodellen håller alltså oförändrad genom leverantörsbytet.
  //
  // email_confirmed_at sätts direkt: det finns ingen utgående mailväg i den här
  // kodlinjen, så ett overifierat konto hade varit permanent utelåst. Att låtsas
  // om en verifiering som ingen kan slutföra är värre än att inte ha någon.
  try {
    await sql(
      `insert into auth.users (email, encrypted_password, raw_user_meta_data, email_confirmed_at)
       values ($1, $2, jsonb_build_object('full_name', $3::text), now())`,
      [email, await hashPassword(password), fullName]
    );
  } catch (error) {
    return { success: false, error: authErrorMessage((error as Error).message) };
  }

  return signInWithPassword(email, password, "/onboarding");
}

/**
 * Starta en demo — en isolerad workspace UTAN förladdad data, där besökaren
 * får testa mot sitt eget bolag med begränsat antal körningar.
 *
 * En demo behöver ingen riktig mail eller ett lösenord användaren känner till:
 * identiteten skapas med slumpade värden, triggern on_auth_user_created skapar
 * workspacen, och vi märker den `is_demo` så löptaket och uppgraderingsvägen
 * kan skilja den från ett fullt konto. Användaren skickas till /onboarding för
 * att lägga in sina egna uppgifter.
 */
export async function startDemo(): Promise<AuthActionResult> {
  const email = `demo-${randomUUID()}@snajp.se`;
  const password = randomBytes(24).toString("base64url");

  // Supabase-stacken: GoTrue skapar demoanvändaren, triggern skapar workspacen.
  if (hasSupabaseAuthEnv()) {
    const { data, error } = await supabaseAuth().auth.signUp({
      email,
      password,
      options: { data: { full_name: "Demo" } }
    });
    if (error || !data.user) {
      return { success: false, error: "Demo kunde inte startas. Försök igen." };
    }
    await sql(
      `update public.workspaces set is_demo = true
       from public.profiles p where workspaces.id = p.workspace_id and p.id = $1`,
      [data.user.id]
    );
    return signInWithPassword(email, password, "/onboarding");
  }

  // Railway: direkt SQL (scrypt).
  try {
    const rows = await sql<{ id: string }>(
      `insert into auth.users (email, encrypted_password, raw_user_meta_data, email_confirmed_at)
       values ($1, $2, jsonb_build_object('full_name', 'Demo'), now()) returning id`,
      [email, await hashPassword(password)]
    );
    // Triggern skapade workspacen med is_demo=false; markera den här.
    await sql(
      `update public.workspaces set is_demo = true
       from public.profiles p where workspaces.id = p.workspace_id and p.id = $1`,
      [rows[0].id]
    );
  } catch (error) {
    return { success: false, error: "Demo kunde inte startas. Försök igen." };
  }

  return signInWithPassword(email, password, "/onboarding");
}

/**
 * Demo-åtkomst: besökaren lämnar sin mejl, vi skickar en åtkomstlänk.
 *
 * Ingen auto-inloggning och ingen magic link som ger full åtkomst — bara en
 * ruta där de fyller i sin mejl. Sändvägen (email_pipeline/sender.py) är inte
 * kopplad, så det svarar ärligt i stället för att låtsas skicka en länk.
 */
export async function requestDemoAccess(
  email: string,
  // Behålls i signaturen: anropsstället skickar den, och att ta bort parametern
  // hade dolt att vägen ska tillbaka så snart en sändväg finns.
  _nextPath = "/dashboard/emails"
): Promise<AuthActionResult> {
  return {
    success: false,
    error: "Åtkomstlänken kan inte skickas än — den utgående mailvägen är inte kopplad. Mejla hej@snajp.se så ordnar vi en demo direkt."
  };
}

/**
 * Glömt lösenord, steg 1.
 *
 * Samma sak: återställningsmail kräver en sändväg. Formuläret finns kvar och
 * svarar ärligt i stället för att svara "om kontot finns har vi skickat" på ett
 * mail som aldrig lämnar servern.
 */
export async function requestPasswordReset(email: string): Promise<AuthActionResult> {
  return {
    success: false,
    error: `Återställning via mail är inte kopplad än. Kontakta support så återställs lösenordet manuellt. (${email})`
  };
}

/**
 * Glömt lösenord, steg 2: sätt det nya.
 *
 * Kräver en inloggad session. Utan session kastar den, och det är rätt —
 * annars hade en oinloggad kunnat posta hit och byta lösenord på vem som helst.
 */
export async function updatePassword(password: string): Promise<AuthActionResult> {
  if (password.length < MIN_PASSWORD_LENGTH) {
    return { success: false, error: "Lösenordet är för kort." };
  }

  const session = await auth();
  if (!session?.user?.id) {
    return {
      success: false,
      error: "Återställningslänken är inte längre giltig. Begär en ny nedan."
    };
  }

  await sql("update auth.users set encrypted_password = $2, updated_at = now() where id = $1", [
    session.user.id,
    await hashPassword(password)
  ]);

  return { success: true, message: "Lösenordet är bytt. Du är inloggad." };
}

/**
 * Google och Microsoft 365.
 *
 * Auth.js har providers för båda. Samma OAuth-appar som förut, ny callback-URL:
 * `/api/auth/callback/google` respektive `/api/auth/callback/microsoft-entra-id`
 * i stället för Supabases. Inbjudningsmodellen håller automatiskt — triggern
 * on_auth_user_created fyrar på insert i auth.users oavsett inloggningssätt.
 */
export async function signInWithOAuth(
  provider: "google" | "azure",
  nextPath = "/dashboard"
): Promise<AuthActionResult & { url?: string }> {
  const providerId = provider === "google" ? "google" : "microsoft-entra-id";
  const configured =
    provider === "google" ? process.env.AUTH_GOOGLE_ID : process.env.AUTH_MICROSOFT_ENTRA_ID_ID;

  if (!configured) {
    return {
      success: false,
      error: `${provider === "google" ? "Google" : "Microsoft"}-inloggning är inte konfigurerad än. Se AUTH.md.`
    };
  }

  // Servern får aldrig följa redirecten själv — klienten ska navigera dit,
  // annars hamnar användaren hos providern i en fetch utan webbläsare.
  return {
    success: true,
    url: `/api/auth/signin/${providerId}?callbackUrl=${encodeURIComponent(nextPath)}`
  };
}

export async function signOut(): Promise<void> {
  await authSignOut({ redirectTo: "/login" });
}
