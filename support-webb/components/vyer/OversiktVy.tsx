"use client";

import { ArrowRight } from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";
import { PageHeader } from "@/components/PageHeader";
import { Badge, SkeletonRows } from "@/components/ui";
import { BAS, type Inkorgssvar } from "@/lib/api";
import { felmeddelande, readJson } from "@/lib/http/json";
import { cn } from "@/lib/utils";

/**
 * Läget i inkorgen: hur mycket som väntar på dig, vad agenten redan
 * hanterat, och de senaste ärendena. Ruled rows, inte kortmatta.
 */

const STATUSETIKETT: Record<string, string> = {
  // Samma rättelse som InkorgVy: backendens status heter awaiting_approval.
  awaiting_approval: "Väntar på dig",
  awaiting_review: "Väntar på dig",
  new: "Ny",
  processing: "Bearbetas",
  sent: "Skickat",
  rejected: "Avvisat",
  taken_over: "Övertaget",
  auto_sent: "Skickade själv",
  escalated: "Eskalerade",
  failed: "Föll"
};

export function OversiktVy() {
  const [inkorg, setInkorg] = useState<Inkorgssvar | null>(null);
  const [fel, setFel] = useState<string | null>(null);

  useEffect(() => {
    (async () => {
      try {
        const svar = await fetch(`${BAS}/inbox?limit=100`).then((s) => readJson<Inkorgssvar>(s));
        setInkorg(svar);
      } catch (orsak) {
        setFel(felmeddelande(orsak));
        setInkorg({ emails: [], category_counts: {}, status_counts: {} });
      }
    })();
  }, []);

  const laddar = inkorg === null;
  const statusar = inkorg?.status_counts ?? {};
  const senaste = (inkorg?.emails ?? []).slice(0, 5);

  const nyckeltal: Array<[string, number | string, boolean]> = [
    ["Ärenden i inkorgen", inkorg?.emails.length ?? "—", false],
    ["Väntar på dig", laddar ? "—" : statusar.awaiting_approval ?? 0, (statusar.awaiting_approval ?? 0) > 0],
    ["Eskalerade", laddar ? "—" : statusar.escalated ?? 0, false]
  ];

  return (
    <div className="space-y-10">
      <PageHeader rubrik="Översikt" />

      {fel ? (
        <p role="alert" className="max-w-[70ch] text-[0.875rem] text-danger">
          {fel}
        </p>
      ) : null}

      <section aria-label="Inkorgens nyckeltal">
        <dl className="grid gap-y-6 border-b border-ink/15 pb-6 sm:grid-cols-3 lg:divide-x lg:divide-ink/12">
          {nyckeltal.map(([etikett, varde, lyft], i) => (
            <div key={etikett} className={cn("min-w-0", i > 0 && "lg:pl-8", i < 2 && "lg:pr-8")}>
              <dt className="text-[0.8125rem] font-medium text-ink/55">{etikett}</dt>
              <dd className={cn("numeral mt-2 text-[1.75rem] lg:text-[2rem]", lyft ? "text-ochre" : "text-ink")}>
                {varde}
              </dd>
            </div>
          ))}
        </dl>
      </section>

      <section>
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h2 className="font-display text-[1.25rem]">Senaste ärenden</h2>
          <Link
            href="/inkorg"
            className="focus-ring inline-flex items-center gap-1.5 rounded-[4px] text-[0.875rem] text-ink/60 hover:text-ink"
          >
            Hela inkorgen
            <ArrowRight className="h-3.5 w-3.5" aria-hidden />
          </Link>
        </div>

        {laddar ? (
          <div className="mt-4">
            <SkeletonRows />
          </div>
        ) : senaste.length === 0 ? (
          <div className="mt-4 border-y border-ink/15 py-10 text-center">
            <p className="font-display text-[1.375rem] text-ink">Inkorgen är tom.</p>
          </div>
        ) : (
          <div className="mt-4 divide-y divide-ink/12 border-y border-ink/15">
            {senaste.map((mail) => (
              <Link
                key={mail.id}
                href={`/inkorg?id=${mail.id}`}
                className="focus-ring flex flex-wrap items-baseline gap-x-4 gap-y-1 rounded-[4px] py-3 transition-colors hover:bg-paper2/50"
              >
                <span className="min-w-0 flex-1 truncate text-[0.9375rem] font-medium">
                  {mail.subject || "Utan ämnesrad"}
                </span>
                <span className="truncate text-[0.875rem] text-ink/55">
                  {mail.from_name || mail.from_email || "—"}
                </span>
                {mail.classification?.category ? (
                  <Badge tone="neutral">{mail.classification.category}</Badge>
                ) : null}
                <Badge tone={mail.status === "awaiting_approval" ? "warn" : "good"}>
                  {STATUSETIKETT[mail.status ?? ""] ?? mail.status ?? "—"}
                </Badge>
              </Link>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
