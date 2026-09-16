"use client";

import { useEffect, useState } from "react";
import { PageHeader } from "@/components/PageHeader";
import { Badge, EmptyState, SkeletonRows } from "@/components/ui";
import { BAS, type Leadslista } from "@/lib/api";
import { felmeddelande, readJson } from "@/lib/http/json";

/** Beställda leadslistor med status. Beställningen görs tills vidare i
 *  Snajp-webben — den här vyn är läget och resultatet. */
export function ListorVy() {
  const [listor, setListor] = useState<Leadslista[] | null>(null);
  const [fel, setFel] = useState<string | null>(null);

  useEffect(() => {
    (async () => {
      try {
        const svar = await fetch(`${BAS}/leads/listor`).then((s) =>
          readJson<{ lists: Leadslista[] }>(s)
        );
        setListor(svar?.lists ?? []);
      } catch (orsak) {
        setFel(felmeddelande(orsak));
        setListor([]);
      }
    })();
  }, []);

  return (
    <div className="space-y-8">
      <PageHeader
        rubrik="Leadslistor"
        beskrivning="Färdiga listor Iris byggt: verifierade bolag med kontaktväg, källa och signal per rad. Ingenting i en lista skickas någonsin automatiskt."
      />

      {fel ? (
        <p role="alert" className="max-w-[70ch] text-[0.875rem] text-danger">
          {fel}
        </p>
      ) : null}

      {listor === null ? (
        <SkeletonRows />
      ) : listor.length === 0 ? (
        <EmptyState
          title="Inga leadslistor ännu"
          body="Listor beställs från arbetsytan på Snajp-webben. När en lista är byggd dyker den upp här med status och innehåll."
        />
      ) : (
        <div className="divide-y divide-ink/12 border-y border-ink/15">
          {listor.map((lista) => (
            <div key={lista.id} className="flex flex-wrap items-baseline gap-x-4 gap-y-1 py-3">
              <span className="min-w-0 flex-1 truncate text-[0.9375rem] font-medium">
                {lista.titel || "Utan titel"}
              </span>
              {typeof lista.antal === "number" ? (
                <span className="num text-[0.9375rem] text-ink/62">{lista.antal} rader</span>
              ) : null}
              <Badge tone={lista.status === "klar" ? "good" : "neutral"}>
                {lista.status || "beställd"}
              </Badge>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
