"use client";

import { ArrowRight, Play } from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";
import { PageHeader } from "@/components/PageHeader";
import { Badge, SkeletonRows, btnLiten, btnPrimary } from "@/components/ui";
import { BAS, type KoPost, type Prospekt } from "@/lib/api";
import { felmeddelande, readJson } from "@/lib/http/json";
import { cn } from "@/lib/utils";

/**
 * Första vyn: läget i pipelinen, i tre tal, och vägen vidare. Ruled rows,
 * inte kortmatta — samma App-familj som resten av Snajp.
 */
export function OversiktVy() {
  const [prospekt, setProspekt] = useState<Prospekt[] | null>(null);
  const [ko, setKo] = useState<KoPost[] | null>(null);
  const [fel, setFel] = useState<string | null>(null);

  useEffect(() => {
    (async () => {
      try {
        const [p, k] = await Promise.all([
          fetch(`${BAS}/leads/prospects`).then((s) => readJson<{ prospects: Prospekt[] }>(s)),
          fetch(`${BAS}/leads/queue`).then((s) => readJson<{ items: KoPost[] }>(s))
        ]);
        setProspekt(p?.prospects ?? []);
        setKo(k?.items ?? []);
      } catch (orsak) {
        setFel(felmeddelande(orsak));
        setProspekt([]);
        setKo([]);
      }
    })();
  }, []);

  const laddar = prospekt === null;
  const kvalificerade = (prospekt ?? []).filter((p) => p.qualified).length;
  const senaste = (prospekt ?? []).slice(0, 5);

  const nyckeltal: Array<[string, number | string]> = [
    ["Prospekt", prospekt?.length ?? "—"],
    ["Kvalificerade", laddar ? "—" : kvalificerade],
    ["Väntar på din granskning", ko?.length ?? "—"]
  ];

  return (
    <div className="space-y-10">
      <PageHeader
        rubrik="Översikt"
        beskrivning="Bolagen agenten hittat, hur många som kvalificerat sig, och utkasten som väntar på ditt godkännande. Ingenting skickas utan att du sagt ja."
        actions={
          <Link href="/agenten" className={cn(btnPrimary, btnLiten)}>
            <Play className="h-4 w-4" aria-hidden />
            Kör agenten
          </Link>
        }
      />

      {fel ? (
        <p role="alert" className="max-w-[70ch] text-[0.875rem] text-danger">
          {fel}
        </p>
      ) : null}

      <section aria-label="Pipelinens nyckeltal">
        <dl className="grid gap-y-6 border-y border-ink/15 py-6 sm:grid-cols-3 lg:divide-x lg:divide-ink/12">
          {nyckeltal.map(([etikett, varde], i) => (
            <div key={etikett} className={cn("min-w-0", i > 0 && "lg:pl-8", i < 2 && "lg:pr-8")}>
              <dt className="text-[0.8125rem] font-medium text-ink/55">{etikett}</dt>
              <dd
                className={cn(
                  "numeral mt-2 text-[1.75rem] lg:text-[2rem]",
                  etikett === "Väntar på din granskning" && (ko?.length ?? 0) > 0
                    ? "text-ochre"
                    : "text-ink"
                )}
              >
                {varde}
              </dd>
            </div>
          ))}
        </dl>
        {(ko?.length ?? 0) > 0 ? (
          <p className="mt-3 text-[0.875rem] text-ink/60">
            <Link
              href="/granskning"
              className="focus-ring rounded-[4px] underline decoration-ochre/50 underline-offset-4 hover:text-ink"
            >
              {ko?.length} utkast väntar i granskningskön
            </Link>
          </p>
        ) : null}
      </section>

      <section>
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h2 className="font-display text-[1.25rem]">Senaste prospekt</h2>
          <Link
            href="/prospekt"
            className="focus-ring inline-flex items-center gap-1.5 rounded-[4px] text-[0.875rem] text-ink/60 hover:text-ink"
          >
            Alla prospekt
            <ArrowRight className="h-3.5 w-3.5" aria-hidden />
          </Link>
        </div>

        {laddar ? (
          <div className="mt-4">
            <SkeletonRows />
          </div>
        ) : senaste.length === 0 ? (
          <div className="mt-4 border-y border-ink/15 py-10 text-center">
            <p className="font-display text-[1.375rem] text-ink">
              Inga prospekt ännu — låt agenten leta.
            </p>
            <p className="mx-auto mt-2 max-w-[52ch] text-[0.9375rem] leading-6 text-ink/60">
              Agenten söker fram bolag som matchar din målgrupp, gör research
              och skriver utkast som du granskar innan något skickas.
            </p>
            <Link href="/agenten" className={cn(btnPrimary, "mt-5")}>
              Kör agenten
              <ArrowRight className="h-4 w-4" aria-hidden />
            </Link>
          </div>
        ) : (
          <div className="mt-4 divide-y divide-ink/12 border-y border-ink/15">
            {senaste.map((rad) => (
              <div key={rad.id} className="flex flex-wrap items-baseline gap-x-4 gap-y-1 py-3">
                <span className="min-w-0 flex-1 truncate text-[0.9375rem] font-medium">
                  {rad.company_name}
                </span>
                {rad.ort ? <span className="text-[0.875rem] text-ink/50">{rad.ort}</span> : null}
                <span className="num text-[0.9375rem] text-ink/62">
                  {typeof rad.icp_fit === "number" ? `${Math.round(rad.icp_fit * 100)} %` : "—"}
                </span>
                <Badge tone={rad.qualified ? "good" : "neutral"}>
                  {rad.qualified ? "Kvalificerad" : rad.status || "Ny"}
                </Badge>
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
