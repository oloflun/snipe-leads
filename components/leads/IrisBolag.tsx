"use client";

import { useCallback, useEffect, useState } from "react";
import { EmailStudioEditor } from "@/components/email/EmailStudioEditor";
import { Tidslinje } from "@/components/leads/Tidslinje";
import { SkeletonRows, btnPrimary, btnSecondary, flik, flikAktiv, flikInaktiv, fliklista } from "@/components/ui";
import { mejlaOss } from "@/components/marketing/copy";
import { addonSpec } from "@/lib/addons";
import { offertForUtkast } from "@/lib/leads/offert";
import type { EmailStudioData } from "@/lib/data/emails";
import { demoOversiktSvar } from "@/lib/demo/oversikt";
import { kontaktnamn, type ExempelBolag } from "@/lib/demo/iris-exempel";
import { felmeddelande, readJsonBody } from "@/lib/http/json";
import { sv, useLocale, type Locale, type Localized } from "@/lib/i18n";
import { STATUS_ETIKETT, UTFALL_ETIKETT, kriterier, nivaEtikett } from "@/lib/prospekt";
import { cn } from "@/lib/utils";

/**
 * Leadets detaljpanel (Bedömning, Mejlutkast, Tidslinje) och delarna den
 * behöver. Sidan själv — underflikarna, listan i full bredd och lådan som
 * detaljen öppnas i — bor sedan 2026-10-05 i `components/leads/LeadsSida.tsx`.
 *
 * ## Exempelbolagen
 *
 * "Kör exempelkörningen" i den utfällda panelen lägger de sex fixturbolagen
 * ur `lib/demo/iris-exempel.ts` överst i den RIKTIGA listan, märkta Exempel —
 * inte i en egen, fristående resultatlista. Källan är medvetet den handskrivna
 * fixturen (bolag, signal, utkast) och inte `lib/demo/leads-korning.ts`, som
 * hör till en annan, äldre demoyta.
 */

type Prospekt = {
  id: string;
  company_name: string;
  contact_name: string | null;
  contact_email: string | null;
  contact_role?: string | null;
  /** Registerkällans telefon (migration 081). */
  contact_phone?: string | null;
  status: string;
  origin?: string | null;
  ort: string | null;
  sni: string | null;
  website: string | null;
  orgnr: string | null;
  anstallda?: number | null;
  score_total: number | null;
  icp_fit: number | null;
  qualified: boolean | null;
  disqualifiers: string[] | null;
  score_breakdown: unknown;
  /** Iris-bedömningen (migration 079): nivå A/B/C, motivering och Jev. */
  niva?: "A" | "B" | "C" | null;
  motivering?: string | null;
  jev?: JevData | null;
};

type JevData = {
  triage?: { lage?: string; fit?: number | null; skulle_falla?: boolean; fall_skal?: string[]; stodrad?: string | null } | null;
  klassning?: { lage?: string; sannolikhet?: number | null; trafikniva?: string | null; insats?: string | null } | null;
};

export type ExempelRad = Prospekt & { _exempel: ExempelBolag };

function statusEtikett(status: string, locale: Locale): string {
  return STATUS_ETIKETT[status]?.[locale] ?? status;
}

