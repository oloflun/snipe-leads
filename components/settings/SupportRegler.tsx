"use client";

import { Loader2 } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { createDemoSupportApi } from "@/lib/demo/support-inbox";
import { readJsonBody } from "@/lib/http/json";
import { cn } from "@/lib/utils";

/**
 * Autosvarsreglerna per fack.
 *
 * ## Varför de flyttade hit
 *
 * De låg i en utfällbar panel inuti inkorgen (`components/snajp/Dashboard.tsx`)
 * medan leads-agentens motsvarande kontroll — hur långt agenten får gå på egen
 * hand — låg under Inställningar. Samma fråga, två helt olika ställen, och för
 * en duo-kund var det inte uppenbart att det VAR samma fråga.
 *
 * Inkorgen behåller en länk hit. Panelen där var dessutom en av två saker som
 * gömdes bakom en knapp på en yta där resten var synligt.
 */

type Regel = { category: string; label: string; mode: "auto" | "draft" | "escalate" };

const LAGEN: { varde: Regel["mode"]; etikett: string; forklaring: string }[] = [
  {
    varde: "draft",
    etikett: "Utkast",
    forklaring: "Agenten skriver svaret, du godkänner det. Standard."
  },
  {
    varde: "auto",
    etikett: "Auto",
    forklaring: "Skickas direkt när konfidensen är hög och tonen inte är negativ."
  },
  { varde: "escalate", etikett: "Eskalera", forklaring: "Går alltid till en människa." }
];

export function SupportRegler({ demo = false }: Readonly<{ demo?: boolean }>) {
  const [demoApi] = useState(() => (demo ? createDemoSupportApi() : null));
  const [regler, setRegler] = useState<Regel[] | null>(null);
  const [sparar, setSparar] = useState<string | null>(null);
  const [fel, setFel] = useState<string | null>(null);
  const [klart, setKlart] = useState<string | null>(null);

  const api = useCallback(
    async <T,>(path: string, init?: RequestInit): Promise<T> => {
      if (demoApi) return demoApi<T>(path, init);
      const response = await fetch(`/api/snajp-support${path}`, {
        headers: { "Content-Type": "application/json" },
        cache: "no-store",
        ...init
      });
      const kropp = await readJsonBody<T & { error?: string; detail?: string; offline?: boolean }>(
        response
      );
      if (!response.ok || kropp?.offline) {
        throw new Error(kropp?.detail ?? kropp?.error ?? `Kunde inte nå reglerna (${response.status}).`);
      }
      return (kropp ?? ({} as T)) as T;
    },
    [demoApi]
  );

  const ladda = useCallback(async () => {
    try {
      setFel(null);
      setRegler((await api<{ rules?: Regel[] }>("/rules")).rules ?? []);
    } catch (orsak) {
      setFel(orsak instanceof Error ? orsak.message : "Kunde inte hämta reglerna.");
      setRegler([]);
    }
  }, [api]);

  useEffect(() => {
    void ladda();
  }, [ladda]);

  async function satt(kategori: string, lage: string) {
    setSparar(kategori);
    setFel(null);
    setKlart(null);
    try {
      await api("/rules", { method: "PUT", body: JSON.stringify({ category: kategori, mode: lage }) });
      await ladda();
      setKlart("Sparat. Regeln gäller från nästa ärende.");
    } catch (orsak) {
      setFel(orsak instanceof Error ? orsak.message : "Kunde inte spara regeln.");
    } finally {
      setSparar(null);
    }
  }

  if (regler === null) {
    return (
      <div className="grid gap-3" aria-busy="true">
        {Array.from({ length: 6 }).map((_, index) => (
          <div key={index} className="h-14 animate-pulse rounded-card bg-ink/[0.055]" />
        ))}
      </div>
    );
  }

  return (
    <div className="grid gap-7">
      <dl className="grid gap-4 border-t border-ink/15 pt-5 sm:grid-cols-3">
        {LAGEN.map((lage) => (
          <div key={lage.varde}>
            <dt className="text-[0.9375rem] font-semibold">{lage.etikett}</dt>
            <dd className="mt-1 text-[0.875rem] leading-6 text-ink/60">{lage.forklaring}</dd>
          </div>
        ))}
      </dl>

      {/* Spärren står här och inte bara i koden: en kund som sätter allt på
          Auto ska veta vad som ändå aldrig går den vägen. */}
      <p className="max-w-[68ch] rounded-card bg-paper2/50 px-5 py-4 text-[0.875rem] leading-6 text-ink/70">
        Pengar, juridik, GDPR och arga kunder eskaleras alltid till en människa, oavsett vad som
        står här.
      </p>

      <div className="divide-y divide-ink/10 border-y border-ink/15">
        {regler.map((regel) => (
          <div
            key={regel.category}
            className="flex flex-wrap items-center justify-between gap-x-6 gap-y-2 py-3.5"
          >
            <span className="text-[0.9375rem]">{regel.label}</span>
            <span className="flex items-center gap-2">
              {sparar === regel.category ? (
                <Loader2 className="h-4 w-4 animate-spin text-ink/40" aria-hidden />
              ) : null}
              <select
                value={regel.mode}
                disabled={sparar !== null}
                aria-label={`Hantering av ${regel.label}`}
                onChange={(e) => void satt(regel.category, e.target.value)}
                className={cn(
                  "focus-ring min-h-11 rounded-input border border-ink/15 bg-paper px-3 text-[16px]",
                  "disabled:cursor-not-allowed disabled:opacity-40"
                )}
              >
                {LAGEN.map((lage) => (
                  <option key={lage.varde} value={lage.varde}>
                    {lage.etikett}
                  </option>
                ))}
              </select>
            </span>
          </div>
        ))}
      </div>

      {klart ? (
        <p role="status" className="text-[0.875rem] text-moss">
          {klart}
        </p>
      ) : null}
      {fel ? (
        <p role="alert" className="max-w-[62ch] break-words text-[0.875rem] text-danger">
          {fel}
        </p>
      ) : null}
    </div>
  );
}
