"use client";

import { AlertTriangle } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { EmptyState, SkeletonRows } from "@/components/ui";
import { EjAktiverad, arEjAktiverad } from "@/components/EjAktiverad";
import { demoOversiktSvar } from "@/lib/demo/oversikt";
import { readJsonBody } from "@/lib/http/json";

/**
 * Svar — vad prospekten faktiskt svarat.
 *
 * ## Vad den ersatte
 *
 * Fliken renderade sju hårdkodade svar ur en array i WorkspaceViews.tsx:
 * "Låter relevant. Skicka gärna exempel på IT-chefer i regionen." och sex till,
 * med påhittade avsändarnamn, för varje inloggad kund. Kommentaren i koden
 * förklarade att alla sex klasser skulle finnas med "eftersom en demo som
 * utlovar sex kategorier men visar tre ser ut som att hälften av
 * klassificeraren är trasig" — men vyn låg inte bara i demon. Den låg i den
 * betalda arbetsytan, där påhittade svar från påhittade personer ser ut som
 * riktiga svar från riktiga personer.
 *
 * ## Klassificeringen står inte här
 *
 * Den gamla vyn visade en klass per svar (positive, objection, away…).
 * `outreach_messages` har ingen sådan kolumn, och ingen kodväg skriver en.
 * Att räkna fram den i webbläsaren ur brödtexten hade varit en gissning
 * presenterad som ett agentbeslut — samma sort som möteskolumnen i analysvyn.
 * Kolumnen är därför borta tills klassificeraren skriver sitt utfall till
 * databasen; prospektets status står i stället, och den är räknad.
 */

type Svarsrad = {
  id: string;
  body: string;
  sent_at: string | null;
  thread_id: string;
  company_name: string | null;
  contact_name: string | null;
  contact_email: string | null;
  status: string | null;
};

type Lage =
  | { fas: "laddar" }
  | { fas: "ejAktiverad" }
  | { fas: "fel"; meddelande: string }
  | { fas: "klar"; svar: Svarsrad[] };

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

function nar(iso: string | null): string {
  if (!iso) return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "—";
  return d.toLocaleDateString("sv-SE", { day: "numeric", month: "short" });
}

export function Svar({ demo = false }: Readonly<{ demo?: boolean }>) {
  const [lage, setLage] = useState<Lage>({ fas: "laddar" });

  const hamta = useCallback(async () => {
    setLage({ fas: "laddar" });

    if (demo) {
      const svar = demoOversiktSvar("/leads/svar") as { replies?: Svarsrad[] } | undefined;
      setLage({ fas: "klar", svar: svar?.replies ?? [] });
      return;
    }

    try {
      const response = await fetch("/api/snajp-support/leads/svar", { cache: "no-store" });
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
              : `Kunde inte hämta svaren (status ${response.status}).`
        });
        return;
      }
      const kropp = await readJsonBody<{ replies?: Svarsrad[]; offline?: boolean }>(response);
      if (!kropp || kropp.offline) {
        setLage({ fas: "fel", meddelande: "Backenden svarade utan innehåll." });
        return;
      }
      setLage({ fas: "klar", svar: kropp.replies ?? [] });
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
    return <EjAktiverad yta="Svar" />;
  }

  if (lage.fas === "fel") {
    return (
      <div className="flex items-start gap-3 border-y border-ochre/40 bg-ochre/10 px-4 py-4">
        <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-ochre" aria-hidden />
        <div className="min-w-0">
          <p className="text-sm font-medium text-ink">Svaren kunde inte hämtas</p>
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

  if (!lage.svar.length) {
    return (
      <EmptyState
        title="Inga svar ännu"
        body="Här hamnar svaren från bolagen agenten kontaktat. Listan är tom tills någon svarat — inga exempelsvar som platshållare."
      />
    );
  }

  return (
    <ul className="divide-y divide-ink/15 border-y border-ink/15">
      {lage.svar.map((s) => (
        <li key={s.id} className="py-5">
          <div className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
            <p className="text-[1.0625rem] font-semibold tracking-[-0.01em]">
              {s.contact_name ?? s.contact_email ?? "Okänd avsändare"}
              {s.company_name ? (
                <span className="ml-2 text-[15px] font-normal text-ink/55">{s.company_name}</span>
              ) : null}
            </p>
            <span className="kicker shrink-0 text-mineral">
              {nar(s.sent_at)}
              {s.status ? ` · ${STATUS_ETIKETT[s.status] ?? s.status}` : ""}
            </span>
          </div>
          <p className="mt-2 max-w-[75ch] whitespace-pre-line text-[15px] leading-6 text-ink/78">
            {s.body}
          </p>
        </li>
      ))}
    </ul>
  );
}
