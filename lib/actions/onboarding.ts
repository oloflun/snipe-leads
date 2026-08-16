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
  const { auth } = await import("@/lib/auth");
  const session = await auth();
  const user = session?.user;

  if (!user?.id) {
    return { success: false, error: "Du måste vara inloggad." };
  }

  const { getProfileForUser } = await import("@/lib/workspace");
  const { sqlAsUser } = await import("@/lib/db");
  let profile = await getProfileForUser(user.id);

  if (!profile) {
    // "Försök logga in igen" var en återvändsgränd: en ny inloggning gav aldrig
    // en profilrad, eftersom bara signup-triggern kunde skapa den. Läk istället.
    try {
      await sqlAsUser(user.id, "select public.ensure_workspace_for_current_user()");
    } catch (repairError) {
      return {
        success: false,
        error: `Ditt konto saknar ett workspace och kunde inte repareras: ${(repairError as Error).message}`
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

  // En upsert i stället för läs-sen-skriv: unika index på workspace_id gör
  // villkoret till databasens jobb, och två samtidiga sparningar kan inte
  // längre skapa två rader.
  try {
    await sqlAsUser(
      user.id,
      `insert into public.business_contexts
         (workspace_id, product, target_audience, industries, geography, tone, offer, cta, contact_roles, updated_at)
       values ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
       on conflict (workspace_id) do update set
         product = excluded.product,
         target_audience = excluded.target_audience,
         industries = excluded.industries,
         geography = excluded.geography,
         tone = excluded.tone,
         offer = excluded.offer,
         cta = excluded.cta,
         contact_roles = excluded.contact_roles,
         updated_at = excluded.updated_at`,
      [
        payload.workspace_id,
        payload.product,
        payload.target_audience,
        payload.industries,
        payload.geography,
        payload.tone,
        payload.offer,
        payload.cta,
        payload.contact_roles,
        payload.updated_at
      ]
    );
  } catch (error) {
    return { success: false, error: (error as Error).message };
  }

  redirect("/dashboard");
}