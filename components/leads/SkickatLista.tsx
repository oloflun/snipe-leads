"use client";

import { ChevronDown } from "lucide-react";
import { useMemo, useState } from "react";
import { Badge, SkeletonRows, Tomt, chip, chipAktiv, chipInaktiv, chiplista, meta } from "@/components/ui";
import { useLocale, type Localized } from "@/lib/i18n";
import { relativTid } from "@/lib/leads/suite";
import { STATUS_ETIKETT } from "@/lib/prospekt";
import { cn } from "@/lib/utils";

/**
 * Skickat (Sebbe 2026-10-07, flyttad till Leads › Inkorg › Skickat av Fas 4
 * 2026-10-08): varje leadsmejl som gått ut, med bolaget, mottagaren och hela
 * texten så som den skickades (signatur och lagstadgad fot ingår). Backend:
 * GET /api/leads/skickat.
 *
 * Varje rad bär leadets NUVARANDE status. Svarshanteringen
 * (snajp-support/app/leads/svar.py) och samtalsutfallen flyttar statusen, så
 * raden byter filter av sig själv: Väntar på svar (kontaktad), Svarat, Möte
 * (möte, vunnen) och Ej intresserad (förlorad, spärrad).
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
  /** Leadets nuvarande status (prospects.status). */
  status?: string | null;
};

type Filter = "alla" | "vantar" | "svarat" | "mote" | "ej";

const FILTER: { id: Exclude<Filter, "alla">; etikett: Localized; statusar: string[] }[] = [
  { id: "vantar", etikett: { sv: "Väntar på svar", en: "Awaiting reply" }, statusar: ["contacted"] },
  { id: "svarat", etikett: { sv: "Svarat", en: "Replied" }, statusar: ["replied"] },
  { id: "mote", etikett: { sv: "Möte", en: "Meeting" }, statusar: ["meeting", "won"] },
  { id: "ej", etikett: { sv: "Ej intresserad", en: "Not interested" }, statusar: ["lost", "suppressed"] }
];

/** Filtret en rad hör till. Ett lead vars status inte flyttats (äldre utskick
 *  före 2026-10-07 satte ingen status) väntar fortfarande på svar. */
function filterFor(r: SkickatRad): Exclude<Filter, "alla"> {
  return FILTER.find((f) => f.statusar.includes(r.status ?? ""))?.id ?? "vantar";
}

/** Samma färger som Iris-listans statusprick (LeadsTabell.STATUSPRICK):
 *  grönt i hamn, blått på väg mot affär, rött nej, gult kontaktad utan svar. */
const PRICK: Record<string, string> = {
  contacted: "bg-ochre",
  replied: "bg-chart-blue",
  meeting: "bg-chart-blue",
  won: "bg-moss",
  lost: "bg-danger",
  suppressed: "bg-danger"
};

function Antal({ aktiv, children }: Readonly<{ aktiv: boolean; children: React.ReactNode }>) {
  return <span className={cn("num tabular-nums", aktiv ? "text-paper-muted" : "text-ink-subtle")}>{children}</span>;
}

export function SkickatLista({
  rader,
  fel,
  onValj,
  filtrerbar = false
}: Readonly<{
  rader: SkickatRad[] | null;
  fel: string | null;
  onValj?: (prospektId: string) => void;
  /** Statusfiltren (Inkorg › Skickat). Demons lista i Iris-listan har dem inte. */
  filtrerbar?: boolean;
}>) {
  const { locale, text } = useLocale();
  const [oppen, setOppen] = useState<string | null>(null);
  const [filter, setFilter] = useState<Filter>("alla");

  const antal = useMemo(() => {
    const karta = new Map<Filter, number>([["alla", rader?.length ?? 0]]);
    for (const r of rader ?? []) karta.set(filterFor(r), (karta.get(filterFor(r)) ?? 0) + 1);
    return karta;
  }, [rader]);
  const synliga = useMemo(
    () => (rader ?? []).filter((r) => filter === "alla" || filterFor(r) === filter),
    [rader, filter]
  );

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
    <div className="space-y-4">
      {filtrerbar ? (
        <ul className={chiplista} aria-label={text({ sv: "Filtrera skickade mejl", en: "Filter sent emails" })}>
          {([{ id: "alla", etikett: { sv: "Alla", en: "All" } }, ...FILTER] as { id: Filter; etikett: Localized }[]).map((f) => (
            <li key={f.id}>
              <button
                type="button"
                aria-pressed={filter === f.id}
                onClick={() => setFilter(f.id)}
                className={cn(chip, filter === f.id ? chipAktiv : chipInaktiv)}
              >
                {text(f.etikett)} <Antal aktiv={filter === f.id}>{antal.get(f.id) ?? 0}</Antal>
              </button>
            </li>
          ))}
        </ul>
      ) : null}

      {synliga.length === 0 ? (
        <Tomt>{text({ sv: "Inga skickade mejl i det här filtret.", en: "No sent emails in this filter." })}</Tomt>
      ) : (
        <ul className="divide-y divide-ink/12 border-y border-ink/15" aria-label={text({ sv: "Skickade mejl", en: "Sent emails" })}>
          {synliga.map((r) => {
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
                      {r.status && STATUS_ETIKETT[r.status] ? (
                        <span className="inline-flex items-center gap-1.5 text-[0.8125rem] text-ink-muted">
                          <span aria-hidden className={cn("h-2 w-2 shrink-0 rounded-full", PRICK[r.status] ?? "bg-ochre")} />
                          {text(STATUS_ETIKETT[r.status])}
                        </span>
                      ) : r.svarat ? (
                        <Badge tone="good">{text({ sv: "Svarat", en: "Replied" })}</Badge>
                      ) : null}
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
      )}
    </div>
  );
}
