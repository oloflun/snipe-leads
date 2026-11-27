/**
 * Iris utkast i CRM:et: typerna för granskningskön, Skickat och provmejlet som
 * leads-API:t lämnar dem, och anropet till Email Studio (AP15).
 *
 * Samma ändpunkter som dagens Leads (IrisGranskning, SkickatLista,
 * ProvmejlKnapp, EmailStudioEditor). Ingen affärsregel räknas här: vad som får
 * skickas, när och varför inte avgör backenden (scheduler.skicka_godkant,
 * send_guard, sandplan). Gränssnittet visar utfallet och skälet den lämnar.
 */
import { CrmFel } from "@/lib/crm/api";
import { irisAnrop } from "@/lib/crm/iris/anrop";
import type { Localized } from "@/lib/i18n";
import type { KonversationsMejl } from "@/lib/leads/konversation";

/** Kundens signatur, normaliserad av backenden (app/leads/signatur.py). `text` är blocket som står sist i brödtexten. */
export type Signatur = {
  text: string;
  namn: string;
  titel?: string;
  verksamhet?: string;
  telefon?: string;
  epost?: string;
  ort?: string;
  webb?: string;
  bolag?: string;
  logotyp_url?: string;
};

/** En post i granskningskön (`GET /leads/queue`, storage.list_review_queue). */
export type Kopost = {
  id: string;
  subject?: string | null;
  body?: string | null;
  /** Det granskaren och AI:n arbetar på (signatur.dela_utkast). */
  brodtext?: string | null;
  /** Signaturen och den lagstadgade foten: visas, redigeras aldrig. */
  svans?: string | null;
  prospect_email?: string | null;
  prospect_id?: string | null;
  company_name?: string | null;
  contact_name?: string | null;
  contact_role?: string | null;
  website?: string | null;
  lagesbeskrivning?: string | null;
  signaler?: string[] | string | null;
  created_at?: string | null;
  scheduled_at?: string | null;
  thread_id?: string | null;
  message_id?: string | null;
};

export type Kosvar = { items?: Kopost[]; signatur?: Signatur | null };

/** En rad i Skickat (`GET /leads/skickat`), schemalagd eller skickad. */
export type SkickatRad = {
  id: string;
  subject: string | null;
  body: string;
  /** null för ett schemalagt utkast: det har inte gått ut än. */
  sent_at: string | null;
  schemalagt?: boolean;
  skickas_tidigast?: string | null;
  queue_item_id?: string | null;
  thread_id?: string | null;
  prospect_id: string | null;
  company_name: string | null;
  contact_name: string | null;
  prospect_email: string | null;
  svarat: boolean;
  status?: string | null;
  /** Trådens mejl, äldst först. Bara när bolaget svarat. */
  konversation?: KonversationsMejl[];
};

export type Skickatsvar = { skickat?: SkickatRad[]; signatur?: Signatur | null };

/** Utfallet av Godkänn och skicka eller Skicka nu (`approve`, `skicka-nu`). */
export type Sandutfall = { utfall?: string; besked?: string; skal?: string | null; status?: string };

/** Ett besked efter en handling: texten, om den är ett fel, och skälen per bolag. */
export type Besked = { text: string; fel: boolean; orsaker?: string[] };

export const UTAN_AMNE: Localized = { sv: "Utan ämnesrad", en: "No subject line" };

/** Skälet backenden gav, i hela meningar (svenska: sändspärrarnas text finns bara på svenska). */
export function skalUr(s: Sandutfall): string {
  return s.skal || s.besked?.split(": ").slice(1).join(": ") || "";
}

/** Läget en skickad rad står i (LU-083). Ett lead vars status inte flyttats väntar fortfarande på svar. */
export type Skickatlage = "vantar" | "svarat" | "mote" | "ej";

