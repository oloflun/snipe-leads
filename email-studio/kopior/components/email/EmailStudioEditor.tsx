"use client";

import { useState, useTransition } from "react";
import type { EmailStudioAction } from "@/lib/agent/email-studio-prompt";
import type { EmailStudioData } from "@/lib/data/emails";
import { useLocale } from "@/lib/i18n";
import { cn } from "@/lib/utils";

type StudioActionDef = {
  action: EmailStudioAction;
  label: string;
};

const STUDIO_ACTIONS: StudioActionDef[] = [
  { action: "shorter", label: "Kortare" },
  { action: "rewrite", label: "Skriv om" },
  { action: "improve", label: "Förbättra" },
  { action: "personalize", label: "Personalisera" },
  { action: "translate", label: "Översätt" },
  { action: "ab_variants", label: "A/B-varianter" },
  { action: "followup", label: "Uppföljning" },
  { action: "analyze", label: "Analysera" }
];

type RichResult = {
  original_version?: string | null;
  new_version: string;
  explanation: string;
  subject_suggestions: string[];
  confidence_tips?: string;
  action?: string;
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

export function EmailStudioEditor({ data, compact = false }: Readonly<{ data: EmailStudioData; compact?: boolean }>) {
  const { locale, t } = useLocale();
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
        const res = await fetch('/api/email-studio', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            action,
            draft: body,
            subject,
            context: refineContext,
            userId: 'current-user', // could be dynamic
          }),
        });
        const apiRes = await res.json();

        if (!res.ok || !apiRes.success || !apiRes.data) {
          setError(apiRes.error || 'Kunde inte utföra åtgärden');
          setActiveAction(null);
          return;
        }

        const d = apiRes.data;
        const rich: RichResult = {
          original_version: d.original_version ?? null,
          new_version: d.new_version || d.body || body,
          explanation: d.explanation || "",
          subject_suggestions: d.subject_suggestions || (d.subject ? [d.subject] : []),
          confidence_tips: d.confidence_tips,
          action
        };

        setLastResult(rich);

        // For analyze/ab/followup we keep original editor state; user decides to apply
        // For direct rewrite actions, auto-apply the new body (and a suggested subject if present)
        const directApply = ["shorter", "rewrite", "improve", "personalize", "translate"].includes(action);
        if (directApply) {
          if (rich.subject_suggestions[0]) setSubject(rich.subject_suggestions[0]);
          setBody(rich.new_version);
        }

        setActiveAction(null);
      } catch (e: any) {
        setError(e.message || 'Nätverksfel');
        setActiveAction(null);
      }
    });
  }

  function applyResult() {
    if (!lastResult) return;
    if (lastResult.subject_suggestions[0]) setSubject(lastResult.subject_suggestions[0]);
    setBody(lastResult.new_version);
    // keep the result visible for review
  }

  function dismissResult() {
    setLastResult(null);
  }

  const inputRows = [
    ["Företag", data.email.companyName],
    ["Signal", data.email.signal],
    ["Erbjudande", data.email.offer ?? data.businessContext?.offer],
    ["CTA", data.email.cta ?? data.businessContext?.cta]
  ].filter(([, value]) => Boolean(value)) as [string, string][];

  return (
    <div className={cn("grid grid-cols-12 gap-x-8 gap-y-10", compact ? "" : "")}>
      {!compact && inputRows.length > 0 ? (
        <aside className="col-span-12 md:col-span-4">
          <h2 className="kicker text-mineral">Inputs</h2>
          <div className="mt-5 divide-y divide-ink/15 border-y border-ink/15">
            {inputRows.map(([label, value]) => (
              <div key={label} className="py-4">
                <p className="kicker text-mineral">{label}</p>
                <p className="mt-2 text-[15px] leading-6 text-ink/72">{value}</p>
              </div>
            ))}
          </div>
        </aside>
      ) : null}

      <section className={cn("col-span-12", compact ? "" : inputRows.length > 0 ? "md:col-span-8" : "")}>
        <div className="border-y border-ink/15 py-5">
          <p className="kicker text-ochre">
            {data.email.variantLength} · {data.email.variantType}
            {data.source === "mock" ? " · demo" : ""}
          </p>
          <input
            value={subject}
            onChange={(event) => setSubject(event.target.value)}
            className="mt-4 w-full bg-transparent font-display text-4xl italic-disp tighten outline-none"
            aria-label="Ämnesrad"
          />
        </div>

        <textarea
          value={body}
          onChange={(event) => setBody(event.target.value)}
          className="mt-6 min-h-[420px] w-full resize-y border border-ink/15 bg-paper2/70 p-6 text-[16px] leading-8 text-ink outline-none transition focus:border-ochre"
          aria-label="Mejltext"
        />

        {error ? <p className="mt-4 text-sm text-ochre">{error}</p> : null}
        {isPending ? <p className="mt-4 font-mono text-xs uppercase tracking-[0.16em] text-mineral">Email Studio använder marketingskills…</p> : null}

        {/* Rich result panel per Snipra Prompt spec */}
        {lastResult && !isPending && (
          <div className="mt-6 border border-ochre/40 bg-paper2/60 p-5 text-[15px]">
            <div className="flex items-center justify-between">
              <p className="kicker text-ochre uppercase tracking-[0.16em]">Email Studio resultat — {lastResult.action}</p>
              <div className="flex gap-2">
                <button onClick={applyResult} className="border border-ink/15 px-3 py-1 text-xs uppercase tracking-widest hover:border-ochre">Använd ny version</button>
                <button onClick={dismissResult} className="border border-ink/15 px-3 py-1 text-xs uppercase tracking-widest hover:border-ochre">Stäng</button>
              </div>
            </div>

            {lastResult.original_version && (
              <>
                <p className="mt-4 text-xs uppercase tracking-[0.16em] text-mineral">Ursprunglig version</p>
                <pre className="mt-1 whitespace-pre-wrap text-ink/80 text-sm border-l-2 pl-3 border-ink/20">{lastResult.original_version}</pre>
              </>
            )}

            <p className="mt-4 text-xs uppercase tracking-[0.16em] text-mineral">Ny version</p>
            <pre className="mt-1 whitespace-pre-wrap text-ink text-sm border-l-2 pl-3 border-ochre/60">{lastResult.new_version}</pre>

            {lastResult.explanation && (
              <>
                <p className="mt-4 text-xs uppercase tracking-[0.16em] text-mineral">Förklaring av förändringarna</p>
                <p className="mt-1 text-ink/80">{lastResult.explanation}</p>
              </>
            )}

            {lastResult.subject_suggestions?.length > 0 && (
              <>
                <p className="mt-4 text-xs uppercase tracking-[0.16em] text-mineral">Förslag på ämnesrad</p>
                <ul className="mt-1 list-disc pl-5 text-ink/80">
                  {lastResult.subject_suggestions.map((s, i) => <li key={i}>{s}</li>)}
                </ul>
              </>
            )}

            {lastResult.confidence_tips && (
              <>
                <p className="mt-4 text-xs uppercase tracking-[0.16em] text-mineral">Konfidens / Tips</p>
                <p className="mt-1 text-ink/80">{lastResult.confidence_tips}</p>
              </>
            )}
          </div>
        )}

        <div className="mt-5 flex flex-wrap gap-3">
          {STUDIO_ACTIONS.map((item) => {
            const isActive = activeAction === item.action && isPending;
            return (
              <button
                key={item.action}
                type="button"
                disabled={isPending}
                onClick={() => runAction(item.action)}
                className={cn(
                  "border border-ink/15 px-4 py-3 font-mono text-xs uppercase tracking-[0.16em] transition hover:border-ochre hover:text-ochre active:translate-y-px disabled:cursor-wait disabled:opacity-60",
                  isActive && "border-ochre text-ochre"
                )}
              >
                {item.label}
              </button>
            );
          })}
        </div>

        <p className="mt-3 text-[11px] uppercase tracking-[0.2em] text-mineral">
          Alla åtgärder använder marketingskills (cold-email, copywriting, ab-testing, emails, marketing-psychology m.fl.)
        </p>
      </section>
    </div>
  );
}