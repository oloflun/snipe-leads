"use server";

import { createClient } from "@/lib/supabase/server";
import { redirect } from "next/navigation";

export type AuthActionResult = {
  success: boolean;
  error?: string;
  message?: string;
};

function getSiteUrl(): string {
  return process.env.NEXT_PUBLIC_SITE_URL ?? "http://localhost:3000";
}

// Supabase svarar på engelska med meddelanden skrivna för utvecklare. Användaren
// såg dem rakt av och hade ingen chans att förstå vad som gick fel — särskilt
// "Email not confirmed", som var det verkliga stoppet vid registrering med
// privat mailadress. Okända fel går fram i original hellre än att sväljas.
const errorMessages: Record<string, string> = {
  "invalid login credentials": "Fel e-postadress eller lösenord.",
  "email not confirmed":
    "Adressen är inte verifierad än. Klicka på länken i mailet vi skickade — kolla skräpposten om det inte kommit fram.",
  "user already registered":
    "Det finns redan ett konto med den adressen. Logga in, eller använd magic link om du glömt lösenordet.",
  // Ingen siffra här: minimilängden sätts i Supabase och kan ändras utan att
  // den här filen rörs. Ett hårdkodat tal skulle då ljuga för användaren.
  "password should be at least 6 characters": "Lösenordet är för kort.",
  "unable to validate email address: invalid format": "Kontrollera e-postadressen — formatet ser fel ut.",
  "email rate limit exceeded":
    "För många mail har skickats till den adressen den senaste timmen. Vänta en stund och försök igen.",
  "over_email_send_rate_limit":
    "För många mail har skickats till den adressen den senaste timmen. Vänta en stund och försök igen.",
  "signups not allowed for this instance":
    "Registrering är avstängd för den här sajten. Be om en inbjudan istället."
};

function authErrorMessage(message: string): string {
  return errorMessages[message.trim().toLowerCase()] ?? message;
}

export async function signInWithPassword(
  email: string,
  password: string,
  nextPath = "/dashboard"
): Promise<AuthActionResult> {
  const supabase = await createClient();
  const { error } = await supabase.auth.signInWithPassword({ email, password });

  if (error) {
    return { success: false, error: authErrorMessage(error.message) };
  }

  // Konton som skapades innan signup-triggern lagades saknar profilrad. Utan
  // detta hamnar de i en oändlig loop mellan /dashboard och /onboarding.
  await ensureWorkspace(supabase);

  redirect(nextPath);
}

type SupabaseServerClient = Awaited<ReturnType<typeof createClient>>;

async function ensureWorkspace(supabase: SupabaseServerClient): Promise<void> {
  const { error } = await supabase.rpc("ensure_workspace_for_current_user");
  if (error) {
    // Inloggningen ska inte falla på detta — proxyn skickar användaren till
    // /onboarding, som försöker igen och visar felet där om det kvarstår.
    console.error("ensure_workspace_for_current_user:", error.message);
  }
}

export async function signUpWithPassword(
  email: string,
  password: string,
  fullName: string
): Promise<AuthActionResult> {
  const supabase = await createClient();
  const { error } = await supabase.auth.signUp({
    email,
    password,
    options: {
      data: { full_name: fullName },
      emailRedirectTo: `${getSiteUrl()}/auth/callback?next=/onboarding`
    }
  });

  if (error) {
    return { success: false, error: authErrorMessage(error.message) };
  }

  const {
    data: { session }
  } = await supabase.auth.getSession();

  if (session) {
    redirect("/onboarding");
  }

  // Utan session krävs verifiering. Den gamla texten ("Du kan nu logga in") var
  // fel: användaren gjorde som den blev tillsagd och möttes av "Email not
  // confirmed" — vilket var precis så registreringen upplevdes som trasig.
  return {
    success: true,
    message: `Vi har skickat en verifieringslänk till ${email}. Klicka på den för att aktivera kontot — kolla skräpposten om mailet inte dyker upp inom några minuter.`
  };
}