const T = {
  beslutsfattare: { sv: "Beslutsfattare", en: "Decision maker" },
  anstallda: { sv: "anställda", en: "employees" },
  tjanstenSvararInte: {
    sv: "Tjänsten svarar inte. Försök igen om en minut.",
    en: "The service is not responding. Try again in a minute."
  },
  tomtSvar: { sv: "Backenden svarade utan innehåll.", en: "The backend replied without content." },
  korIris: { sv: "Kör Iris", en: "Run Iris" },
  hittaBolag: { sv: "Hitta bolag", en: "Find companies" },
  hittaBolagText: {
    sv: "Utan filter hittar Iris själv de bolag som passar er produkt bäst, utifrån er sparade målgrupp.",
    en: "Without filters, Iris finds the companies that fit your product best, based on your saved target audience."
  },
  exempelOverst: { sv: "Exempelbolag läggs överst i listan.", en: "Example companies are added to the top of the list." },
  kor: { sv: "Kör…", en: "Running…" },
  allaTillagda: { sv: "Alla tillagda", en: "All added" },
  allaExempelTillagda: { sv: "Alla exempelbolag tillagda", en: "All example companies added" },
  korExempel: { sv: "Kör exempel", en: "Run example" },
  korExempelkorningen: { sv: "Kör exempelkörningen", en: "Run the example" },
  vy: { sv: "Vy", en: "View" },
  doljBortvalda: { sv: "Dölj bortvalda", en: "Hide rejected" },
  bolag: { sv: "Bolag", en: "Companies" },
  ingaBolag: { sv: "Inga bolag ännu", en: "No companies yet" },
  exempel: { sv: "Exempel", en: "Example" },
  researchar: { sv: "Researchar", en: "Researching" },
  valjBolag: { sv: "Välj ett lead i listan.", en: "Pick a lead in the list." },
  bolagenKundeInte: { sv: "Bolagen kunde inte hämtas", en: "Could not load the companies" },
  forsokIgen: { sv: "Försök igen", en: "Try again" },
  tillval: { sv: "Tillval", en: "Add-on" },
  utkastTogForLang: { sv: "Utkastet tog för lång tid.", en: "The draft took too long." },
  utkastKundeInte: { sv: "Utkastet kunde inte skrivas.", en: "The draft could not be written." },
  utkastInteKlart: {
    sv: "Utkastet blev inte klart. Försök igen om en stund.",
    en: "The draft was not finished. Try again in a moment."
  },
  ingenKontaktadress: {
    sv: "Iris hittade ingen kontaktadress på bolagets sajt. Försök igen om en stund, eller komplettera bolaget med en adress.",
    en: "Iris found no contact address on the company's site. Try again in a moment, or add an address to the company."
  },
  bolagetHittadesInte: { sv: "Bolaget hittades inte.", en: "Company not found." },
  poang: { sv: "Poäng", en: "Score" },
  bedomning: { sv: "Bedömning", en: "Assessment" },
  kallor: { sv: "Källor", en: "Sources" },
  motivering: { sv: "Motivering", en: "Reasoning" },
  kriterier: { sv: "Kriterier", en: "Criteria" },
  kalla: { sv: "källa", en: "source" },
  researchPagar: {
    sv: "Iris researchar bolaget. Poäng och motivering visas när researchen är klar.",
    en: "Iris is researching the company. Score and reasoning appear when the research is done."
  },
  bedomdesInnan: {
    sv: "Bedömdes innan Iris-profilen fanns. Kör researchen igen för poäng och motivering.",
    en: "Assessed before the Iris profile existed. Run the research again to get a score and reasoning."
  },
  varforBortvald: { sv: "Varför bortvald", en: "Why rejected" },
  ingaKallor: { sv: "Inga källor sparade.", en: "No sources saved." },
  mejlutkast: { sv: "Mejlutkast", en: "Email draft" },
  ingetUtkast: { sv: "Inget utkast ännu.", en: "No draft yet." },
  skapaUtkast: { sv: "Skapa utkast", en: "Create draft" },
  letarKontakt: {
    sv: "Iris letar kontaktadress på bolagets sajt … Det tar ungefär en minut, och utkastet skrivs direkt efteråt.",
    en: "Iris is looking for a contact address on the company's site … It takes about a minute, and the draft is written right after."
  },
  skriverUtkastet: { sv: "Skriver utkastet…", en: "Writing the draft…" },
  exempelutkast: { sv: "Exempelutkast.", en: "Example draft." },
  stodrad: { sv: "Stödrad", en: "Supporting line" },
  godkant: { sv: "Godkänt. Utkastet ligger nu i sändkön.", en: "Approved. The draft is now in the send queue." },
  godkanner: { sv: "Godkänner…", en: "Approving…" },
  godkannOchSkicka: { sv: "Godkänn och skicka", en: "Approve and send" },
  godkannIGranskning: { sv: "Godkänn under Att göra.", en: "Approve under To do." }
} satisfies Record<string, Localized>;

/** Samma text på båda språken: serverns egna felmeddelanden, som redan är färdiga. */
function samma(text: string): Localized {
  return { sv: text, en: text };
}

/**
 * Språket för fetch-hjälparen, som anropas utanför komponenterna och inte kan
 * använda useLocale. LocaleProvider (lib/i18n.tsx) håller `<html lang>` i takt
 * med valet, så attributet är samma källa som hooken läser.
 */
function sprak(): Locale {
  return typeof document !== "undefined" && document.documentElement.lang === "en" ? "en" : "sv";
}

function domanAv(url: string | null | undefined): string | null {
  if (!url) return null;
  try {
    return new URL(url.startsWith("http") ? url : `https://${url}`).hostname.replace(/^www\./, "");
  } catch {
    return url;
  }
}

function segment(p: Prospekt): string {
  return [p.orgnr, p.ort, domanAv(p.website)].filter(Boolean).join(" · ") || "—";
}

