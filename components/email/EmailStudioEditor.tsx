"use client";

import { useState, useTransition } from "react";
import { refineEmail } from "@/lib/actions/emails";
import type { EmailRefineAction } from "@/lib/agent/email-studio-prompt";
import type { EmailStudioData } from "@/lib/data/emails";
import { useLocale } from "@/lib/i18n";
import { cn } from "@/lib/utils";

type StudioAction = {
  action: EmailRefineAction;
  labelSv: string;
  labelKey?: "action.shorter" | "action.rewrite" | "action.human" | "action.professional" | "action.persuasive";
};

const STUDIO_ACTIONS: StudioAction[] = [
  { action: "shorter", labelSv: "Kortare", labelKey: "action.shorter" },
  { action: "more_personal", labelSv: "Mer personlig" },
  { action: "clearer_cta", labelSv: "Tydligare CTA" },
  { action: "rewrite", labelSv: "Skriv om", labelKey: "action.rewrite" }
];

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
  const [activeAction, setActiveAction] = useState<EmailRefineAction | null>(null);
  const [isPending, startTransition] = useTransition();

  const refineContext = toRefineContext(data);

  function runAction(action: EmailRefineAction) {
    setError(null);
    setActiveAction(action);

    startTransition(async () => {
      const result = await refineEmail({
        emailId: data.email.id,
        subject,
        body,
        action,
        locale,
        context: refineContext
      });

      if (!result.success || !result.data) {
        setError(result.error ?? "Kunde inte omskriva mejlet");
        setActiveAction(null);
        return;
      }

      setSubject(result.data.subject);
      setBody(result.data.body);
      setActiveAction(null);
    });
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
        {isPending ? <p className="mt-4 font-mono text-xs uppercase tracking-[0.16em] text-mineral">Agenten omskriver med marketing skills…</p> : null}

        <div className="mt-5 flex flex-wrap gap-3">
          {STUDIO_ACTIONS.map((item) => {
            const label = item.labelKey ? t(item.labelKey) : item.labelSv;
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
                {label}
              </button>
            );
          })}
        </div>
      </section>
    </div>
  );
}