"use client";

import { ChevronDown } from "lucide-react";
import { useState } from "react";
import { Badge, SkeletonRows, Tomt, meta } from "@/components/ui";
import { useLocale } from "@/lib/i18n";
import { relativTid } from "@/lib/leads/suite";
import { cn } from "@/lib/utils";

/**
 * Iris-leads › Skickat (Sebbe 2026-10-07): varje leadsmejl som gått ut, med
 * bolaget, mottagaren och hela texten så som den skickades (signatur och
 * lagstadgad fot ingår). Backend: GET /api/leads/skickat.
 */

export type SkickatRad = {
  id: string;
  subject: string | null;
  body: string;
  sent_at: string;
  prospect_id: string | null;
  company_name: string | null;
  contact_name: string | null;
  prospect_email: string | null;
  svarat: boolean;
};

export function SkickatLista({
  rader,
  fel,
  onValj
}: Readonly<{ rader: SkickatRad[] | null; fel: string | null; onValj?: (prospektId: string) => void }>) {
  const { locale, text } = useLocale();
  const [oppen, setOppen] = useState<string | null>(null);

  if (fel) {
    return (
      <p role="alert" className="text-[14px] text-danger">
        {fel}
      </p>
    );
  }
  if (rader === null) return <SkeletonRows />;
  if (rader.length === 0) {
    return <Tomt>{text({ sv: "Inga mejl skickade än.", en: "No emails sent yet." })}</Tomt>;
  }

  return (
    <ul className="divide-y divide-ink/12 border-y border-ink/15" aria-label={text({ sv: "Skickade mejl", en: "Sent emails" })}>
      {rader.map((r) => {
        const oppnad = oppen === r.id;
        const nar = new Date(r.sent_at);
        return (
          <li key={r.id} className="py-3">
            <button
              type="button"
              aria-expanded={oppnad}
              onClick={() => setOppen(oppnad ? null : r.id)}
              className="focus-ring block w-full rounded-input text-left"
            >
              <div className="flex items-start justify-between gap-4">
                <div className="min-w-0">
                  <p className="truncate text-[0.9375rem] font-semibold text-ink">
                    {r.company_name ?? text({ sv: "Okänt bolag", en: "Unknown company" })}
                  </p>
                  <p className="mt-0.5 truncate text-[0.875rem] text-ink-muted">
                    {r.subject || text({ sv: "Utan ämnesrad", en: "No subject line" })}
                  </p>
                  <p className={cn(meta, "mt-0.5 truncate")}>
                    {[r.prospect_email, relativTid(r.sent_at, locale)].filter(Boolean).join(" · ")}
                  </p>
                </div>
                <span className="flex shrink-0 items-center gap-2">
                  {r.svarat ? <Badge tone="good">{text({ sv: "Svarat", en: "Replied" })}</Badge> : null}
                  <ChevronDown
                    aria-hidden
                    className={cn("h-4 w-4 text-ink-muted transition-transform", oppnad && "rotate-180")}
                  />
                </span>
              </div>
            </button>
            {oppnad ? (
              <div className="mt-3 rounded-card border border-ink/12 bg-paper px-4 py-4 sm:px-5">
                <dl className="grid gap-1 text-[0.8125rem] sm:grid-cols-[auto_1fr] sm:gap-x-4">
                  <dt className="text-ink-subtle">{text({ sv: "Till", en: "To" })}</dt>
                  <dd className="break-all text-ink">{r.prospect_email ?? "–"}</dd>
                  <dt className="text-ink-subtle">{text({ sv: "Skickat", en: "Sent" })}</dt>
                  <dd className="num tabular-nums text-ink">
                    {nar.toLocaleString(locale === "sv" ? "sv-SE" : "en-GB", {
                      dateStyle: "medium",
                      timeStyle: "short",
                      timeZone: "Europe/Stockholm"
                    })}
                  </dd>
                  <dt className="text-ink-subtle">{text({ sv: "Ämne", en: "Subject" })}</dt>
                  <dd className="text-ink">{r.subject || "–"}</dd>
                </dl>
                <p className="mt-4 whitespace-pre-wrap break-words text-[0.9375rem] leading-7 text-ink">{r.body}</p>
                {r.prospect_id && onValj ? (
                  <button
                    type="button"
                    onClick={() => onValj(r.prospect_id!)}
                    className="focus-ring mt-4 text-[0.8125rem] font-medium text-ink-muted underline underline-offset-4 hover:text-ink"
                  >
                    {text({ sv: "Öppna bolaget", en: "Open the company" })}
                  </button>
                ) : null}
              </div>
            ) : null}
          </li>
        );
      })}
    </ul>
  );
}
