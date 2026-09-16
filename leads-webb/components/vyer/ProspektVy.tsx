"use client";

import { ChevronDown } from "lucide-react";
import { useEffect, useState } from "react";
import { PageHeader } from "@/components/PageHeader";
import { Badge, EmptyState, SkeletonRows } from "@/components/ui";
import { BAS, type Prospekt } from "@/lib/api";
import { felmeddelande, readJson } from "@/lib/http/json";
import { kallEtikett, statusEtikett } from "@/lib/iris";
import { cn } from "@/lib/utils";

/**
 * Bolagen Iris hittat, som täta rader: namn, ort, träffsäkerhet mot
 * målgruppen, kontaktväg och läge. Underkännandeskälen visas rakt på raden —
 * ett bortvalt bolag ska bära sitt varför.
 *
 * Källtransparensen: "Hittad via" på varje rad. Källorna sparas per prospekt
 * i backenden (prospect_sources) och hämtas ur detaljendpointen först när
 * raden fälls ut — listan förblir en lista, inte hundra extra anrop.
 * Visas det inga källor är det sanningen: utan källa får Iris inte skriva
 * ett utkast, och det ska synas snarare än döljas.
 */

type Kallage =
  | { fas: "stangd" }
  | { fas: "hamtar" }
  | { fas: "klar"; kallor: string[] }
  | { fas: "fel"; text: string };

function Kallrad({ id }: Readonly<{ id: string }>) {
  const [lage, setLage] = useState<Kallage>({ fas: "stangd" });
  const oppen = lage.fas !== "stangd";

  async function vaxla() {
    if (oppen) {
      setLage({ fas: "stangd" });
      return;
    }
    setLage({ fas: "hamtar" });
    try {
      const svar = await fetch(`${BAS}/leads/prospects/${encodeURIComponent(id)}`).then((s) =>
        readJson<{ sources?: string[] }>(s)
      );
      setLage({ fas: "klar", kallor: svar?.sources ?? [] });
    } catch (orsak) {
      setLage({ fas: "fel", text: felmeddelande(orsak) });
    }
  }

  return (
    <div className="mt-1">
      <button
        type="button"
        onClick={() => void vaxla()}
        aria-expanded={oppen}
        className="focus-ring inline-flex items-center gap-1 rounded-[4px] text-[0.8125rem] text-ink/55 hover:text-ink"
      >
        <ChevronDown
          className={cn("h-3.5 w-3.5 transition-transform", oppen && "rotate-180")}
          aria-hidden
        />
        Hittad via
      </button>
      {lage.fas === "hamtar" ? (
        <p className="mt-1 text-[0.8125rem] text-ink/45">Hämtar källor …</p>
      ) : lage.fas === "fel" ? (
        <p className="mt-1 text-[0.8125rem] text-danger">{lage.text}</p>
      ) : lage.fas === "klar" ? (
        lage.kallor.length ? (
          <ul className="mt-1.5 space-y-1">
            {lage.kallor.map((url) => (
              <li key={url} className="flex flex-wrap items-baseline gap-x-2.5">
                <span className="rounded-[6px] border border-ink/10 bg-ink/[0.035] px-2 py-0.5 text-xs font-medium text-ink/70">
                  {kallEtikett(url)}
                </span>
                <a
                  href={url}
                  target="_blank"
                  rel="noreferrer noopener"
                  className="focus-ring min-w-0 break-all rounded-[4px] text-[0.8125rem] text-ink/55 underline decoration-ink/25 underline-offset-4 hover:text-ink"
                >
                  {url}
                </a>
              </li>
            ))}
          </ul>
        ) : (
          <p className="mt-1 max-w-[70ch] text-[0.8125rem] text-ink/50">
            Inga källor sparade för det här bolaget. Utan minst en källa skriver Iris inget
            utkast. Det är källkravet, inte ett fel.
          </p>
        )
      ) : null}
    </div>
  );
}

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
        beskrivning="Bolagen Iris hittat åt dig, med träffsäkerhet mot din målgrupp och källorna bakom varje fynd. Underkända bolag står kvar med sitt skäl, så att det Iris valt bort går att kontrollera."
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
          body="Kör Iris så letar hon fram bolag som matchar din målgrupp och lägger dem här."
        />
      ) : (
        <div className="divide-y divide-ink/12 border-y border-ink/15">
          {prospekt.map((rad) => (
            <div key={rad.id} className="py-3">
              <div className="flex flex-wrap items-baseline gap-x-4 gap-y-1">
                <span className="min-w-0 flex-1 basis-full break-words text-[0.9375rem] font-medium sm:basis-auto sm:truncate">
                  {rad.company_name}
                </span>
                {rad.ort ? <span className="text-[0.875rem] text-ink/50">{rad.ort}</span> : null}
                <span
                  className="num text-[0.9375rem] text-ink/62 sm:w-[4.5rem] sm:text-right"
                  title="Träffsäkerhet mot din målgrupp"
                >
                  {typeof rad.icp_fit === "number" ? `${Math.round(rad.icp_fit * 100)} %` : "—"}
                </span>
                <Badge tone={rad.qualified ? "good" : rad.disqualifiers?.length ? "warn" : "neutral"}>
                  {rad.qualified
                    ? "Kvalificerad"
                    : rad.disqualifiers?.length
                      ? "Underkänd"
                      : (rad.status && statusEtikett(rad.status)) || "Ny"}
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
              <Kallrad id={rad.id} />
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
