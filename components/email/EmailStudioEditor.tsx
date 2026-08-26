"use client";

import { useState, useTransition } from "react";
import type { EmailStudioAction } from "@/lib/agent/email-studio-prompt";
import type { EmailStudioData } from "@/lib/data/emails";
import { btnPrimary } from "@/components/ui";
import { felmeddelande, readJson } from "@/lib/http/json";
import { useLocale } from "@/lib/i18n";
import type { Localized } from "@/lib/i18n";
import { cn } from "@/lib/utils";

type StudioActionDef = {
  action: EmailStudioAction;
  label: Localized;
};

const STUDIO_ACTIONS: StudioActionDef[] = [
  { action: "shorter", label: { sv: "Kortare", en: "Shorter" } },
  { action: "rewrite", label: { sv: "Skriv om", en: "Rewrite" } },
  { action: "improve", label: { sv: "Förbättra", en: "Improve" } },
  { action: "personalize", label: { sv: "Personalisera", en: "Personalise" } },
  { action: "translate", label: { sv: "Översätt", en: "Translate" } },
  { action: "ab_variants", label: { sv: "A/B-varianter", en: "A/B variants" } },
  { action: "followup", label: { sv: "Uppföljning", en: "Follow-up" } },
  { action: "analyze", label: { sv: "Analysera", en: "Analyse" } }
];

const ui = {
  subjectLabel: { sv: "Ämnesrad", en: "Subject line" },
  bodyLabel: { sv: "Mejltext", en: "Email body" },
  working: { sv: "Skriver om", en: "Rewriting" },
  original: { sv: "Ursprunglig version", en: "Original version" },
  updated: { sv: "Ny version", en: "New version" },
  explanation: { sv: "Vad som ändrades", en: "What changed" },
  subjects: { sv: "Förslag på ämnesrad", en: "Subject line suggestions" },
  tips: { sv: "Konfidens och tips", en: "Confidence and tips" },
  apply: { sv: "Använd ny version", en: "Use new version" },
  dismiss: { sv: "Stäng", en: "Close" },
  failed: { sv: "Åtgärden gick inte att köra", en: "That action could not run" },
  network: { sv: "Nätverksfel", en: "Network error" },
  company: { sv: "Företag", en: "Company" },
  signal: { sv: "Signal", en: "Signal" },
  offer: { sv: "Erbjudande", en: "Offer" },
  cta: { sv: "CTA", en: "CTA" },
  exempel: {
    sv: "Exempelmejl. Ni har inga utkast ännu — starta en körning under Leads, så ligger era egna här.",
    en: "Example email. You have no drafts yet — start a run under Leads and your own will appear here."
  }
} satisfies Record<string, Localized>;

type RichResult = {
  original_version?: string | null;
  new_version: string;
  simulated?: boolean;
  simulated_reason?: string;
  explanation: string;
  subject_suggestions: string[];
  confidence_tips?: string;
  action?: string;
};

/**
 * Så som API:t faktiskt svarar — lösare än RichResult, eftersom modellen inte
 * alltid fyller varje fält. Fälten vägs ihop till en RichResult nedan.
 */
type RichApiPayload = {
  original_version?: string | null;
  new_version?: string;
  /** Sant när svaret INTE kom från en modell — se app/api/email-studio/route.ts. */
  simulated?: boolean;
  simulated_reason?: string;
  body?: string;
  explanation?: string;
  subject?: string;
  subject_suggestions?: string[];
  confidence_tips?: string;
};

function toRefineContext(data: EmailStudioData) {
  return {
    companyName: data.email.companyName ?? undefined,
    signal: data.email.signal ?? undefined,
    offer: data.email.offer ?? data.businessContext?.offer ?? undefined,
    cta: data.email.cta ?? data.businessContext?.cta ?? undefined,
    contactName: data.email.contactName ?? undefined
  };
}

