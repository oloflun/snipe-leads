"use server";

import type { BusinessContextInsert } from "@/lib/database.types";
import { redirect } from "next/navigation";

export type OnboardingInput = {
  product: string;
  targetAudience: string;
  industries: string;
  geography: string;
  tone: string;
  offer: string;
  cta: string;
  contactRoles: string;
  // Supportsidan — valfria. Lämnas de tomma fungerar onboarding precis som
  // förut, men kundservice-agenten saknar då underlag och eskalerar allt.
  companyName?: string;
  guarantee?: string;
  terms?: string;
  delivery?: string;
  returnsPolicy?: string;
  supportEmail?: string;
};

export type OnboardingActionResult = {
  success: boolean;
  error?: string;
  /** Hur det gick att lära upp supportagenten. Blockerar aldrig onboarding. */
  supportAgent?: { synced: boolean; articles: number; error?: string };
};

function splitList(value: string): string[] {
  return value
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

export async function saveBusinessContext(input: OnboardingInput): Promise<OnboardingActionResult> {
  const { createClient } = await import("@/lib/supabase/server");
  const supabase = await createClient();
  const {
    data: { user }
  } = await supabase.auth.getUser();

  if (!user) {
    return { success: false, error: "Du måste vara inloggad." };
  }

  const { getProfileForUser } = await import("@/lib/workspace");
  const profile = await getProfileForUser(user.id);
  if (!profile) {
    return { success: false, error: "Profil saknas. Försök logga in igen." };
  }

  const payload: BusinessContextInsert = {
    workspace_id: profile.workspace_id,
    product: input.product.trim(),
    target_audience: input.targetAudience.trim(),
    industries: splitList(input.industries),
    geography: splitList(input.geography),
    tone: input.tone.trim(),
    offer: input.offer.trim(),
    cta: input.cta.trim(),
    contact_roles: splitList(input.contactRoles),
    company_name: input.companyName?.trim() || null,
    guarantee: input.guarantee?.trim() || null,
    terms: input.terms?.trim() || null,
    delivery: input.delivery?.trim() || null,
    returns_policy: input.returnsPolicy?.trim() || null,
    support_email: input.supportEmail?.trim() || null,
    updated_at: new Date().toISOString()
  };

  const { data: existing, error: lookupError } = await supabase
    .from("business_contexts")
    .select("id")
    .eq("workspace_id", profile.workspace_id)
    .maybeSingle<{ id: string }>();

  if (lookupError) {
    return { success: false, error: lookupError.message };
  }

  const { error } = existing
    ? await supabase.from("business_contexts").update(payload).eq("id", existing.id)
    : await supabase.from("business_contexts").insert(payload);

  if (error) {
    return { success: false, error: error.message };
  }

  // Lär upp kundservice-agenten på bolagets egna villkor. Bäst-möjligt: går
  // backenden inte att nå ska onboarding ändå slutföras — profilen ligger kvar
  // i databasen och kan synkas om från inställningarna.
  const { syncCompanyProfileToSnajp } = await import("@/lib/snajp/profile");
  const sync = await syncCompanyProfileToSnajp({
    companyName: input.companyName,
    product: input.product,
    targetAudience: input.targetAudience,
    tone: input.tone,
    guarantee: input.guarantee,
    terms: input.terms,
    delivery: input.delivery,
    returnsPolicy: input.returnsPolicy,
    supportEmail: input.supportEmail
  });

  if (sync.synced) {
    await supabase
      .from("business_contexts")
      .update({ support_synced_at: new Date().toISOString() })
      .eq("workspace_id", profile.workspace_id);
  }

  redirect("/dashboard");
}