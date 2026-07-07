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

export async function signInWithPassword(
  email: string,
  password: string,
  nextPath = "/dashboard"
): Promise<AuthActionResult> {
  const supabase = await createClient();
  const { error } = await supabase.auth.signInWithPassword({ email, password });

  if (error) {
    return { success: false, error: error.message };
  }

  redirect(nextPath);
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
    return { success: false, error: error.message };
  }

  const {
    data: { session }
  } = await supabase.auth.getSession();

  if (session) {
    redirect("/onboarding");
  }

  return {
    success: true,
    message: "Kontot skapades. Du kan nu logga in."
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
    return { success: false, error: error.message };
  }

  return {
    success: true,
    message: "Magic link skickad. Kontrollera din inkorg. Du får direkt tillgång till Email Studio."
  };
}

export async function signOut(): Promise<void> {
  const supabase = await createClient();
  await supabase.auth.signOut();
  redirect("/login");
}