function beskrivning(p: Prospekt): string | null {
  if (p.motivering) return p.motivering;
  const träff = kriterier(p.score_breakdown).find((k) => k.motivering && k.utfall !== "saknas");
  return träff?.motivering ?? (p.disqualifiers?.[0] ?? null);
}

/** Researchen är köad eller pågår: raden finns men är inte bedömd än. */
function researchPagar(p: Prospekt): boolean {
  return p.origin !== "example" && !p.niva && p.score_total == null && p.icp_fit == null;
}

function poang(p: Prospekt): string {
  if (typeof p.score_total === "number") return String(p.score_total);
  if (typeof p.icp_fit === "number") return String(Math.round(p.icp_fit * 100));
  return "—";
}

/** Fixturbolaget som ett prospekt-format radlistan redan vet hur den ritar. */
export function exempelTillRad(b: ExempelBolag): ExempelRad {
  return {
    id: b.id,
    company_name: b.companyName,
    contact_name: `${kontaktnamn(b)}, ${b.contactRole}`,
    contact_email: null,
    status: b.status,
    origin: "example",
    ort: b.ort,
    sni: b.bransch,
    website: b.website,
    orgnr: b.orgnr,
    anstallda: b.anstallda,
    score_total: b.score,
    icp_fit: null,
    qualified: true,
    disqualifiers: null,
    motivering: b.beskrivning,
    // Utfallsnyckeln (UTFALL_ETIKETT i lib/prospekt.ts) är data, inte copy: den
    // översätts aldrig, bara etiketten den slås upp till. Escape så att
    // INV-COPY-001 inte läser nyckeln som oöversatt text.
    score_breakdown: [{ etikett: "Signal", utfall: "träff", motivering: b.beskrivning, hart: false }], // inte-copy: fixturnyckel
    _exempel: b
  };
}

export function FelBox({ meddelande, onForsok }: Readonly<{ meddelande: string; onForsok: () => void }>) {
  const { text } = useLocale();
  return (
    <div className="flex items-start gap-3 border-y border-ochre/40 bg-ochre/10 px-4 py-4">
      <div className="min-w-0">
        <p className="text-sm font-medium text-ink">{text(T.bolagenKundeInte)}</p>
        <p className="mt-1 text-sm text-ink-muted">{meddelande}</p>
        <button
          type="button"
          onClick={onForsok}
          className="focus-ring mt-3 inline-flex min-h-9 items-center rounded-input bg-paper2 px-3 text-[13px] font-medium"
        >
          {text(T.forsokIgen)}
        </button>
      </div>
    </div>
  );
}

