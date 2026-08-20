"use server";

import { SNAJP_SUPPORT_URL } from "@/app/api/snajp-support/_lib";
import { sparaBusinessContext } from "@/lib/data/business-context";
import { requireSnajpTenant } from "@/lib/snajp/tenant";
import { getBusinessContextForWorkspace, getWorkspaceContext } from "@/lib/workspace";

/**
 * Affärskontexten — vad ni säljer och till vem.
 *
 * ## Varför bara fyra fält
 *
 * Raden i `business_contexts` har nio kolumner. Fyra av dem ägs redan av andra
 * ytor, och att rita dem här hade gett två sanningar om samma sak:
 *
 *  * `tone` hör till röstdokumentet (`/settings/soul`). Två tonrutor på två
 *    sidor betyder att den som skriver i fel ruta inte hörs.
 *  * `industries`, `geography` och `contact_roles` ÄR målgruppen, och den bor i
 *    leads-agentens ICP (`/settings/leads`, `agent_configs.settings.icp`).
 *
 * De kolumnerna läses därför in och skrivs tillbaka orörda. Fälten här är de
 * fyra ingen annan yta äger.
 *
 * ## Varför kontextdokumentet skickas vidare
 *
 * Leads-agenten läser INTE `business_contexts`. Den läser
 * `agent_context_docs` med kind `product_marketing` (se
 * `leads/context_pack.py` och `leads/business_context.py`). Utan den här
 * vidareskickningen kan en kund alltså fylla i hela sidan och ändå mötas av
 * "affärskontext saknas" när de försöker slå på automatiskt utskick — vilket
 * är precis den sortens fel som ser ut som en bugg i grinden.
 */

export type Affarskontextfalt = {
  product: string;
  target_audience: string;
  offer: string;
  cta: string;
};

export type AffarskontextResultat = {
  success: boolean;
  error?: string;
  /** Sparat i arbetsytan, men agenten fick inte kontexten. Inte samma sak som ett fel. */
  varning?: string;
};

export async function hamtaAffarskontext(): Promise<Affarskontextfalt | null> {
  const context = await getWorkspaceContext();
  if (!context) return null;

  const rad = await getBusinessContextForWorkspace(context.workspace.id, context.user.id);
  if (!rad) return { product: "", target_audience: "", offer: "", cta: "" };

  // Platshållaren uppstartsformuläret skriver är inte ett svar kunden gett, och
  // ska inte stå i en ruta de ombeds ändra. Se AVVAKTAR i actions/onboarding.ts.
  const utan = (varde: string) => (varde.startsWith("(läses in") ? "" : varde);

  return {
    product: rad.product ?? "",
    target_audience: utan(rad.target_audience ?? ""),
    offer: utan(rad.offer ?? ""),
    cta: utan(rad.cta ?? "")
  };
}

export async function sparaAffarskontext(
  input: Affarskontextfalt
): Promise<AffarskontextResultat> {
  const context = await getWorkspaceContext();
  if (!context) {
    return { success: false, error: "Du måste vara inloggad." };
  }

  const produkt = input.product.trim();
  if (!produkt) {
    return {
      success: false,
      error: "Skriv en rad om vad ni säljer. Det är det agenten ska sälja."
    };
  }

  const befintlig = await getBusinessContextForWorkspace(context.workspace.id, context.user.id);

  try {
    await sparaBusinessContext(context.user.id, {
      workspace_id: context.workspace.id,
      product: produkt,
      target_audience: input.target_audience.trim(),
      offer: input.offer.trim() || produkt,
      cta: input.cta.trim(),
      // Ägs av andra ytor — se filens docstring. Läses in och skrivs tillbaka.
      tone: befintlig?.tone ?? "",
      industries: befintlig?.industries ?? [],
      geography: befintlig?.geography ?? [],
      contact_roles: befintlig?.contact_roles ?? [],
      updated_at: new Date().toISOString()
    });
  } catch (error) {
    return { success: false, error: (error as Error).message };
  }

  const varning = await skickaTillAgenten(input, produkt);
  return { success: true, varning };
}

/**
 * Vidare till backenden som `product_marketing`-kontextdokument.
 *
 * Fäller aldrig sparningen. Raden i databasen är kundens svar och den är redan
 * skriven; att kasta bort ett lyckat sparande för att backenden sover vore
 * sämre än att säga vad som inte gick. Kunden får en varning, inte ett fel.
 */
async function skickaTillAgenten(
  input: Affarskontextfalt,
  produkt: string
): Promise<string | undefined> {
  const stycken = [
    `Vad vi säljer: ${produkt}`,
    input.target_audience.trim() ? `Vem vi säljer till: ${input.target_audience.trim()}` : null,
    input.offer.trim() ? `Erbjudande: ${input.offer.trim()}` : null,
    input.cta.trim() ? `Nästa steg vi vill ha: ${input.cta.trim()}` : null
  ].filter(Boolean);

  try {
    const tenant = await requireSnajpTenant();
    const response = await fetch(`${SNAJP_SUPPORT_URL}/api/leads/context-docs`, {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-API-Key": tenant.apiKey },
      body: JSON.stringify({
        kind: "product_marketing",
        content: stycken.join("\n\n"),
        source: "settings/affarskontext"
      }),
      // Render och Railway kallstartar. En sparning som faller på en vaknande
      // backend hade sett ut som att texten inte togs emot.
      signal: AbortSignal.timeout(60_000)
    });
    if (!response.ok) {
      return `Sparat. Agenten hämtar texten först när backenden svarar igen (${response.status}).`;
    }
    return undefined;
  } catch {
    return "Sparat i arbetsytan. Agenten kunde inte nås just nu och läser texten vid nästa försök.";
  }
}
