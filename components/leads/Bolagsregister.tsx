"use client";

import { AlertTriangle } from "lucide-react";
import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { useArbetsvag } from "@/components/AppShell";
import { kriterier } from "@/lib/prospekt";
import { EmptyState, SkeletonRows } from "@/components/ui";
import { EjAktiverad, arEjAktiverad } from "@/components/EjAktiverad";
import { demoOversiktSvar } from "@/lib/demo/oversikt";
import { felmeddelande, readJsonBody } from "@/lib/http/json";
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
  /** 'example' för de sex påhittade bolagen (se exempelbolag.py). Redan i svaret. */
  origin?: string | null;
  ort: string | null;
  sni: string | null;
  website: string | null;
  orgnr: string | null;
  score_total: number | null;
  icp_fit: number | null;
  qualified: boolean | null;
  disqualifiers: string[] | null;
  // Avsiktligt otypad: fältet HAR nått hit som en sträng. Se lib/prospekt.ts.
  score_breakdown: unknown;
};

type Lage =
  | { fas: "laddar" }
  | { fas: "ejAktiverad" }
  | { fas: "fel"; meddelande: string }
  | { fas: "klar"; prospekt: Prospekt[] };

/** Utfallet av ETT befordran-försök — visas rad för rad efter "Flytta över valda". */
type Utfallsrad = {
  id: string;
  company_name: string;
  ok: boolean;
  /** Bara satt när ok=false. Backendens 422-lista, redan på svenska. */
  saknas?: string[];
};