export function ListorUpsell() {
  const { text } = useLocale();
  const spec = addonSpec("leadlists");
  return (
    <div className="min-w-0 border-t border-ink/15 py-6">
      <div className="flex min-w-0 flex-wrap items-baseline justify-between gap-x-6 gap-y-2">
        <h4 className="min-w-0 break-words text-[17px]">{text(spec.name)}</h4>
        <span className="kicker shrink-0 text-mineral">{text(T.tillval)}</span>
      </div>
      <p className="mt-3 max-w-[64ch] text-[15px] leading-7">{text(spec.what)}</p>
      <a
        href={mejlaOss(text({ sv: `Tillägg: ${spec.name.sv}`, en: `Add-on: ${spec.name.en}` }))}
        className="mt-4 inline-block text-[13px] underline underline-offset-4 transition hover:text-ochre"
      >
        {text({ sv: `Hör av dig om ${spec.name.sv.toLowerCase()}`, en: `Ask us about ${spec.name.en.toLowerCase()}` })}
      </a>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Detaljpanelen — research, källor och mejlutkastet för ETT valt bolag.
// ---------------------------------------------------------------------------

type UtkastLage =
  | { fas: "kontrollerar" }
  | { fas: "ingen" }
  | { fas: "letar-kontakt" }
  | { fas: "skapar" }
  | { fas: "fel"; meddelande: Localized }
  | { fas: "klar"; data: EmailStudioData; queueItemId: string | null };

/**
 * Prospekt utan kontaktmail: "Skapa utkast" slutade förut i ett dött
 * "Mottagaradress saknas." — ett fel kunden inte kan åtgärda själv, för ett
 * bolag Iris själv presenterat (uppmätt 2026-09-21 på ett listbolag utan
 * research). Nu startar knappen i stället kontaktjakten: processa-om kör
 * researchen, som skrapar bolagets egna kontakt-/om-oss-sidor och skriver
 * kontaktfälten (_uppgradera_kontakt i backenden). Vi pollar prospektet tills
 * adressen finns och fortsätter sedan själva in i utkastet.
 */
const KONTAKTJAKT_FORSOK = 24;
const KONTAKTJAKT_PAUS_MS = 5_000;

async function pollaLeadsJobb(jobId: string, locale: Locale): Promise<{
  status?: string;
  error?: string;
  result?: {
    body?: string;
    subject?: string;
    escalated?: boolean;
    escalation_reason?: string | null;
    queue_item_id?: string | null;
  };
}> {
  for (let forsok = 0; forsok < 90; forsok += 1) {
    await new Promise((r) => setTimeout(r, forsok < 5 ? 800 : 2000));
    const jobb = await snajpAnrop<{
      status?: string;
      error?: string;
      result?: {
        body?: string;
        subject?: string;
        escalated?: boolean;
        escalation_reason?: string | null;
        queue_item_id?: string | null;
      };
    }>("/leads/jobb/" + encodeURIComponent(jobId), { method: "GET" });
    if (jobb.status === "completed" || jobb.status === "failed") {
      return jobb;
    }
  }
  return { status: "timeout", error: T.utkastTogForLang[locale] };
}

async function jagaKontakt(prospektId: string): Promise<Prospekt | null> {
  await snajpAnrop("/leads/prospects/processa-om", {
    method: "POST",
    body: JSON.stringify({ prospect_ids: [prospektId], scope: "research" })
  });
  for (let forsok = 0; forsok < KONTAKTJAKT_FORSOK; forsok += 1) {
    await new Promise((r) => setTimeout(r, KONTAKTJAKT_PAUS_MS));
    const kropp = await snajpAnrop<{ prospect?: Prospekt }>(`/leads/prospects/${prospektId}`);
    if (kropp.prospect?.contact_email) return kropp.prospect;
  }
  return null;
}

async function snajpAnrop<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`/api/snajp-support${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init
  });
  const kropp = (await readJsonBody<T & { error?: string; detail?: unknown }>(response)) ?? ({} as T);
  if (!response.ok) {
    const k = kropp as { error?: string; detail?: unknown };
    const detaljtext = Array.isArray(k.detail)
      ? k.detail
          .map((d) => (d && typeof d === "object" && "msg" in d ? String((d as { msg: unknown }).msg) : String(d)))
          .join("; ")
      : typeof k.detail === "string"
        ? k.detail
        : undefined;
    const avvisat: Localized = {
      sv: `Anropet avvisades (${response.status}).`,
      en: `The request was rejected (${response.status}).`
    };
    throw new Error(detaljtext ?? k.error ?? avvisat[sprak()]);
  }
  return kropp;
}

function byggForskningssammanfattning(p: Prospekt): string {
  const rader = kriterier(p.score_breakdown)
    .map((k) => `${k.etikett} (${k.utfall})${k.motivering ? `: ${k.motivering}` : ""}`)
    .join("\n");
  // Agentens underlag, inte copy: alltid svenska, som mejlet det styr.
  const varfor = p.motivering
    ? sv({ sv: `Varför bolaget valdes: ${p.motivering}`, en: `Why the company was picked: ${p.motivering}` })
    : null;
  return [varfor, rader]
    .filter(Boolean)
    .join("\n\n")
    .slice(0, 8000);
}

function exempelStudioData(b: ExempelBolag): EmailStudioData {
  return {
    source: "mock",
    businessContext: null,
    email: {
      id: b.id,
      subject: b.draft.subject,
      body: b.draft.body,
      variantLength: "medium",
      variantType: "cold_outreach",
      status: "draft",
      companyId: b.id,
      contactId: null,
      companyName: b.companyName,
      signal: b.signal,
      offer: b.offer,
      cta: b.cta,
      contactName: kontaktnamn(b)
    }
  };
}

export function LeadDetail({
  id,
  demo,
  exempel
}: Readonly<{ id: string; demo: boolean; exempel?: ExempelBolag }>) {
  const { locale, text } = useLocale();
  const [lage, setLage] = useState<
    | { fas: "laddar" }
    | { fas: "fel"; meddelande: Localized }
    | { fas: "klar"; prospekt: Prospekt; kallor: { label: string; url: string }[] }
  >({ fas: "laddar" });
  const [utkastLage, setUtkastLage] = useState<UtkastLage>({ fas: "kontrollerar" });
  const [forsok, setForsok] = useState(0);
  // Postens vyer (Snajp Suite, Twentys postsida): nyckeltalen ovanför står
  // kvar, resten väljs i flikraden i stället för att staplas i en kolumn.
  const [postFlik, setPostFlik] = useState<"bedomning" | "utkast" | "tidslinje">("bedomning");

  useEffect(() => {
    let avbruten = false;
    async function load() {
      setLage({ fas: "laddar" });
      setUtkastLage({ fas: "kontrollerar" });

      if (exempel) {
        setLage({ fas: "klar", prospekt: exempelTillRad(exempel), kallor: exempel.kallor });
        setUtkastLage({ fas: "klar", data: exempelStudioData(exempel), queueItemId: null });
        return;
      }

      if (demo) {
        const svar = demoOversiktSvar("/leads/prospects") as { prospects?: Prospekt[] } | undefined;
        const träff = svar?.prospects?.find((p) => p.id === id);
        if (avbruten) return;
        if (träff) {
          setLage({ fas: "klar", prospekt: träff, kallor: [] });
          setUtkastLage({ fas: "ingen" });
        } else {
          setLage({ fas: "fel", meddelande: T.bolagetHittadesInte });
        }
        return;
      }

      try {
        const response = await fetch(`/api/snajp-support/leads/prospects/${encodeURIComponent(id)}`, {
          cache: "no-store"
        });
        if (avbruten) return;
        if (!response.ok) {
          setLage({
            fas: "fel",
            meddelande: {
              sv: `Kunde inte hämta bolaget (status ${response.status}).`,
              en: `Could not load the company (status ${response.status}).`
            }
          });
          return;
        }
        const kropp = await readJsonBody<{ prospect?: Prospekt; sources?: string[] }>(response);
        if (!kropp?.prospect) {
          setLage({ fas: "fel", meddelande: T.tomtSvar });
          return;
        }
        // Backenden lämnar bara url:er — etiketten är url:en själv, samma
        // synliga text som förut. Exempelbolagen har en riktig etikett
        // (se lib/demo/iris-exempel.ts), båda formerna delar samma renderare.
        setLage({
          fas: "klar",
          prospekt: kropp.prospect,
          kallor: (kropp.sources ?? []).map((url) => ({ label: url, url }))
        });
        try {
          const utkast = await snajpAnrop<{
            utkast?: { id: string; subject?: string | null; body?: string | null } | null;
            queue_item_id?: string | null;
          }>(`/leads/prospects/${id}/utkast`);
          if (avbruten) return;
          if (utkast.utkast?.body) {
            setUtkastLage({
              fas: "klar",
              data: {
                source: "database",
                businessContext: null,
                email: {
                  id: utkast.utkast.id,
                  subject: utkast.utkast.subject || `Till ${kropp.prospect.company_name}`,
                  body: utkast.utkast.body,
                  variantLength: "medium",
                  variantType: "cold_outreach",
                  status: "draft",
                  companyId: kropp.prospect.id,
                  contactId: null,
                  companyName: kropp.prospect.company_name,
                  signal: beskrivning(kropp.prospect),
                  offer: null,
                  cta: null,
                  contactName: kropp.prospect.contact_name
                }
              },
              queueItemId: utkast.queue_item_id ?? null
            });
          } else {
            setUtkastLage({ fas: "ingen" });
          }
        } catch {
          setUtkastLage({ fas: "ingen" });
        }
      } catch (error) {
        if (!avbruten) setLage({ fas: "fel", meddelande: samma(felmeddelande(error)) });
      }
    }
    void load();
    return () => {
      avbruten = true;
    };
  }, [id, demo, exempel, forsok]);

  const skapaUtkastFor = useCallback(async (p: Prospekt) => {
    setUtkastLage({ fas: "skapar" });
    try {
      const offerSummary = await offertForUtkast();
      const koat = await snajpAnrop<{
        job_id?: string;
        fase?: string;
        escalated?: boolean;
        escalation_reason?: string | null;
        subject?: string;
        body?: string;
        queue_item_id?: string | null;
      }>("/leads/outreach/draft", {
        method: "POST",
        body: JSON.stringify({
          prospect_id: p.id,
          prospect_email: p.contact_email,
          company_name: p.company_name,
          offer_summary: offerSummary,
          // Agentens instruktion, inte copy: alltid svenska, så att mejlet till
          // det svenska bolaget blir svenskt oavsett gränssnittets språk.
          brief: sv({
            sv: `Skriv ett kort, personligt första mejl till kontaktpersonen på ${p.company_name}. Utgå ifrån poängmotiveringen i researchunderlaget och håll dig till det som redan är känt. Ingen hype, inga superlativ, ren text. Utkastet ska köas för granskning, inte skickas.`,
            en: `Write a short, personal first email to the contact person at ${p.company_name}. Start from the score reasoning in the research and stick to what is already known. No hype, no superlatives, plain text. The draft is queued for review, not sent.`
          }),
          research_summary: byggForskningssammanfattning(p)
        })
      });

      // /leads/outreach/draft svarar 202 med ett job_id — LLM-körningen får
      // inte ligga i POST-svaret (proxyns tidsbudget). Utkastet hämtas ur
      // jobbet, precis som tvillingen Bolagssida.tsx gör. Utan pollningen
      // lästes 202-svaret som ett färdigt utkast utan body, och VARJE
      // "Skapa utkast" härifrån slutade i "Utkastet blev inte klart."
      // (uppmätt i development 2026-09-21).
      let svar = koat;
      if (koat.job_id && (koat.fase === "skriver" || !koat.body)) {
        const klart = await pollaLeadsJobb(koat.job_id, locale);
        if (klart.status !== "completed" || !klart.result) {
          throw new Error(klart.error || text(T.utkastKundeInte));
        }
        svar = klart.result;
      }

      if (svar.escalated || !svar.body) {
        setUtkastLage({
          fas: "fel",
          meddelande: svar.escalation_reason ? samma(svar.escalation_reason) : T.utkastInteKlart
        });
        return;
      }
      setUtkastLage({
        fas: "klar",
        data: {
          source: "database",
          businessContext: null,
          email: {
            id: svar.queue_item_id ?? p.id,
            subject: svar.subject || `Till ${p.company_name}`,
            body: svar.body,
            variantLength: "medium",
            variantType: "cold_outreach",
            status: "draft",
            companyId: p.id,
            contactId: null,
            companyName: p.company_name,
            signal: beskrivning(p),
            offer: offerSummary,
            cta: null,
            contactName: p.contact_name
          }
        },
        queueItemId: svar.queue_item_id ?? null
      });
    } catch (error) {
      setUtkastLage({ fas: "fel", meddelande: samma(felmeddelande(error)) });
    }
  }, [locale, text]);

  const skapaUtkast = useCallback(async () => {
    if (lage.fas !== "klar" || demo || exempel) return;
    let p = lage.prospekt;
    if (!p.contact_email) {
      // Ingen återvändsgränd: starta kontaktjakten och fortsätt själv när
      // adressen finns. Se jagaKontakt ovan.
      setUtkastLage({ fas: "letar-kontakt" });
      try {
        const uppdaterad = await jagaKontakt(p.id);
        if (!uppdaterad) {
          setUtkastLage({ fas: "fel", meddelande: T.ingenKontaktadress });
          return;
        }
        p = uppdaterad;
        setLage({ fas: "klar", prospekt: uppdaterad, kallor: lage.kallor });
      } catch (error) {
        setUtkastLage({ fas: "fel", meddelande: samma(felmeddelande(error)) });
        return;
      }
    }
    await skapaUtkastFor(p);
  }, [lage, demo, exempel, skapaUtkastFor]);

  if (lage.fas === "laddar") {
    return <SkeletonRows />;
  }

  if (lage.fas === "fel") {
    return <FelBox meddelande={text(lage.meddelande)} onForsok={() => setForsok((n) => n + 1)} />;
  }

  const { prospekt: p, kallor } = lage;

  return (
    <div className="rounded-card border border-ink/12 bg-paper p-5 md:p-6">
      <div className="flex flex-wrap items-start justify-between gap-x-4 gap-y-2">
        <div className="min-w-0">
          <h2 className="text-[1.125rem] font-semibold tracking-[-0.01em] text-ink">{p.company_name}</h2>
          <p className="mt-1 text-[13px] text-ink-subtle">{segment(p)}</p>
        </div>
        {p.origin === "example" ? <span className="kicker shrink-0 text-mineral">{text(T.exempel)}</span> : null}
      </div>

      <dl className="mt-5 grid grid-cols-3 gap-x-6 gap-y-4 border-t border-ink/12 pt-4">
        <div>
          <dt className="kicker text-mineral">{text(T.poang)}</dt>
          <dd className="num mt-1 text-[1.25rem] font-semibold tabular-nums">
            {researchPagar(p) ? "…" : poang(p)}
          </dd>
        </div>
        <div>
          <dt className="kicker text-mineral">{text(T.bedomning)}</dt>
          <dd className={cn("mt-1 text-[15px]", p.niva === "C" && "text-danger")}>
            {researchPagar(p)
              ? text(T.researchar)
              : p.niva
                ? nivaEtikett(p.niva, locale)
                : statusEtikett(p.status, locale)}
          </dd>
        </div>
        <div>
          <dt className="kicker text-mineral">{text(T.kallor)}</dt>
          <dd className="mt-1 text-[15px]">{kallor.length}</dd>
        </div>
      </dl>

      {/* Tryckknappar, inte role=tab: ingen pilnavigering, och knappen säger
          sitt läge med aria-pressed (4.1.2). */}
      <div className={cn("mt-5", fliklista)} role="group" aria-label={p.company_name}>
        {(
          [
            ["bedomning", T.bedomning],
            ["utkast", T.mejlutkast],
            ["tidslinje", { sv: "Tidslinje", en: "Timeline" }]
          ] as const
        ).map(([id, etikett]) => (
          <button
            key={id}
            type="button"
            aria-pressed={postFlik === id}
            onClick={() => setPostFlik(id)}
            className={cn(flik, postFlik === id ? flikAktiv : flikInaktiv)}
          >
            {text(etikett)}
          </button>
        ))}
      </div>

      {postFlik === "bedomning" ? (
      <div className="mt-5">
        {p.motivering ? (
          <>
            <h3 className="kicker text-mineral">{text(T.motivering)}</h3>
            <p className="mt-2 max-w-[65ch] text-[15px] leading-7 text-ink">{p.motivering}</p>
          </>
        ) : null}
        <h3 className={cn("kicker text-mineral", p.motivering && "mt-5")}>{text(T.kriterier)}</h3>
        {kriterier(p.score_breakdown).length ? (
          <ul className="mt-3 divide-y divide-ink/10">
            {kriterier(p.score_breakdown).map((k, i) => (
              <li key={`${k.nyckel ?? k.etikett}-${i}`} className="py-3">
                <div className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
                  <p className="text-[14px] font-medium">{k.etikett}</p>
                  <span className={cn("kicker", k.hart && k.utfall === "miss" ? "text-danger" : "text-mineral")}>
                    {UTFALL_ETIKETT[k.utfall] ?? k.utfall}
                  </span>
                </div>
                {k.motivering ? (
                  <p className="mt-1 max-w-[65ch] text-[14px] leading-6 text-ink-muted">{k.motivering}</p>
                ) : null}
                {k.belagg?.length ? (
                  <ul className="mt-2 space-y-1">
                    {k.belagg.map((b) => (
                      <li key={b.citat} className="border-l-2 border-ink/15 pl-3 text-[13px] leading-5 text-ink-subtle">
                        ”{b.citat}”
                        {b.url.startsWith("http") ? (
                          <>
                            {" "}
                            <a
                              href={b.url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="focus-ring underline decoration-ink/25 underline-offset-4"
                            >
                              {text(T.kalla)}
                            </a>
                          </>
                        ) : null}
                      </li>
                    ))}
                  </ul>
                ) : null}
              </li>
            ))}
          </ul>
        ) : (
          <p className="mt-3 text-[14px] text-ink-subtle">
            {researchPagar(p)
              ? text(T.researchPagar)
              : text(T.bedomdesInnan)}
          </p>
        )}

        {p.niva === "C" && p.disqualifiers?.length ? (
          <div className="mt-4">
            <h4 className="kicker text-mineral">{text(T.varforBortvald)}</h4>
            <ul className="mt-2 space-y-1.5">
              {p.disqualifiers.map((skal) => (
                <li key={skal} className="border-l-2 border-danger pl-3 text-[14px] text-ink-muted">
                  {skal}
                </li>
              ))}
            </ul>
          </div>
        ) : null}

        {p.jev?.triage || p.jev?.klassning ? <JevRad jev={p.jev} /> : null}

        <h4 className="mt-5 kicker text-mineral">{text(T.kallor)}</h4>
        {kallor.length ? (
          <ul className="mt-2 space-y-1.5">
            {kallor.map((kalla) => (
              <li key={kalla.url}>
                <a
                  href={kalla.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="focus-ring break-all text-[13px] text-ink-muted underline decoration-ink/25 underline-offset-4"
                >
                  {kalla.label}
                </a>
              </li>
            ))}
          </ul>
        ) : (
          <p className="mt-2 text-[14px] text-ink-subtle">{text(T.ingaKallor)}</p>
        )}
      </div>
      ) : null}

      {postFlik === "utkast" ? (
      <div className="mt-5">

        {utkastLage.fas === "kontrollerar" ? (
          <div className="mt-3 h-16 animate-pulse rounded-input bg-ink/[0.03]" />
        ) : null}

        {utkastLage.fas === "ingen" ? (
          demo ? (
            <p className="mt-3 text-[14px] leading-6 text-ink-muted">{text(T.ingetUtkast)}</p>
          ) : (
            <div className="mt-3">
              <p className="text-[14px] leading-6 text-ink-muted">{text(T.ingetUtkast)}</p>
              <button type="button" onClick={() => void skapaUtkast()} className={cn(btnPrimary, "mt-4")}>
                {text(T.skapaUtkast)}
              </button>
            </div>
          )
        ) : null}

        {utkastLage.fas === "letar-kontakt" ? (
          <p className="mt-3 text-[14px] leading-6 text-ink-subtle">
            {text(T.letarKontakt)}
          </p>
        ) : null}

        {utkastLage.fas === "skapar" ? <p className="mt-3 text-[14px] text-ink-subtle">{text(T.skriverUtkastet)}</p> : null}

        {utkastLage.fas === "fel" ? (
          <div className="mt-3">
            <p role="alert" className="text-[14px] text-danger">
              {text(utkastLage.meddelande)}
            </p>
            <button
              type="button"
              onClick={() => void skapaUtkast()}
              className={cn(btnSecondary, "mt-3")}
            >
              {text(T.forsokIgen)}
            </button>
          </div>
        ) : null}

        {utkastLage.fas === "klar" ? (
          <div className="mt-4">
            <EmailStudioEditor data={utkastLage.data} compact />
            {!demo && !exempel ? (
              <GodkannKnapp queueItemId={utkastLage.queueItemId} />
            ) : (
              <p className="mt-4 text-[13px] leading-6 text-ink-subtle">{text(T.exempelutkast)}</p>
            )}
          </div>
        ) : null}
      </div>
      ) : null}

      {postFlik === "tidslinje" ? (
        <div className="mt-5">
          <Tidslinje prospectId={id} demo={demo || Boolean(exempel)} />
        </div>
      ) : null}
    </div>
  );
}

/** Jevs förbedömning och klassning (app/leads/jev.py) — visas för att
 * kunden och vi ska kunna jämföra den med kodens bedömning. */
function JevRad({ jev }: Readonly<{ jev: JevData }>) {
  const { text } = useLocale();
  const t = jev.triage;
  const k = jev.klassning;
  const delar = [
    t && typeof t.fit === "number"
      ? text({ sv: `förbedömning ${t.fit.toFixed(1)} av 3`, en: `pre-assessment ${t.fit.toFixed(1)} of 3` })
      : null,
    t?.skulle_falla
      ? text({
          sv: `hade valt bort (${(t.fall_skal ?? []).join("; ")})`,
          en: `would have rejected (${(t.fall_skal ?? []).join("; ")})`
        })
      : null,
    k && typeof k.sannolikhet === "number"
      ? text({ sv: `bra lead ${Math.round(k.sannolikhet * 100)} %`, en: `good lead ${Math.round(k.sannolikhet * 100)} %` })
      : null,
    k?.trafikniva ? text({ sv: `prioritet ${k.trafikniva}`, en: `priority ${k.trafikniva}` }) : null
  ].filter(Boolean);
  if (!delar.length) return null;
  return (
    <div className="mt-5">
      <h4 className="kicker text-mineral">Jev</h4>
      <p className="mt-2 max-w-[65ch] text-[13px] leading-6 text-ink-subtle">
        {delar.join(" · ")}
        {t?.stodrad ? <span className="block">{text(T.stodrad)}: ”{t.stodrad}”</span> : null}
      </p>
    </div>
  );
}

function GodkannKnapp({ queueItemId }: Readonly<{ queueItemId: string | null }>) {
  const { text } = useLocale();
  const [godkant, setGodkant] = useState(false);
  const [busy, setBusy] = useState(false);
  const [fel, setFel] = useState<string | null>(null);

  async function godkann() {
    if (!queueItemId) return;
    setBusy(true);
    setFel(null);
    try {
      await snajpAnrop(`/leads/queue/${encodeURIComponent(queueItemId)}/approve`, { method: "POST" });
      setGodkant(true);
    } catch (error) {
      setFel(felmeddelande(error));
    } finally {
      setBusy(false);
    }
  }

  if (godkant) {
    return (
      <p role="status" className="mt-4 text-[15px] text-moss">
        {text(T.godkant)}
      </p>
    );
  }

  return (
    <div className="mt-4">
      <button
        type="button"
        disabled={busy || !queueItemId}
        onClick={() => void godkann()}
        className={cn(btnPrimary, "disabled:cursor-wait disabled:opacity-60")}
      >
        {busy ? text(T.godkanner) : text(T.godkannOchSkicka)}
      </button>
      {!queueItemId ? (
        <p className="mt-3 text-[13px] leading-6 text-ink-subtle">{text(T.godkannIGranskning)}</p>
      ) : null}
      {fel ? (
        <p role="alert" className="mt-3 max-w-[65ch] text-[14px] text-danger">
          {fel}
        </p>
      ) : null}
    </div>
  );
}
