"use client";

import { AlertTriangle } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { Badge, Rad, Radlista, SkeletonRows, Tomt, btnLiten, btnSecondary, meta, rubrikPanel } from "@/components/ui";
import { EjAktiverad, arEjAktiverad } from "@/components/EjAktiverad";
import { demoOversiktSvar } from "@/lib/demo/oversikt";
import { readJsonBody } from "@/lib/http/json";
import { cn } from "@/lib/utils";

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

/** Datumet, eller null — raden utelämnar då datumet i stället för att visa ett streck. */
function nar(iso: string | null): string | null {
  if (!iso) return null;
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return null;
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
        <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-warning" aria-hidden />
        <div className="min-w-0">
          <p className="text-[0.9375rem] font-medium text-ink">Svaren kunde inte hämtas</p>
          <p className="mt-1 text-[0.9375rem] text-ink-muted">{lage.meddelande}</p>
          <button type="button" onClick={() => void hamta()} className={cn(btnSecondary, btnLiten, "mt-3")}>
            Försök igen
          </button>
        </div>
      </div>
    );
  }

  if (!lage.svar.length) {
    return (
      <Tomt>Inga svar ännu från bolagen som Iris kontaktat.</Tomt>
    );
  }

  // Radlista/Rad ur components/ui.tsx: samma hårlinjespråk som tabellerna,
  // skrivet en gång i stället för som lösa klasser här.
  return (
    <Radlista ariaLabel="Svar från prospekt">
      {lage.svar.map((s) => (
        <Rad key={s.id}>
          {/* Radens anatomi: avsändare → bolag och datum som meta → status
              som Badge till höger. */}
          <div className="flex flex-wrap items-start justify-between gap-x-4 gap-y-1">
            <div className="min-w-0">
              <p className={rubrikPanel}>{s.contact_name ?? s.contact_email ?? "Okänd avsändare"}</p>
              {s.company_name || nar(s.sent_at) ? (
                <p className={cn(meta, "mt-0.5")}>
                  {[s.company_name, nar(s.sent_at)].filter(Boolean).join(" · ")}
                </p>
              ) : null}
            </div>
            {s.status ? <Badge>{STATUS_ETIKETT[s.status] ?? s.status}</Badge> : null}
          </div>
          <p className="mt-2 max-w-[75ch] whitespace-pre-line text-[0.9375rem] leading-6 text-ink-muted">
            {s.body}
          </p>
        </Rad>
      ))}
    </Radlista>
  );
}
