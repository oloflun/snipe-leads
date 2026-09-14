"use client";

import { AlertTriangle } from "lucide-react";
import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { useArbetsvag } from "@/components/AppShell";
import { EmptyState, SkeletonRows } from "@/components/ui";
import { EjAktiverad, arEjAktiverad } from "@/components/EjAktiverad";
import { demoOversiktSvar } from "@/lib/demo/oversikt";
import { readJsonBody } from "@/lib/http/json";

/**
 * Kontakterna — personerna bakom prospekten.
 *
 * ## Varför den läser prospekt och inte en kontakttabell
 *
 * `public.contacts` finns i schemat men skrivs inte av någon kodväg; den är
 * ett fossil från mock-eran, samma sort som `public.companies` (se
 * lib/data/dashboard.ts om sonden som frågade fel tabell). De kontakter
 * produkten faktiskt har är `prospects.contact_name` och `contact_email`, en
 * per bolag. Att läsa en tom tabell och visa "inga kontakter" medan
 * kontakterna syns i bolagslistan hade varit ett fel som ser ut som ett
 * tomtillstånd.
 *
 * Vyn ersatte `contacts` ur lib/mock-data.ts — påhittade personer med
 * påhittade mejladresser, visade för varje inloggad kund.
 *
 * Prospekt UTAN kontaktperson tas bort ur listan i stället för att visas som
 * "—". En rad utan namn och utan adress är inte en kontakt; den hör hemma i
 * bolagslistan, där den redan står.
 */

type Prospekt = {
  id: string;
  company_name: string;
  contact_name: string | null;
  contact_email: string | null;
  status: string;
  ort: string | null;
  sni: string | null;
};

type Lage =
  | { fas: "laddar" }
  | { fas: "ejAktiverad" }
  | { fas: "fel"; meddelande: string }
  | { fas: "klar"; prospekt: Prospekt[] };

const STATUS_ETIKETT: Record<string, string> = {
  new: "Ny",
  researching: "Research pågår",
  ready: "Redo",
  contacted: "Kontaktad",
  replied: "Svarat",
  meeting: "Möte",
  won: "Vunnen",
  lost: "Förlorad",
  suppressed: "Spärrad"
};

export function Kontakter({ demo = false }: Readonly<{ demo?: boolean }>) {
  const [lage, setLage] = useState<Lage>({ fas: "laddar" });
  const vag = useArbetsvag();

  const hamta = useCallback(async () => {
    setLage({ fas: "laddar" });

    if (demo) {
      const svar = demoOversiktSvar("/leads/prospects") as { prospects?: Prospekt[] } | undefined;
      setLage({ fas: "klar", prospekt: svar?.prospects ?? [] });
      return;
    }

    try {
      const response = await fetch("/api/snajp-support/leads/prospects", { cache: "no-store" });
      if (response.status === 409) {
        // Kroppen måste läsas ÄVEN vid felstatus här: koden bor i den, och
        // 409 betyder två olika saker (se arEjAktiverad).
        const kropp = await readJsonBody<unknown>(response).catch(() => null);
        if (arEjAktiverad(response.status, kropp)) {
          setLage({ fas: "ejAktiverad" });
          return;
        }
      }
      if (!response.ok) {
        setLage({
          fas: "fel",
          meddelande:
            response.status >= 500
              ? "Tjänsten svarar inte just nu. Den vaknar ur viloläge och kan ta upp till en minut."
              : `Kunde inte hämta kontakterna (status ${response.status}).`
        });
        return;
      }
      const kropp = await readJsonBody<{ prospects?: Prospekt[]; offline?: boolean }>(response);
      if (!kropp || kropp.offline) {
        setLage({ fas: "fel", meddelande: "Backenden svarade utan innehåll." });
        return;
      }
      setLage({ fas: "klar", prospekt: kropp.prospects ?? [] });
    } catch (error) {
      setLage({
        fas: "fel",
        meddelande: error instanceof Error ? error.message : "Kunde inte nå servern."
      });
    }
  }, [demo]);

  useEffect(() => {
    void hamta();
  }, [hamta]);

  if (lage.fas === "laddar") return <SkeletonRows />;

  if (lage.fas === "ejAktiverad") {
    return <EjAktiverad yta="Kontakter" />;
  }

  if (lage.fas === "fel") {
    return (
      <div className="flex items-start gap-3 border-y border-ochre/40 bg-ochre/10 px-4 py-4">
        <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-ochre" aria-hidden />
        <div className="min-w-0">
          <p className="text-sm font-medium text-ink">Kontakterna kunde inte hämtas</p>
          <p className="mt-1 text-sm text-ink/70">{lage.meddelande}</p>
          <button
            type="button"
            onClick={() => void hamta()}
            className="focus-ring mt-3 inline-flex min-h-9 items-center rounded-input bg-paper2 px-3 text-[13px] font-medium"
          >
            Försök igen
          </button>
        </div>
      </div>
    );
  }

  const kontakter = lage.prospekt.filter((p) => p.contact_name || p.contact_email);

  if (!kontakter.length) {
    return (
      <EmptyState
        title="Inga kontaktpersoner ännu"
        body="Agenten hittar kontaktpersonen när den researchar ett bolag. Bolag utan hittad kontakt står kvar i bolagslistan."
      />
    );
  }

  return (
    <ul className="divide-y divide-ink/15 border-y border-ink/15">
      {kontakter.map((p) => (
        <li key={p.id} className="flex flex-wrap items-baseline justify-between gap-x-6 gap-y-1 py-4">
          <div className="min-w-0">
            <p className="text-[1.0625rem] font-semibold tracking-[-0.01em]">
              {p.contact_name ?? p.contact_email}
            </p>
            {p.contact_name && p.contact_email ? (
              <p className="mt-1 break-all text-sm text-ink/55">{p.contact_email}</p>
            ) : null}
          </div>
          <div className="min-w-0 text-right">
            {demo ? (
              <span className="text-[15px]">{p.company_name}</span>
            ) : (
              <Link
                href={vag(`/dashboard/companies/${p.id}`)}
                className="focus-ring text-[15px] underline decoration-ink/25 underline-offset-4"
              >
                {p.company_name}
              </Link>
            )}
            <p className="kicker mt-1 text-mineral">
              {[p.sni, p.ort].filter(Boolean).join(" · ")}
              {p.status ? ` · ${STATUS_ETIKETT[p.status] ?? p.status}` : ""}
            </p>
          </div>
        </li>
      ))}
    </ul>
  );
}