export function EmailStudioEditor({
  data,
  compact = false
}: Readonly<{ data: EmailStudioData; compact?: boolean }>) {
  const { text } = useLocale();
  const [subject, setSubject] = useState(data.email.subject);
  const [body, setBody] = useState(data.email.body);
  const [error, setError] = useState<string | null>(null);
  const [activeAction, setActiveAction] = useState<EmailStudioAction | null>(null);
  const [isPending, startTransition] = useTransition();
  const [lastResult, setLastResult] = useState<RichResult | null>(null);

  const refineContext = toRefineContext(data);

  function runAction(action: EmailStudioAction) {
    setError(null);
    setActiveAction(action);
    setLastResult(null);

    startTransition(async () => {
      try {
        const res = await fetch("/api/email-studio", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            action,
            draft: body,
            subject,
            context: refineContext,
            userId: "current-user"
          })
        });
        // readJson kastar med ett läsbart meddelande vid tom kropp, icke-JSON
        // eller felstatus — catch nedan visar det. Ett rått
        // "Unexpected end of JSON input" når aldrig kunden.
        const apiRes = await readJson<{ success?: boolean; data?: RichApiPayload; error?: string }>(
          res
        );

        if (!apiRes?.success || !apiRes.data) {
          setError(apiRes?.error || text(ui.failed));
          setActiveAction(null);
          return;
        }

        const d = apiRes.data;
        const rich: RichResult = {
          original_version: d.original_version ?? null,
          new_version: d.new_version || d.body || body,
          simulated: d.simulated === true,
          simulated_reason: d.simulated_reason,
          explanation: d.explanation || "",
          subject_suggestions: d.subject_suggestions || (d.subject ? [d.subject] : []),
          confidence_tips: d.confidence_tips,
          action
        };

        setLastResult(rich);

        // Direct rewrites apply straight away; analyse/AB/follow-up keep the editor
        // untouched so the user decides.
        const directApply = ["shorter", "rewrite", "improve", "personalize", "translate"].includes(action);
        if (directApply) {
          if (rich.subject_suggestions[0]) setSubject(rich.subject_suggestions[0]);
          setBody(rich.new_version);
        }

        setActiveAction(null);
      } catch (e) {
        setError(felmeddelande(e, text(ui.network)));
        setActiveAction(null);
      }
    });
  }

  function applyResult() {
    if (!lastResult) return;
    if (lastResult.subject_suggestions[0]) setSubject(lastResult.subject_suggestions[0]);
    setBody(lastResult.new_version);
  }

  const inputRows = [
    [text(ui.company), data.email.companyName],
    [text(ui.signal), data.email.signal],
    [text(ui.offer), data.email.offer ?? data.businessContext?.offer],
    [text(ui.cta), data.email.cta ?? data.businessContext?.cta]
  ].filter(([, value]) => Boolean(value)) as [string, string][];

  const activeLabel = STUDIO_ACTIONS.find((item) => item.action === activeAction)?.label;

  return (
    <div className={cn("grid gap-6", !compact && inputRows.length > 0 ? "lg:grid-cols-12" : "")}>
      {!compact && inputRows.length > 0 ? (
        <aside className="lg:col-span-4">
          <dl className="space-y-5">
            {inputRows.map(([label, value]) => (
              <div key={label}>
                <dt className="text-[0.8125rem] font-medium text-ink/45">{label}</dt>
                <dd className="mt-1 text-[0.9375rem] leading-6 text-ink/80">{value}</dd>
              </div>
            ))}
          </dl>
        </aside>
      ) : null}

      <section className={cn(!compact && inputRows.length > 0 ? "lg:col-span-8" : "")}>
        {/* Bara i arbetsytan (`compact` är marknadssidan, som redan säger i
            sin egen text att mejlet är ett exempel).

            Utan raden fick en ny kund ett färdigskrivet säljmejl till ett bolag
            de aldrig hört talas om, omärkt, i sin egen Email Studio — och
            ingenting sa att agenterna inte redan hade skrivit det åt dem. */}
        {!compact && data.source === "mock" ? (
          <p className="mb-5 rounded-input bg-paper2/70 px-4 py-3 text-[0.875rem] leading-6 text-ink/65">
            {text(ui.exempel)}
          </p>
        ) : null}

        <label htmlFor="studio-subject" className="block text-[0.8125rem] font-medium text-ink/45">
          {text(ui.subjectLabel)}
        </label>
        <input
          id="studio-subject"
          maxLength={200}
          value={subject}
          onChange={(event) => setSubject(event.target.value)}
          className="focus-ring mt-2 w-full rounded-input border border-ink/12 bg-paper px-4 py-3 text-[1.25rem] font-semibold tracking-[-0.01em] outline-none transition-colors focus:border-ink/30"
        />

        <label htmlFor="studio-body" className="mt-6 block text-[0.8125rem] font-medium text-ink/45">
          {text(ui.bodyLabel)}
        </label>
        <textarea
          id="studio-body"
          maxLength={8000}
          value={body}
          onChange={(event) => setBody(event.target.value)}
          className={cn(
            "focus-ring mt-2 w-full resize-y rounded-card border border-ink/12 bg-paper p-5 text-[1rem] leading-7 text-ink outline-none transition-colors focus:border-ink/30",
            compact ? "min-h-[210px]" : "min-h-[320px]"
          )}
        />

        <div className="hrule mt-6 flex flex-wrap gap-2 pt-5">
          {STUDIO_ACTIONS.map((item) => {
            const isActive = activeAction === item.action && isPending;
            return (
              <button
                key={item.action}
                type="button"
                disabled={isPending}
                onClick={() => runAction(item.action)}
                className={cn(
                  // States are mutually exclusive rather than layered: `cn` is a plain
                  // join with no tailwind-merge, so a base `bg-paper text-ink` plus an
                  // appended `bg-ink text-paper` left BOTH in the class list, and the
                  // cascade picked paper for both. The running button rendered paper
                  // text on paper ground, i.e. invisible.
                  "focus-ring inline-flex min-h-11 items-center rounded-input px-4 text-[0.875rem] font-medium transition-colors active:translate-y-px disabled:cursor-wait disabled:opacity-50",
                  isActive ? "bg-ink text-paper" : "bg-paper text-ink hover:bg-ink hover:text-paper"
                )}
              >
                {text(item.label)}
              </button>
            );
          })}
        </div>

        <div aria-live="polite" className="mt-4">
          {isPending && activeLabel ? (
            <p className="text-[0.875rem] text-ink/50">
              {text(ui.working)}
              <span className="ml-1 inline-flex">
                <span className="animate-pulse">.</span>
                <span className="animate-pulse [animation-delay:150ms]">.</span>
                <span className="animate-pulse [animation-delay:300ms]">.</span>
              </span>
            </p>
          ) : null}

          {error ? (
            <p className="rounded-input bg-danger/10 px-4 py-3 text-[0.875rem] text-danger">{error}</p>
          ) : null}
        </div>

        {lastResult && !isPending ? (
          <div className="reveal mt-5 rounded-card bg-paper p-5">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <p className="text-[0.8125rem] font-semibold text-ochre">{text(ui.updated)}</p>
              <div className="flex flex-wrap gap-2">
                <button
                  type="button"
                  onClick={applyResult}
                  className={btnPrimary}
                >
                  {text(ui.apply)}
                </button>
                <button
                  type="button"
                  onClick={() => setLastResult(null)}
                  className="focus-ring inline-flex min-h-11 items-center rounded-input px-4 text-[0.875rem] font-medium text-ink/60 transition-colors hover:text-ink"
                >
                  {text(ui.dismiss)}
                </button>
              </div>
            </div>

            {lastResult.original_version ? (
              <>
                <p className="mt-5 text-[0.8125rem] font-medium text-ink/45">{text(ui.original)}</p>
                <p className="mt-1 whitespace-pre-wrap text-[0.9375rem] leading-7 text-ink/55">
                  {lastResult.original_version}
                </p>
              </>
            ) : null}

            {/* Ett simulerat svar ska aldrig gå att förväxla med ett
                modellskrivet. Utan raden fick kunden mallgenererad text
                presenterad som agentens arbete — samma fel som analysvyn och
                bolagslistan hade, fast i den flik man faktiskt skriver i. */}
            {lastResult.simulated ? (
              <p className="mt-5 rounded-input border border-ochre/40 bg-ochre/10 px-4 py-3 text-[0.875rem] leading-6 text-ink/75">
                <strong className="font-semibold">Exempelsvar.</strong>{" "}
                {lastResult.simulated_reason === "anonym"
                  ? "Du är inte inloggad, så åtgärden kördes inte mot någon modell."
                  : lastResult.simulated_reason === "tillfälligt fel"
                    ? "Modellen svarade inte just nu, så du fick ett förskrivet förslag under tiden. Prova åtgärden igen om en liten stund."
                    : "Ingen modellnyckel är kopplad i den här miljön, så åtgärden kördes inte mot någon modell."}
              </p>
            ) : null}

            <p className="mt-5 text-[0.8125rem] font-medium text-ink/45">{text(ui.updated)}</p>
            <p className="mt-1 whitespace-pre-wrap text-[0.9375rem] leading-7 text-ink">
              {lastResult.new_version}
            </p>

            {lastResult.explanation ? (
              <>
                <p className="mt-5 text-[0.8125rem] font-medium text-ink/45">{text(ui.explanation)}</p>
                <p className="mt-1 text-[0.9375rem] leading-7 text-ink/80">{lastResult.explanation}</p>
              </>
            ) : null}

            {lastResult.subject_suggestions?.length > 0 ? (
              <>
                <p className="mt-5 text-[0.8125rem] font-medium text-ink/45">{text(ui.subjects)}</p>
                <ul className="mt-1 space-y-1 text-[0.9375rem] leading-7 text-ink/80">
                  {lastResult.subject_suggestions.map((suggestion) => (
                    <li key={suggestion}>{suggestion}</li>
                  ))}
                </ul>
              </>
            ) : null}

            {lastResult.confidence_tips ? (
              <>
                <p className="mt-5 text-[0.8125rem] font-medium text-ink/45">{text(ui.tips)}</p>
                <p className="mt-1 text-[0.9375rem] leading-7 text-ink/80">{lastResult.confidence_tips}</p>
              </>
            ) : null}
          </div>
        ) : null}
      </section>
    </div>
  );
}
