"use server";

import { SNAJP_SUPPORT_URL } from "@/app/api/snajp-support/_lib";
import { readJson } from "@/lib/http/json";
import { sparaBusinessContext } from "@/lib/data/business-context";
import { requireSnajpTenant } from "@/lib/snajp/tenant";
import { aktivVy } from "@/lib/vy";
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
 * ## Varför demo OCH kundbesök går en annan väg
 *
 * `business_contexts` är RLS-scopad mot ARBETSYTAN, inte mot tenanten. I
 * demovyn OCH i ett kundbesök (`aktivVy().vy === "kund"`, se lib/vy.ts) är
 * arbetsytan fortfarande adminens egen medan tenanten är demokontots eller
 * den namngivna kundens — en skrivning hade alltså landat på Snajps rad
 * medan agenten läser en annan tenant, och formuläret hade visat Snajps svar
 * i den besökta kundens inställningar (bekräftat i produktion 2026-09-02:
 * två olika kundbesök visade identiskt Snajp-innehåll). Där är
 * kontextdokumentet i backenden enda sanning, och det är ändå det enda
 * agenten läser (se docstringen nedan).
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

//: Rubrikerna som skrivs till kontextdokumentet, och läses tillbaka ur det.
//: EN karta, inte två listor: skrivningen och läsningen måste vara varandras
//: inverser, och två separata listor glider isär vid första omformuleringen.
const RUBRIKER: [keyof Affarskontextfalt, string][] = [
  ["product", "Vad vi säljer"],
  ["target_audience", "Vem vi säljer till"],
  ["offer", "Erbjudande"],
  ["cta", "Nästa steg vi vill ha"]
];

function tillDokument(input: Affarskontextfalt): string {
  return RUBRIKER.map(([falt, rubrik]) => [rubrik, input[falt].trim()] as const)
    .filter(([, varde]) => varde)
    .map(([rubrik, varde]) => `${rubrik}: ${varde}`)
    .join("\n\n");
}

function franDokument(content: string): Affarskontextfalt {
  const falt: Affarskontextfalt = { product: "", target_audience: "", offer: "", cta: "" };
  for (const stycke of content.split(/\n\n+/)) {
    const traff = RUBRIKER.find(([, rubrik]) => stycke.startsWith(`${rubrik}: `));
    if (traff) {
      falt[traff[0]] = stycke.slice(traff[1].length + 2).trim();
    }
  }
  return falt;
}

/** Senaste `product_marketing`-dokumentet från backenden, för demovyn. */
async function hamtaFranAgenten(): Promise<Affarskontextfalt | null> {
  try {
    const tenant = await requireSnajpTenant();
    const response = await fetch(
      `${SNAJP_SUPPORT_URL}/api/leads/context-docs?kind=product_marketing`,
      {
        headers: { "X-API-Key": tenant.apiKey },
        cache: "no-store",
        signal: AbortSignal.timeout(60_000)
      }
    );
    // readJson och inte response.json(): en sovande backend svarar med en
    // HTML-sida medan den vaknar, och ett dött anrop svarar utan kropp alls.
    // Båda ger "Unexpected end of JSON input" långt från orsaken (INV-API-001).
    const data = await readJson<{ docs?: { content?: string; version?: number }[] }>(response);
    if (!data) return { product: "", target_audience: "", offer: "", cta: "" };
    // Högsta version, inte första eller sista i listan: Postgres sorterar
    // `created_at desc` och MemoryStorage gör det inte, så en index-baserad
    // gissning ger olika dokument i sviten och i drift. `version` räknas upp
    // per (tenant, kind) av save_context_doc och är den ordning som gäller.
    const senaste = [...(data.docs ?? [])].sort(
      (a, b) => (b.version ?? 0) - (a.version ?? 0)
    )[0]?.content;
    return senaste
      ? franDokument(senaste)
      : { product: "", target_audience: "", offer: "", cta: "" };
  } catch {
    return null;
  }
}

export async function hamtaAffarskontext(): Promise<Affarskontextfalt | null> {
  // Demo OCH kundbesök: samma väg, av samma skäl (se filens docstring).
  // `business_contexts` är RLS-scopad mot arbetsytan, och vid ett kundbesök
  // är arbetsytan fortfarande adminens EGEN — bara backend-nyckeln pekar på
  // kunden. Ett kundbesök som lästes härifrån visade därför alltid Snajps
  // egna rad, oavsett vilken namngiven kund bannern sa.
  if ((await aktivVy()).vy !== "admin") {
    return hamtaFranAgenten();
  }

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
      error: "Skriv en rad om vad ni säljer. Det är det agenterna ska sälja."
    };
  }

  // Demo OCH kundbesök: bara till agenten, aldrig till arbetsytans egen rad.
  // Samma root cause som i hamtaAffarskontext — en sparning härifrån under
  // ett kundbesök skrev annars över Snajps EGEN business_contexts-rad, inte
  // den besökta kundens. Ett misslyckande är då ett riktigt fel — det finns
  // ingen rad i arbetsytan som räddar texten om backenden inte svarar.
  if ((await aktivVy()).vy !== "admin") {
    const varning = await skickaTillAgenten(input, produkt);
    return varning ? { success: false, error: varning } : { success: true };
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
  const dokument = tillDokument({ ...input, product: produkt });

  try {
    const tenant = await requireSnajpTenant();
    const response = await fetch(`${SNAJP_SUPPORT_URL}/api/leads/context-docs`, {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-API-Key": tenant.apiKey },
      body: JSON.stringify({
        kind: "product_marketing",
        content: dokument,
        source: "settings/affarskontext"
      }),
      // Render och Railway kallstartar. En sparning som faller på en vaknande
      // backend hade sett ut som att texten inte togs emot.
      signal: AbortSignal.timeout(60_000)
    });
    if (!response.ok) {
      return `Sparat. Agenterna hämtar texten först när backenden svarar igen (${response.status}).`;
    }
    return undefined;
  } catch {
    return "Sparat i arbetsytan. Agenterna kunde inte nås just nu och läser texten vid nästa försök.";
  }
}

/**
 * Erbjudandetexten utkastet kräver — SAMMA källa som inställningssidan visar.
 *
 * Leads-UI:t läste tidigare bara `agent_context_docs` (product_marketing) och
 * behandlade HTTP 5xx som "inte ifylld". Settings skriver `business_contexts`
 * och skickar vidare best-effort. Ett fyllt formulär såg därför tomt ut för
 * utkastknappen.
 *
 * Om arbetsytan har produkttext: använd den och backfilla kontextdokumentet.
 * 5xx från agenten är inte "inte ifylld".
 */
export async function lasOffertForUtkast(): Promise<string> {
  const workspace = await hamtaAffarskontext();
  if (!workspace) {
    throw new Error("Du måste vara inloggad för att skapa utkast.");
  }
  const franWorkspace = workspace.product.trim() ? tillDokument(workspace) : "";
  if (franWorkspace) {
    await skickaTillAgenten(workspace, workspace.product.trim());
    return franWorkspace.slice(0, 2000);
  }

  const franAgent = await hamtaFranAgenten();
  const dokument = franAgent && franAgent.product.trim() ? tillDokument(franAgent) : "";
  if (dokument) {
    return dokument.slice(0, 2000);
  }

  throw new Error(
    "Affärskontexten (Vad ni säljer) är inte ifylld ännu. Fyll i den under Inställningar, " +
      "Vad agenterna vet, Affärskontext innan utkast kan skapas."
  );
}
