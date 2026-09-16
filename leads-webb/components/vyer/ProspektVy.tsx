"use client";

import { useEffect, useState } from "react";
import { PageHeader } from "@/components/PageHeader";
import { Badge, EmptyState, SkeletonRows } from "@/components/ui";
import { BAS, type Prospekt } from "@/lib/api";
import { felmeddelande, readJson } from "@/lib/http/json";

/**
 * Bolagen agenten hittat, som täta rader: namn, ort, träffsäkerhet mot
 * målgruppen, kontaktväg och läge. Underkännandeskälen visas rakt på raden —
 * ett bortvalt bolag ska bära sitt varför.
 */
export function ProspektVy() {
  const [prospekt, setProspekt] = useState<Prospekt[] | null>(null);
  const [fel, setFel] = useState<string | null>(null);

  useEffect(() => {
    (async () => {
      try {
        const svar = await fetch(`${BAS}/leads/prospects`).then((s) =>
          readJson<{ prospects: Prospekt[] }>(s)
        );
        setProspekt(svar?.prospects ?? []);
      } catch (orsak) {
        setFel(felmeddelande(orsak));
        setProspekt([]);
      }
    })();
  }, []);

  return (
    <div className="space-y-8">
      <PageHeader
        rubrik="Prospekt"
        beskrivning="Bolagen agenten hittat åt dig, med träffsäkerhet mot din målgrupp. Underkända bolag står kvar med sitt skäl — det agenten valt bort ska gå att kontrollera."
      />

      {fel ? (
        <p role="alert" className="max-w-[70ch] text-[0.875rem] text-danger">
          {fel}
        </p>
      ) : null}

      {prospekt === null ? (
        <SkeletonRows />
      ) : prospekt.length === 0 ? (
        <EmptyState
          title="Inga prospekt ännu"
          body="Kör agenten så letar den fram bolag som matchar din målgrupp och lägger dem här."
        />
      ) : (
        <div className="divide-y divide-ink/12 border-y border-ink/15">
          {prospekt.map((rad) => (
            <div key={rad.id} className="py-3">
              <div className="flex flex-wrap items-baseline gap-x-4 gap-y-1">
                <span className="min-w-0 flex-1 truncate text-[0.9375rem] font-medium">
                  {rad.company_name}
                </span>
                {rad.ort ? <span className="text-[0.875rem] text-ink/50">{rad.ort}</span> : null}
                <span
                  className="num w-[4.5rem] text-right text-[0.9375rem] text-ink/62"
                  title="Träffsäkerhet mot din målgrupp"
                >
                  {typeof rad.icp_fit === "number" ? `${Math.round(rad.icp_fit * 100)} %` : "—"}
                </span>
                <Badge tone={rad.qualified ? "good" : rad.disqualifiers?.length ? "warn" : "neutral"}>
                  {rad.qualified ? "Kvalificerad" : rad.disqualifiers?.length ? "Underkänd" : rad.status || "Ny"}
                </Badge>
              </div>
              <div className="mt-0.5 flex flex-wrap gap-x-4 text-[0.875rem] text-ink/55">
                {rad.contact_name ? <span>{rad.contact_name}</span> : null}
                {rad.contact_email ? <span>{rad.contact_email}</span> : null}
              </div>
              {rad.disqualifiers?.length ? (
                <p className="mt-1 max-w-[78ch] text-[0.875rem] text-ink/55">
                  {rad.disqualifiers.join("; ")}
                </p>
              ) : null}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