export function skickatlage(r: SkickatRad): Skickatlage {
  const s = r.status ?? "";
  if (s === "replied") return "svarat";
  if (s === "meeting" || s === "won") return "mote";
  if (s === "lost" || s === "suppressed") return "ej";
  return "vantar";
}

export const SKICKATLAGE: Record<Skickatlage, Localized> = {
  vantar: { sv: "Väntar på svar", en: "Awaiting reply" },
  svarat: { sv: "Svarat", en: "Replied" },
  mote: { sv: "Möte", en: "Meeting" },
  ej: { sv: "Ej intresserad", en: "Not interested" }
};

/** Prickens ton per läge: kontaktad ockra, svarat och möte blå, vunnen grön, nej röd (LU-083). */
export function skickatton(r: SkickatRad): "ockra" | "bla" | "mossa" | "fara" {
  if (r.status === "won") return "mossa";
  const l = skickatlage(r);
  return l === "svarat" || l === "mote" ? "bla" : l === "ej" ? "fara" : "ockra";
}

// ---------------------------------------------------------------------------
// Provmejlet (LU-037, LU-087)
// ---------------------------------------------------------------------------

let adresser: Promise<string[]> | null = null;

/** Kundens egna adresser, en gång per sidvisning och delade av alla redigerare. Ett tomt svar hämtas om nästa gång. */
export function provmejlAdresser(): Promise<string[]> {
  adresser ??= irisAnrop<{ mottagare?: string[] }>("/leads/provmejl/mottagare")
    .then((s) => s?.mottagare ?? [])
    .catch(() => [])
    .then((lista) => {
      if (lista.length === 0) adresser = null;
      return lista;
    });
  return adresser;
}

/** Felen provmejlet kan få, i kundens ord (ProvmejlKnapp i dagens Leads). */
export function provmejlFel(e: unknown): Localized {
  if (e instanceof CrmFel) {
    if (e.status === 403) return { sv: "Provmejl går bara till era egna adresser.", en: "Test emails can only go to your own addresses." };
    if (e.status === 503)
      return { sv: "Utskick är inte påslagna i den här miljön, så provet kan inte levereras.", en: "Sending is not switched on in this environment, so the test cannot be delivered." };
    if (e.status === 404) return { sv: "Mejlet finns inte längre.", en: "The email no longer exists." };
    return e.text;
  }
  return { sv: "Provmejlet kunde inte skickas just nu. Försök igen om en stund.", en: "The test email could not be sent right now. Try again in a moment." };
}

// ---------------------------------------------------------------------------
// Email Studio (AP15): skriv om texten med AI, i Next (app/api/email-studio)
// ---------------------------------------------------------------------------

export type Studioval = "shorter" | "rewrite" | "improve" | "personalize" | "translate" | "ab_variants" | "followup" | "analyze";

export const STUDIOVAL: { v: Studioval; namn: Localized }[] = [
  { v: "shorter", namn: { sv: "Kortare", en: "Shorter" } },
  { v: "improve", namn: { sv: "Förbättra", en: "Improve" } },
  { v: "personalize", namn: { sv: "Personalisera", en: "Personalise" } },
  { v: "rewrite", namn: { sv: "Ny vinkel", en: "New angle" } },
  { v: "translate", namn: { sv: "Översätt", en: "Translate" } },
  { v: "ab_variants", namn: { sv: "A/B-varianter", en: "A/B variants" } },
  { v: "followup", namn: { sv: "Uppföljning", en: "Follow-up" } },
  { v: "analyze", namn: { sv: "Analysera", en: "Analyse" } }
];

/** Åtgärder som skriver om texten i fältet direkt. Resten visas bredvid, och du väljer. */
export const DIREKTA: ReadonlySet<Studioval> = new Set(["shorter", "rewrite", "improve", "personalize", "translate"]);

/** Bakgrunden AI:n skriver om utifrån: bolaget, läget hos dem, kundens erbjudande och kontakten. */
export type Studiokontext = {
  companyName?: string | null;
  signal?: string | null;
  offer?: string | null;
  contactName?: string | null;
};