/** Svaret /befordra ger, tolkat oavsett statuskod (se readJsonBody). */
type BefordraSvar = {
  detail?: { message?: string; saknas?: string[] } | string;
};

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
  const träff = kriterier(p.score_breakdown).find(
    (k) => k.motivering && k.utfall !== "saknas"
  );
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

  const hamta = useCallback(async (tyst = false) => {
    if (!tyst) setLage({ fas: "laddar" });

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

  useEffect(() => {
    const lyssna = () => {
      void hamta(true);
    };
    window.addEventListener("snipra:leads-korning-klar", lyssna);
    return () => window.removeEventListener("snipra:leads-korning-klar", lyssna);
  }, [hamta]);

  // Fas 3 §4: kryssrutor + "Flytta över valda". Bara i den riktiga vyn — demot
  // visar en statisk ögonblicksbild (demoOversiktSvar) utan riktiga id:n, och
  // ett POST mot ett påhittat id hade bara gett 404 utan att kunden lärt sig
  // något om funktionen.
  const [valda, setValda] = useState<Set<string>>(new Set());
  const [flyttar, setFlyttar] = useState(false);
  const [utfall, setUtfall] = useState<Utfallsrad[] | null>(null);
  const [ifyllnad, setIfyllnad] = useState<
    Record<string, { orgnr: string; website: string; contact_email: string }>
  >({});

  // Fas 2 §3, 2.4-UI: testkörningar döljs som default. Exempelbolag räknas
  // INTE hit — de är produktens tomläge och ska synas även med växeln av.
  const [visaTest, setVisaTest] = useState(false);

  const vaxlaVal = useCallback((id: string) => {
    setValda((forra) => {
      const nasta = new Set(forra);
      if (nasta.has(id)) {
        nasta.delete(id);
      } else {
        nasta.add(id);
      }
      return nasta;
    });
  }, []);

  const flyttaOverValda = useCallback(async (ids?: Set<string>) => {
    if (lage.fas !== "klar") return;
    // Ett snapshot av VILKA som är markerade just nu — valda kan ändras under
    // await-kedjan om kunden hinner klicka mer, men resultatlistan ska svara
    // på det urval knappen faktiskt kördes med.
    const markering = ids ?? valda;
    const kandidater = lage.prospekt.filter((p) => markering.has(p.id));
    if (!kandidater.length) return;

    setFlyttar(true);
    setUtfall(null);
    try {
      const resultat: Utfallsrad[] = [];
      for (const p of kandidater) {
        if (p.origin !== "test" && p.origin !== "example") {
          // Redan i kundens riktiga lista — hoppas över TYST, ingen rad i
          // resultatlistan. En markerad-men-redan-manuell rad är inget fel.
          continue;
        }
        try {
          const extra = ifyllnad[p.id];
          const response = await fetch(`/api/snajp-support/leads/prospects/${p.id}/befordra`, {
            method: "POST",
            headers: extra ? { "Content-Type": "application/json" } : undefined,
            body: extra
              ? JSON.stringify({
                  orgnr: extra.orgnr || undefined,
                  website: extra.website || undefined,
                  contact_email: extra.contact_email || undefined
                })
              : undefined
          });
          if (response.ok) {
            resultat.push({ id: p.id, company_name: p.company_name, ok: true });
            continue;
          }
          const kropp = await readJsonBody<BefordraSvar>(response).catch(() => null);
          const detalj = kropp?.detail;
          const saknas =
            detalj && typeof detalj === "object" && Array.isArray(detalj.saknas)
              ? detalj.saknas
              : [];
          resultat.push({
            id: p.id,
            company_name: p.company_name,
            ok: false,
            saknas: saknas.length
              ? saknas
              : [
                  typeof detalj === "string"
                    ? detalj
                    : `Kunde inte flytta över (status ${response.status}).`
                ]
          });
        } catch (error) {
          resultat.push({
            id: p.id,
            company_name: p.company_name,
            ok: false,
            saknas: [felmeddelande(error)]
          });
        }
      }
      setUtfall(resultat);
      setValda(new Set());
      await hamta();
    } finally {
      setFlyttar(false);
    }
  }, [lage, valda, hamta, ifyllnad]);

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

  // Fas 2 §3, 2.4-UI: testkörningar döljs som default, exempelbolag aldrig.
  const antalTest = lage.prospekt.filter((p) => p.origin === "test").length;
  const synliga = lage.prospekt.filter((p) => visaTest || p.origin !== "test");

  return (
    <>
      {(antalTest > 0 || (!demo && valda.size > 0)) && (
        <div className="mb-5 flex flex-wrap items-center justify-between gap-3">
          {!demo && valda.size > 0 ? (
            <button
              type="button"
              disabled={flyttar}
              onClick={() => void flyttaOverValda()}
              className="border border-ink px-4 py-2 font-mono text-[12px] uppercase tracking-[0.18em] transition hover:bg-ink hover:text-paper disabled:opacity-60"
            >
              {flyttar ? "Flyttar..." : `Flytta över valda (${valda.size})`}
            </button>
          ) : (
            <span />
          )}
          {antalTest > 0 ? (
            // "Diskret" — text i kicker/mineral, inte en stor inställningsväxel.
            // Den hör hemma i arbetsflödet, inte i en inställningsyta.
            <button
              type="button"
              role="switch"
              aria-checked={visaTest}
              onClick={() => setVisaTest((v) => !v)}
              className="focus-ring kicker text-mineral transition hover:text-ochre"
            >
              {visaTest ? "Dölj testkörningar" : `Visa testkörningar (${antalTest})`}
            </button>
          ) : null}
        </div>
      )}

      {utfall && utfall.length > 0 ? (
        <ul className="mb-5 space-y-3 border-y border-ink/15 py-4">
          {utfall.map((rad) => (
            <li key={rad.id} className="text-sm leading-6">
              <span className="font-medium text-ink">{rad.company_name}</span>{" "}
              {rad.ok ? (
                <span className="text-moss">flyttades över till den riktiga listan.</span>
              ) : (
                <span className="text-danger">
                  kunde inte flyttas över: {rad.saknas?.join(" ")}
                </span>
              )}
              {!rad.ok ? (
                <Ifyllnad
                  id={rad.id}
                  varden={ifyllnad[rad.id] ?? { orgnr: "", website: "", contact_email: "" }}
                  disabled={flyttar}
                  onChange={(varden) =>
                    setIfyllnad((forra) => ({ ...forra, [rad.id]: varden }))
                  }
                  onSubmit={() => void flyttaOverValda(new Set([rad.id]))}
                />
              ) : null}
            </li>
          ))}
        </ul>
      ) : null}

      {synliga.length === 0 ? (
        <p className="border-y border-ink/15 py-6 text-[15px] text-ink/60">
          Alla {antalTest} bolag just nu är testkörningar och är dolda. Slå på "Visa
          testkörningar" ovan för att se dem.
        </p>
      ) : (
        <>
          {/* Tabell från md och upp, kort under. Sex kolumner krympta till 375px
              blir ~40px styck och därmed oläsliga — se DESIGN.md App-familjen. */}
          <div className="hidden overflow-x-auto border-y border-ink/15 md:block">
            <table className="w-full min-w-[900px] border-collapse text-[15px]">
              <thead>
                <tr className="border-b border-ink/15 text-left">
                  {/* Fas 3 §4: kryssrutekolumnen har ingen rubriktext — bara i den
                      riktiga vyn, av samma skäl som knappen nedan. */}
                  {!demo ? (
                    <th scope="col" className="w-10 py-4 pr-3">
                      <span className="sr-only">Välj</span>
                    </th>
                  ) : null}
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
                {synliga.map((p) => (
                  <tr key={p.id} className="transition hover:bg-paper2/60">
                    {!demo ? (
                      <td className="py-5 pr-3">
                        <input
                          type="checkbox"
                          checked={valda.has(p.id)}
                          onChange={() => vaxlaVal(p.id)}
                          aria-label={`Välj ${p.company_name}`}
                          className="h-4 w-4 accent-ochre"
                        />
                      </td>
                    ) : null}
                    <th scope="row" className="py-5 pr-6 text-left font-normal">
                      {/* Ingen länk i demon. Bolagssidan ligger under /dashboard,
                          alltså bakom inloggningen — en besökare som klickar hade
                          mötts av en inloggningsruta mitt i en demo. */}
                      <div className="flex flex-wrap items-baseline gap-2">
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
                        {/* Samma märkning som StatusOrd nedan — kicker/mineral, ingen
                            egen badgestil. Ett påhittat bolag ska inte gå att ta för
                            en riktig AI-körning. */}
                        {p.origin === "example" ? <span className="kicker text-mineral">Exempel</span> : null}
                        {p.origin === "test" ? <span className="kicker text-mineral">Test</span> : null}
                      </div>
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
            {synliga.map((p) => (
              <li key={p.id} className="rounded-input border border-ink/15 px-4 py-3">
                <div className="flex items-baseline justify-between gap-3">
                  <div className="flex min-w-0 flex-wrap items-center gap-2">
                    {!demo ? (
                      <input
                        type="checkbox"
                        checked={valda.has(p.id)}
                        onChange={() => vaxlaVal(p.id)}
                        aria-label={`Välj ${p.company_name}`}
                        className="h-4 w-4 shrink-0 accent-ochre"
                      />
                    ) : null}
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
                    {p.origin === "example" ? <span className="kicker text-mineral">Exempel</span> : null}
                  </div>
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
      )}
    </>
  );
}

function Ifyllnad({
  id,
  varden,
  disabled,
  onChange,
  onSubmit
}: Readonly<{
  id: string;
  varden: { orgnr: string; website: string; contact_email: string };
  disabled: boolean;
  onChange: (varden: { orgnr: string; website: string; contact_email: string }) => void;
  onSubmit: () => void;
}>) {
  return (
    <form
      className="mt-3 grid gap-2 sm:grid-cols-3"
      onSubmit={(event) => {
        event.preventDefault();
        onSubmit();
      }}
    >
      <label className="block text-[12px] text-ink/60">
        Organisationsnummer
        <input
          name={`${id}-orgnr`}
          value={varden.orgnr}
          onChange={(event) => onChange({ ...varden, orgnr: event.target.value })}
          placeholder="556824-9022"
          className="focus-ring mt-1 block min-h-11 w-full rounded-input bg-paper2 px-3 text-sm text-ink"
        />
      </label>
      <label className="block text-[12px] text-ink/60">
        Webbplats
        <input
          name={`${id}-website`}
          value={varden.website}
          onChange={(event) => onChange({ ...varden, website: event.target.value })}
          placeholder="https://bolaget.se"
          className="focus-ring mt-1 block min-h-11 w-full rounded-input bg-paper2 px-3 text-sm text-ink"
        />
      </label>
      <label className="block text-[12px] text-ink/60">
        E-post
        <input
          name={`${id}-email`}
          value={varden.contact_email}
          onChange={(event) => onChange({ ...varden, contact_email: event.target.value })}
          placeholder="info@bolaget.se"
          className="focus-ring mt-1 block min-h-11 w-full rounded-input bg-paper2 px-3 text-sm text-ink"
        />
      </label>
      <div className="sm:col-span-3">
        <button
          type="submit"
          disabled={disabled}
          className="border border-ink px-4 py-2 font-mono text-[12px] uppercase tracking-[0.18em] transition hover:bg-ink hover:text-paper disabled:opacity-60"
        >
          Spara och flytta
        </button>
      </div>
    </form>
  );
}

function StatusOrd({ status }: Readonly<{ status: string }>) {
  return (
    <span className={`kicker ${AKTIV_STATUS.has(status) ? "text-ochre" : "text-mineral"}`}>
      {STATUS_ETIKETT[status] ?? status}
    </span>
  );
}