// /emails finns inte. Routen heter /dashboard/emails (lib/routes.ts), så varje
// magic link utan explicit ?next= landade i en 404 — inloggningen lyckades,
// användaren såg en felsida, och felet såg ut att sitta i inloggningen.
export async function signInWithMagicLink(
  email: string,
  nextPath = "/dashboard/emails"
): Promise<AuthActionResult> {
  const supabase = await createClient();
  const { error } = await supabase.auth.signInWithOtp({
    email,
    options: {
      emailRedirectTo: `${getSiteUrl()}/auth/callback?next=${encodeURIComponent(nextPath)}`
    }
  });

  if (error) {
    return { success: false, error: authErrorMessage(error.message) };
  }

  return {
    success: true,
    message: `Magic link skickad till ${email}. Kontrollera inkorgen — och skräpposten.`
  };
}

/**
 * Glömt lösenord, steg 1: skicka återställningslänken.
 *
 * Svarar ALLTID likadant, även när adressen inte finns. Ett "den adressen är
 * okänd" hade gjort formuläret till en kontolista för vem som helst att fråga.
 */
export async function requestPasswordReset(email: string): Promise<AuthActionResult> {
  const supabase = await createClient();
  const { error } = await supabase.auth.resetPasswordForEmail(email, {
    // Via callbacken, inte direkt till /auth/reset. Länken bär en PKCE-kod som
    // måste växlas in mot en session, och det kräver skrivbara cookies — vilket
    // en server component inte har. /auth/callback är redan den route som gör
    // exakt det, och att bygga en andra hade betytt två kodvägar för samma
    // växling.
    redirectTo: `${getSiteUrl()}/auth/callback?next=/auth/reset`
  });

  if (error) {
    // Takgränser och formatfel går fram — de säger inget om huruvida kontot
    // finns, och att svälja dem hade lämnat användaren att vänta på ett mail
    // som aldrig skickades.
    return { success: false, error: authErrorMessage(error.message) };
  }

  return {
    success: true,
    message: `Om det finns ett konto på ${email} har vi skickat en återställningslänk dit. Kolla skräpposten om den inte dyker upp inom några minuter.`
  };
}

/**
 * Glömt lösenord, steg 2: sätt det nya.
 *
 * Kräver att recovery-sessionen redan är växlad in av /auth/reset. Utan
 * session kastar updateUser, och det är rätt — annars hade en oinloggad kunnat
 * posta hit och byta lösenord på vem som helst.
 */
export async function updatePassword(password: string): Promise<AuthActionResult> {
  const supabase = await createClient();

  const {
    data: { user }
  } = await supabase.auth.getUser();
  if (!user) {
    return {
      success: false,
      error: "Återställningslänken är inte längre giltig. Begär en ny nedan."
    };
  }

  const { error } = await supabase.auth.updateUser({ password });
  if (error) {
    return { success: false, error: authErrorMessage(error.message) };
  }

  return { success: true, message: "Lösenordet är bytt. Du är inloggad." };
}

/**
 * Google och Microsoft 365.
 *
 * Callbacken finns redan och gör rätt: exchangeCodeForSession följt av RPC
 * ensure_workspace_for_current_user. Inbjudningsmodellen håller automatiskt —
 * triggern on_auth_user_created läser workspace_invites oavsett inloggningssätt
 * (006_auth_selfheal.sql).
 *
 * Kräver konsolmoment som inte går att göra härifrån: OAuth-app hos Google
 * Cloud respektive Microsoft Entra, client id/secret in i Supabase Auth
 * Providers. Checklistan står i AUTH.md.
 */
export async function signInWithOAuth(
  provider: "google" | "azure",
  nextPath = "/dashboard"
): Promise<AuthActionResult & { url?: string }> {
  const supabase = await createClient();
  const { data, error } = await supabase.auth.signInWithOAuth({
    provider,
    options: {
      redirectTo: `${getSiteUrl()}/auth/callback?next=${encodeURIComponent(nextPath)}`,
      // Servern får aldrig följa redirecten själv — klienten ska navigera dit,
      // annars hamnar användaren hos providern i en fetch utan webbläsare.
      skipBrowserRedirect: true
    }
  });

  if (error) {
    return { success: false, error: authErrorMessage(error.message) };
  }
  if (!data?.url) {
    return {
      success: false,
      error: `${provider === "google" ? "Google" : "Microsoft"}-inloggning är inte aktiverad i Supabase Auth ännu. Se AUTH.md.`
    };
  }

  return { success: true, url: data.url };
}

export async function signOut(): Promise<void> {
  const supabase = await createClient();
  await supabase.auth.signOut();
  redirect("/login");
}