export type Studioresultat = {
  action: Studioval;
  original: string | null;
  ny: string;
  forklaring: string;
  amnen: string[];
  tips: string | null;
  simulerat: boolean;
  orsak: string | null;
};

/** Varför ett svar är förskrivet (`simulated_reason`, app/api/email-studio/route.ts). */
const ORSAKER: Record<string, Localized> = {
  anonym: { sv: "Logga in för att köra åtgärden mot modellen.", en: "Sign in to run this action against the model." },
  "ingen modellnyckel": { sv: "AI-hjälpen är inte påslagen i den här miljön.", en: "AI assistance is not switched on in this environment." },
  kreditslut: { sv: "AI-krediterna är slut hos oss. Din text är orörd.", en: "Our AI credits have run out. Your text is untouched." },
  kvot: { sv: "AI-leverantörens kvot är slut just nu. Prova igen om en stund.", en: "The AI provider's quota is used up right now. Try again in a moment." },
  "tillfälligt fel": { sv: "Modellen svarade inte just nu. Prova igen om en liten stund.", en: "The model did not respond just now. Try again in a moment." }
};
export const simuleringsorsak = (orsak: string | null): Localized => (orsak && ORSAKER[orsak]) || ORSAKER["tillfälligt fel"];

/** Läget hos bolaget som en mening för AI:n: lägesbeskrivningen och signalerna (IrisGranskning.signalFor). */
export function signalUr(lagesbeskrivning: string | null | undefined, signaler: unknown): string | null {
  const lista = Array.isArray(signaler) ? signaler.map(String) : typeof signaler === "string" && signaler.trim() ? [signaler] : [];
  const delar = [lagesbeskrivning?.trim(), lista.length ? `Signaler: ${lista.join("; ")}` : null].filter((d): d is string => Boolean(d));
  return delar.length ? delar.join(" ") : null;
}

/** Kör en åtgärd i Email Studio. Kastar `CrmFel` med en läsbar mening. */
export async function studio(
  action: Studioval,
  amne: string,
  brodtext: string,
  kontext: Studiokontext,
  locale: "sv" | "en",
  harSignatur: boolean
): Promise<Studioresultat> {
  let svar: Response;
  try {
    svar = await fetch("/api/email-studio", {
      method: "POST",
      cache: "no-store",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        action,
        draft: brodtext,
        subject: amne,
        context: {
          companyName: kontext.companyName ?? undefined,
          signal: kontext.signal ?? undefined,
          offer: kontext.offer ?? undefined,
          contactName: kontext.contactName ?? undefined,
          harSignatur
        },
        locale,
        userId: "current-user"
      })
    });
  } catch {
    throw new CrmFel({ sv: "Nätverksfel. Försök igen.", en: "Network error. Try again." }, 0, null);
  }
  const kropp = (await svar.json().catch(() => null)) as {
    success?: boolean;
    error?: string;
    data?: {
      original_version?: string | null;
      new_version?: string;
      body?: string;
      subject?: string;
      subject_suggestions?: string[];
      explanation?: string;
      confidence_tips?: string;
      simulated?: boolean;
      simulated_reason?: string;
    };
  } | null;
  if (!svar.ok || !kropp?.success || !kropp.data) {
    const fel = kropp?.error;
    throw new CrmFel(fel ? { sv: fel, en: fel } : { sv: "Åtgärden gick inte att köra.", en: "That action could not run." }, svar.status, null);
  }
  const d = kropp.data;
  return {
    action,
    original: d.original_version ?? null,
    ny: d.new_version || d.body || brodtext,
    forklaring: d.explanation ?? "",
    amnen: d.subject_suggestions?.length ? d.subject_suggestions : d.subject ? [d.subject] : [],
    tips: d.confidence_tips ?? null,
    simulerat: d.simulated === true,
    orsak: d.simulated_reason ?? null
  };
}
