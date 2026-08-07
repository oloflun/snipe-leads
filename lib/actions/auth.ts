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

export async function signInWithMagicLink(email: string, nextPath = "/emails"): Promise<AuthActionResult> {
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

export async function signOut(): Promise<void> {
  const supabase = await createClient();
  await supabase.auth.signOut();
  redirect("/login");
}