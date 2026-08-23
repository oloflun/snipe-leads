"use client";

import { AlertTriangle } from "lucide-react";
import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { useArbetsvag } from "@/components/AppShell";
import { EmptyState, SkeletonRows } from "@/components/ui";
import { EjAktiverad, arEjAktiverad } from "@/components/EjAktiverad";
import { demoOversiktSvar } from "@/lib/demo/oversikt";
import { readJsonBody } from "@/lib/http/json";
import { cn } from "@/lib/utils";

/**
 * Bolagsregistret — kundens EGNA prospekt.
 *
 * ## Vad det ersatte
 *
 * Vyn renderade `companies` ur `lib/mock-data.ts`: Byggkompaniet Syd, Ateljé
 * Måltid, Nordic Sweat Studios och två till, med påhittade kontaktpersoner och
 * mejladresser — för varje INLOGGAD kund, på både /dashboard/leads och
 * /dashboard/companies. En ny kund som öppnade fliken fick intrycket att
 * agenterna redan hittat fem bolag åt dem.
 *
 * Det är samma fel som Email Studio hade (b5277d1) och som analysvyn hade:
 * exempeldata omärkt i en betald yta. Skillnaden mellan de tre var bara vilken
 * flik man råkade öppna.
 *
 * ## Regler
 *
 * Prospekten hämtas ur `/leads/prospects`, som är tenant-skopad ur sessionen.
 * Tom lista är TOM — inga exempelbolag som platshållare, eftersom det var just
 * den vänligheten som blev lögnen. Ett trasigt anrop säger att det är trasigt.
 *
 * Statusordet översätts. Tabellen visade tidigare våra interna värden
 * ("recommended", "queued") oöversatta i en kundvänd vy; kolumnen togs bort
 * helt av det skälet. Den är tillbaka nu när orden är på svenska.
 */

type Prospekt = {
  id: string;
  company_name: string;
  contact_name: string | null;
  contact_email: string | null;
  status: string;
  ort: string | null;
  sni: string | null;
  website: string | null;
  score_total: number | null;
  icp_fit: number | null;
  qualified: boolean | null;
  disqualifiers: string[] | null;
  score_breakdown: Kriterium[] | null;
};

type Kriterium = { etikett: string; utfall: string; motivering: string; hart?: boolean };

type Lage =
  | { fas: "laddar" }
  | { fas: "ejAktiverad" }
  | { fas: "fel"; meddelande: string }
  | { fas: "klar"; prospekt: Prospekt[] };

/** Backendens statusvärden, på svenska. Speglar check-villkoret i migration 010. */
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

/** Status som betyder att något väntar på kunden — bär ochre, resten är neutrala. */
const AKTIV_STATUS = new Set(["ready", "replied", "meeting"]);

function segment(p: Prospekt): string {
  return [p.sni, p.ort].filter(Boolean).join(" · ") || "—";
}

/**
 * Signalen: det starkaste kriteriet som faktiskt slog in.
 *
 * `score_breakdown` sparas RENDERAD (migration 031) just för att en poäng utan
 * motivering inte går att lita på — och den motiveringen är det närmaste en
 * "signal" prospektet har. Diskvalificerare vinner över den: att ett bolag
 * sorterats bort är viktigare än varför det nästan platsade.
 */
function signal(p: Prospekt): string {
  if (p.disqualifiers?.length) {
    return p.disqualifiers[0];
  }
  const träff = p.score_breakdown?.find((k) => k.motivering && k.utfall !== "saknas");
  return träff?.motivering ?? "—";
}

function poang(p: Prospekt): string {
  if (typeof p.score_total === "number") return String(p.score_total);
  if (typeof p.icp_fit === "number") return String(Math.round(p.icp_fit * 100));
  return "—";
}

