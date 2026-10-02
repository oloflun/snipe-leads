"use client";

import { AlertTriangle } from "lucide-react";
import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { useArbetsvag } from "@/components/AppShell";
import { Cell, EmptyState, SkeletonRows, Tabell, tabellRad } from "@/components/ui";
import { EjAktiverad, arEjAktiverad } from "@/components/EjAktiverad";
import { demoOversiktSvar } from "@/lib/demo/oversikt";
import { readJsonBody } from "@/lib/http/json";
import { useLocale, type Localized } from "@/lib/i18n";

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
  | { fas: "fel"; meddelande: Localized }
  | { fas: "klar"; prospekt: Prospekt[] };

const STATUS_ETIKETT: Record<string, Localized> = {
  new: { sv: "Ny", en: "New" },
  researching: { sv: "Research pågår", en: "Researching" },
  ready: { sv: "Redo", en: "Ready" },
  contacted: { sv: "Kontaktad", en: "Contacted" },
  replied: { sv: "Svarat", en: "Replied" },
  meeting: { sv: "Möte", en: "Meeting" },
  won: { sv: "Vunnen", en: "Won" },
  lost: { sv: "Förlorad", en: "Lost" },
  suppressed: { sv: "Spärrad", en: "Blocked" }
};

export function Kontakter({ demo = false }: Readonly<{ demo?: boolean }>) {
  const { text } = useLocale();
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
              ? { sv: "Tjänsten svarar inte. Försök igen om en minut.", en: "The service is not responding. Try again in a minute." }
              : {
                  sv: `Kunde inte hämta kontakterna (status ${response.status}).`,
                  en: `Could not fetch the contacts (status ${response.status}).`
                }
        });
        return;
      }
      const kropp = await readJsonBody<{ prospects?: Prospekt[]; offline?: boolean }>(response);
      if (!kropp || kropp.offline) {
        setLage({ fas: "fel", meddelande: { sv: "Backenden svarade utan innehåll.", en: "The backend replied without content." } });
        return;
      }
      setLage({ fas: "klar", prospekt: kropp.prospects ?? [] });
    } catch (error) {
      setLage({
        fas: "fel",
        meddelande:
          error instanceof Error
            ? { sv: error.message, en: error.message }
            : { sv: "Kunde inte nå servern.", en: "Could not reach the server." }
      });
    }
  }, [demo]);

  useEffect(() => {
    void hamta();
  }, [hamta]);

  if (lage.fas === "laddar") return <SkeletonRows />;

  if (lage.fas === "ejAktiverad") {
    return <EjAktiverad yta={text({ sv: "Kontakter", en: "Contacts" })} />;
  }

  if (lage.fas === "fel") {
    return (
      <div className="flex items-start gap-3 border-y border-ochre/40 bg-ochre/10 px-4 py-4">
        <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-warning" aria-hidden />
        <div className="min-w-0">
          <p className="text-sm font-medium text-ink">{text({ sv: "Kontakterna kunde inte hämtas", en: "The contacts could not be fetched" })}</p>
          <p className="mt-1 text-sm text-ink-muted">{text(lage.meddelande)}</p>
          <button
            type="button"
            onClick={() => void hamta()}
            className="focus-ring mt-3 inline-flex min-h-9 items-center rounded-input bg-paper2 px-3 text-[13px] font-medium"
          >
            {text({ sv: "Försök igen", en: "Try again" })}
          </button>
        </div>
      </div>
    );
  }

  const kontakter = lage.prospekt.filter((p) => p.contact_name || p.contact_email);

  if (!kontakter.length) {
    return (
      <EmptyState title={text({ sv: "Inga kontaktpersoner ännu", en: "No contacts yet" })} />
    );
  }

  // Fast tabell i stället för flexrader: samma kolumn på samma plats på varje
  // rad, oavsett hur långt ett namn eller en adress är. Se Tabell i
  // components/ui.tsx för varför bredderna är deklarerade.
  return (
    <Tabell
      ariaLabel={text({ sv: "Kontaktpersoner", en: "Contacts" })}
      kolumner={[
        { rubrik: text({ sv: "Kontakt", en: "Contact" }), bredd: "30%" },
        { rubrik: text({ sv: "Bolag", en: "Company" }), bredd: "28%" },
        { rubrik: text({ sv: "Segment", en: "Segment" }), bredd: "26%" },
        { rubrik: text({ sv: "Status", en: "Status" }), bredd: "16%", hoger: true }
      ]}
    >
      {kontakter.map((p) => (
        <tr key={p.id} className={tabellRad}>
          <Cell titel>
            <p className="truncate font-semibold tracking-[-0.01em]">
              {p.contact_name ?? p.contact_email}
            </p>
            {p.contact_name && p.contact_email ? (
              <p className="mt-1 truncate text-sm text-ink-subtle">{p.contact_email}</p>
            ) : null}
          </Cell>
          <Cell>
            {demo ? (
              <span className="block truncate">{p.company_name}</span>
            ) : (
              <Link
                href={vag(`/dashboard/companies/${p.id}`)}
                className="focus-ring block truncate underline decoration-ink/25 underline-offset-4"
              >
                {p.company_name}
              </Link>
            )}
          </Cell>
          <Cell>
            <span className="block truncate text-sm text-ink-muted">
              {[p.sni, p.ort].filter(Boolean).join(" · ") || "–"}
            </span>
          </Cell>
          <Cell hoger>
            <span className="text-sm text-ink-muted">
              {p.status ? (STATUS_ETIKETT[p.status] ? text(STATUS_ETIKETT[p.status]) : p.status) : "–"}
            </span>
          </Cell>
        </tr>
      ))}
    </Tabell>
  );
}
