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
};

export type OnboardingActionResult = {
  success: boolean;
  error?: string;
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
  let profile = await getProfileForUser(user.id);

  if (!profile) {
    // "Försök logga in igen" var en återvändsgränd: en ny inloggning gav aldrig
    // en profilrad, eftersom bara signup-triggern kunde skapa den. Läk istället.
    const { error: repairError } = await supabase.rpc("ensure_workspace_for_current_user");
    if (repairError) {
      return {
        success: false,
        error: `Ditt konto saknar ett workspace och kunde inte repareras: ${repairError.message}`
      };
    }
    profile = await getProfileForUser(user.id);
  }

  if (!profile) {
    return { success: false, error: "Ditt konto saknar ett workspace. Kontakta support." };
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

  redirect("/dashboard");
}