export function Bolagsregister({ demo = false }: Readonly<{ demo?: boolean }>) {
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
      // response.ok före tolkningen: en sovande backend svarar med HTML, och
      // `.json()` på den ger kunden webbläsarens råa felmeddelande.
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
              : `Kunde inte hämta bolagen (status ${response.status}).`
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

  if (lage.fas === "laddar") {
    return <SkeletonRows />;
  }

  if (lage.fas === "ejAktiverad") {
    return <EjAktiverad yta="Företag" />;
  }

  if (lage.fas === "fel") {
    return (
      <div className="flex items-start gap-3 border-y border-ochre/40 bg-ochre/10 px-4 py-4">
        <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-ochre" aria-hidden />
        <div className="min-w-0">
          <p className="text-sm font-medium text-ink">Bolagen kunde inte hämtas</p>
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

  if (!lage.prospekt.length) {
    return (
      <EmptyState
        title="Inga bolag ännu"
        body="Beskriv vilka ni söker i formuläret ovan och starta en körning. Bolagen som agenten hittar hamnar här — listan är tom tills den har hittat några riktiga."
      />
    );
  }

  return (
    <>
      {/* Tabell från md och upp, kort under. Sex kolumner krympta till 375px
          blir ~40px styck och därmed oläsliga — se DESIGN.md App-familjen. */}
      <div className="hidden overflow-x-auto border-y border-ink/15 md:block">
        <table className="w-full min-w-[900px] border-collapse text-[15px]">
          <thead>
            <tr className="border-b border-ink/15 text-left">
              {/* Bara SISTA kolumnen saknar högerpadding. Villkoret var `i >= 4`,
                  vilket tog bort luften även från Score — och eftersom både
                  Score och Status är högerställda skrevs de ihop till
                  "84RESEARCH PÅGÅR". Syns i en skärmbild, inte i ett test som
                  läser textinnehåll. */}
              {["Bolag", "Segment", "Kontakt", "Signal", "Score", "Status"].map((rubrik, i, alla) => (
                <th
                  key={rubrik}
                  scope="col"
                  className={cn(
                    "kicker py-4 font-medium text-mineral",
                    i >= 4 ? "text-right" : "",
                    i < alla.length - 1 ? "pr-6" : ""
                  )}
                >
                  {rubrik}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-ink/15">
            {lage.prospekt.map((p) => (
              <tr key={p.id} className="transition hover:bg-paper2/60">
                <th scope="row" className="py-5 pr-6 text-left font-normal">
                  {/* Ingen länk i demon. Bolagssidan ligger under /dashboard,
                      alltså bakom inloggningen — en besökare som klickar hade
                      mötts av en inloggningsruta mitt i en demo. */}
                  {demo ? (
                    <span className="text-[1.0625rem] font-semibold tracking-[-0.01em]">
                      {p.company_name}
                    </span>
                  ) : (
                    <Link
                      href={vag(`/dashboard/companies/${p.id}`)}
                      className="focus-ring text-[1.0625rem] font-semibold tracking-[-0.01em]"
                    >
                      {p.company_name}
                    </Link>
                  )}
                  {p.website ? <p className="mt-1 text-sm text-ink/55">{p.website}</p> : null}
                </th>
                <td className="kicker py-5 pr-6 text-mineral">{segment(p)}</td>
                <td className="py-5 pr-6">
                  <p className="text-[15px]">{p.contact_name ?? "—"}</p>
                  {p.contact_email ? (
                    <p className="mt-1 break-all text-sm text-ink/55">{p.contact_email}</p>
                  ) : null}
                </td>
                <td className="py-5 pr-6 text-[15px] leading-6 text-ink/72">{signal(p)}</td>
                <td className="num py-5 pr-6 text-right text-[1.0625rem] font-semibold tabular-nums">
                  {poang(p)}
                </td>
                <td className="py-5 text-right whitespace-nowrap">
                  <StatusOrd status={p.status} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <ul className="space-y-2 md:hidden">
        {lage.prospekt.map((p) => (
          <li key={p.id} className="rounded-input border border-ink/15 px-4 py-3">
            <div className="flex items-baseline justify-between gap-3">
              {demo ? (
                <span className="min-w-0 text-[15px] font-semibold tracking-[-0.01em]">
                  {p.company_name}
                </span>
              ) : (
                <Link
                  href={vag(`/dashboard/companies/${p.id}`)}
                  className="focus-ring min-w-0 text-[15px] font-semibold tracking-[-0.01em]"
                >
                  {p.company_name}
                </Link>
              )}
              <span className="num shrink-0 text-[15px] font-semibold tabular-nums">{poang(p)}</span>
            </div>
            <p className="kicker mt-1 text-mineral">{segment(p)}</p>
            <p className="mt-2 text-sm leading-6 text-ink/72">{signal(p)}</p>
            <div className="mt-2 flex flex-wrap items-baseline justify-between gap-x-3 gap-y-1">
              <span className="text-sm text-ink/60">{p.contact_name ?? "Ingen kontakt"}</span>
              <StatusOrd status={p.status} />
            </div>
          </li>
        ))}
      </ul>
    </>
  );
}

function StatusOrd({ status }: Readonly<{ status: string }>) {
  return (
    <span className={`kicker ${AKTIV_STATUS.has(status) ? "text-ochre" : "text-mineral"}`}>
      {STATUS_ETIKETT[status] ?? status}
    </span>
  );
}
