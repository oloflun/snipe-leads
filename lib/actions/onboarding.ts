"use server";

import type { BusinessContextInsert } from "@/lib/database.types";
import { redirect } from "next/navigation";
import { formateraOrgnr, orgnrFel } from "@/lib/orgnr";

/**
 * Fyra fält, inte åtta. Se components/auth/OnboardingForm.tsx om varför de
 * gamla fälten var aktivt skadliga: de var förifyllda med påhittade värden som
 * gick att skicka in rakt av.
 */
export type OnboardingInput = {
  orgnr: string;
  webbplats: string;
  produkt: string;
  fokus: string;
};

export type OnboardingActionResult = {
  success: boolean;
  error?: string;
};

/**
 * Webbadressen normaliseras men VALIDERAS INTE hårt. En kund som skriver
 * "exempel.se" utan protokoll menar https://exempel.se, och att neka den
 * inmatningen hade stoppat onboardingen på en formalitet. Att adressen
 * faktiskt svarar upptäcks när agenten försöker läsa den, och det felet är
 * begripligt på ett sätt som "ogiltig URL" inte är.
 */
function normaliseraWebbplats(rå: string): string {
  const text = (rå ?? "").trim();
  if (!text) return "";
  return /^https?:\/\//i.test(text) ? text : `https://${text}`;
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

  // Serversidan validerar OM. lib/orgnr.ts kör samma kontroll i webbläsaren,
  // men klientkod går att kringgå och det som skyddar är alltid den här sidan.
  const orgnrProblem = orgnrFel(input.orgnr);
  if (orgnrProblem) {
    return { success: false, error: orgnrProblem };
  }

  const webbplats = normaliseraWebbplats(input.webbplats);
  if (!webbplats) {
    return {
      success: false,
      error: "Fyll i webbplatsen. Det är den agenten läser för att förstå er."
    };
  }

  const produkt = input.produkt.trim();
  if (!produkt) {
    return {
      success: false,
      error: "Skriv en rad om vad ni säljer. Det är det agenten ska sälja."
    };
  }

  const fokus = input.fokus.trim();

  // De gamla kolumnerna är not null i schemat och kan inte lämnas tomma. De
  // fylls därför med det agenten VET, inte med gissningar: målgrupp, branscher,
  // geografi och tonläge härleds ur webbplatsen i researchsteget, och att
  // skriva in en gissning här hade gjort gissningen till ett faktum som
  // grundningsgrinden sedan låter agenten citera.
  const AVVAKTAR = "(läses in från webbplatsen)";

  const payload: BusinessContextInsert = {
    workspace_id: profile.workspace_id,
    product: [
      `Organisationsnummer: ${formateraOrgnr(input.orgnr)}`,
      `Webbplats: ${webbplats}`,
      `Vad vi säljer: ${produkt}`,
      fokus ? `Särskilt fokus: ${fokus}` : null
    ]
      .filter(Boolean)
      .join("\n"),
    target_audience: AVVAKTAR,
    industries: [],
    geography: [],
    tone: AVVAKTAR,
    offer: produkt,
    cta: AVVAKTAR,
    contact_roles: [],
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