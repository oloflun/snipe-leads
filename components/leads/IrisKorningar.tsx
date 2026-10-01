"use client";

import Link from "next/link";
import { usePathname, useSearchParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { Cell, Nyckeltal, Tabell, Tomt, btnSecondary, meta, tabellRad } from "@/components/ui";
import { felmeddelande, readJsonBody } from "@/lib/http/json";
import { cn } from "@/lib/utils";

/**
 * Körningar — det kunden kan följa, lämna och återvända till.
 *
 * ## Varför vyn finns
 *
 * Anton startade en Iris-körning 2026-09-30, lämnade sidan, och när han kom
 * tillbaka fanns inget spår: inga nya leads, ingen felorsak, ingen lista.
 * Motorns tillstånd bodde i Redis (TTL en timme) och i körformulärets
 * React-state. Sedan migration 080 (INV-JOB-003) skriver motorn tillståndet
 * till liggaren efter varje steg, och den här vyn läser därifrån:
 * `GET /leads/korningar` (listan) och `GET /leads/korningar/{id}` (en).
 *
 * En pågående körning pollas var tredje sekund tills den säger `klar`.
 * Allt annat är statiskt tills användaren laddar om.
 */

type Tratt = { namn: string; steg: string; skal: string; belagg?: string | null };
type Jobb = { job_id: string; prospect_id?: string; company_name?: string | null };

export type Korning = {
  mal: number;
  levererade: number;
  undersokta: number;
  pagaende: number;
  rundor?: number;
  tak?: number;
  klar: boolean;
  slut_orsak?: string | null;
  flaskhals?: string | null;
  sammanfattning?: string | null;
  scope?: string;
  tratt?: Tratt[];
  jobs?: Jobb[];
};

export type KorningsRad = {
  job_id: string;
  status: "queued" | "processing" | "completed" | "failed";
  scope: "batch" | "lista";
  is_test: boolean;
  created_at: string | null;
  updated_at: string | null;
  completed_at: string | null;
  error: string | null;
  korning: Korning | null;
};

const STATUS_ETIKETT: Record<KorningsRad["status"], string> = {
  queued: "Köad",
  processing: "Pågår",
  completed: "Klar",
  failed: "Misslyckades"
};

/** Motorns slutorsaker (app/leads/korning.py) i kundens ord. */
const SLUT_ETIKETT: Record<string, string> = {
  klar: "Målet nått",
  tak: "Taket nått: fyra gånger så många bolag undersökta som beställda",
  slut_pa_kandidater: "Inga fler bolag att pröva i målgruppen",
  sokningen_foll: "Sökningen gick inte att genomföra",
  budget: "Dagens budget för körningar är slut"
};

function nar(iso: string | null): string {
  if (!iso) return "–";
  return new Date(iso).toLocaleString("sv-SE", { dateStyle: "short", timeStyle: "short" });
}

function typ(rad: KorningsRad): string {
  if (rad.scope === "lista") return "Leadslista";
  if (!rad.korning) return "Egna bolag";
  return rad.korning.scope === "research_and_draft" ? "Iris · research och utkast" : "Iris · research";
}

/** Pågår? Både liggarens status och motorns eget `klar` räknas: raden kan
 *  stå i 'completed' från sökjobbet medan motorn fortfarande fyller på. */
function pagar(rad: KorningsRad): boolean {
  if (rad.status === "queued" || rad.status === "processing") return true;
  return Boolean(rad.korning && !rad.korning.klar && rad.status !== "failed");
}

export function IrisKorningar() {
  const pathname = usePathname() ?? "/dashboard/iris/korningar";
  const sok = useSearchParams();
  // Samma vy under /dashboard, /admin och /demo: Bolag-länken följer basen.
  const bas = pathname.replace(/\/iris(\/.*)?$/, "/iris");
  const [rader, setRader] = useState<KorningsRad[] | null>(null);
  const [fel, setFel] = useState<string | null>(null);
  const [oppen, setOppen] = useState<string | null>(sok?.get("id") ?? null);

  const hamta = useCallback(async () => {
    try {
      const response = await fetch("/api/snajp-support/leads/korningar?limit=30", { cache: "no-store" });
      const kropp = await readJsonBody<{ korningar?: KorningsRad[]; detail?: string }>(response);
      if (!response.ok || !kropp?.korningar) {
        setFel(kropp?.detail ?? "Körningarna gick inte att hämta.");
        return;
      }
      setFel(null);
      setRader(kropp.korningar);
    } catch (cause) {
      setFel(felmeddelande(cause));
    }
  }, []);

  useEffect(() => {
    void hamta();
  }, [hamta]);

  // Poll bara när något pågår. Ett intervall utan pågående körning är bara
  // trafik.
  const nagotPagar = (rader ?? []).some(pagar);
  useEffect(() => {
    if (!nagotPagar) return;
    const id = window.setInterval(() => void hamta(), 3000);
    return () => window.clearInterval(id);
  }, [nagotPagar, hamta]);

  // Körformuläret och Bolag-listan lyssnar på samma händelse.
  useEffect(() => {
    const lyssnare = () => void hamta();
    window.addEventListener("snipra:leads-korning-steg", lyssnare);
    window.addEventListener("snipra:leads-korning-klar", lyssnare);
    return () => {
      window.removeEventListener("snipra:leads-korning-steg", lyssnare);
      window.removeEventListener("snipra:leads-korning-klar", lyssnare);
    };
  }, [hamta]);

  if (fel) {
    return (
      <p role="alert" className="text-[15px] text-danger">
        {fel}
      </p>
    );
  }
  if (rader === null) {
    return <p className={meta}>Hämtar körningar…</p>;
  }
  if (rader.length === 0) {
    return (
      <Tomt
        action={
          <Link href={bas} className={btnSecondary}>
            Till Bolag
          </Link>
        }
      >
        Inga körningar än. Starta en under Bolag, så syns den här med förlopp och resultat.
      </Tomt>
    );
  }

  const aktiv = rader.find(pagar) ?? null;

  return (
    <div className="space-y-10">
      {aktiv ? <Pagaende rad={aktiv} /> : null}

      <Tabell
        ariaLabel="Körningar"
        kolumner={[
          { rubrik: "Startad", bredd: "16%" },
          { rubrik: "Typ", bredd: "22%" },
          { rubrik: "Beställt", bredd: "10%", hoger: true },
          { rubrik: "Leads · undersökta", bredd: "16%", hoger: true },
          { rubrik: "Status", bredd: "12%" },
          { rubrik: "Utfall" }
        ]}
      >
        {rader.map((rad) => {
          const k = rad.korning;
          const arOppen = oppen === rad.job_id;
          return (
            <RadMedDetalj
              key={rad.job_id}
              rad={rad}
              bas={bas}
              oppen={arOppen}
              onToggle={() => setOppen(arOppen ? null : rad.job_id)}
            >
              <Cell>{typ(rad)}</Cell>
              <Cell hoger>{k ? k.mal : "–"}</Cell>
              <Cell hoger>
                {k ? (
                  <>
                    <span className="num tabular-nums">{k.levererade}</span>
                    <span className={meta}> · {k.undersokta}</span>
                  </>
                ) : (
                  "–"
                )}
              </Cell>
              <Cell>
                <span
                  className={cn(
                    "inline-flex items-center gap-1.5",
                    rad.status === "failed" ? "text-danger" : pagar(rad) ? "text-warning" : "text-ink"
                  )}
                >
                  <span
                    aria-hidden
                    className={cn(
                      "h-1.5 w-1.5 rounded-full",
                      rad.status === "failed" ? "bg-danger" : pagar(rad) ? "bg-ochre" : "bg-moss"
                    )}
                  />
                  {pagar(rad) ? "Pågår" : STATUS_ETIKETT[rad.status]}
                </span>
              </Cell>
              <Cell className="text-ink-muted">
                {rad.error
                  ? rad.error
                  : k?.klar
                    ? (k.sammanfattning ?? SLUT_ETIKETT[k.slut_orsak ?? ""] ?? "Klar")
                    : k
                      ? k.pagaende
                        ? "Researchar nästa bolag"
                        : "Letar fler bolag"
                      : rad.scope === "lista"
                        ? "Se Bolag › Listor"
                        : "–"}
              </Cell>
            </RadMedDetalj>
          );
        })}
      </Tabell>
    </div>
  );
}

function Pagaende({ rad }: Readonly<{ rad: KorningsRad }>) {
  const k = rad.korning;
  if (!k) {
    return (
      <p className="text-[15px] text-ink-muted" role="status">
        En körning pågår sedan {nar(rad.created_at)}.
      </p>
    );
  }
  return (
    <div role="status" aria-live="polite">
      <Nyckeltal
        poster={[
          { etikett: "Leads klara", varde: `${k.levererade} av ${k.mal}` },
          { etikett: "Bolag undersökta", varde: k.undersokta, notis: k.tak ? `tak ${k.tak}` : undefined },
          { etikett: "Bortvalda", varde: (k.tratt ?? []).length },
          {
            etikett: "Just nu",
            varde: k.pagaende ? "Researchar" : "Letar",
            notis: k.pagaende ? `${k.pagaende} bolag under research` : `sökrunda ${(k.rundor ?? 0) + 1}`
          }
        ]}
      />
      <p className={cn(meta, "mt-3")}>
        Körningen fortsätter på servern. Du kan lämna sidan och komma tillbaka hit.
      </p>
    </div>
  );
}

/**
 * En rad som fälls ut till sin detalj: levererade bolag med länk, tratten rad
 * för rad, och felorsaken. Tangentbordet når en RIKTIG knapp i radhuvudet
 * (datumet), inte en fokuserbar `<tr>`: en tabellrad med tabIndex och
 * tangentlyssnare läses som "rad", aldrig som "knapp, hopfälld", och
 * skärmläsaren vet då inte att den går att öppna. Musen får dessutom
 * klicka var som helst på raden.
 */
function RadMedDetalj({
  rad,
  bas,
  oppen,
  onToggle,
  children
}: Readonly<{
  rad: KorningsRad;
  bas: string;
  oppen: boolean;
  onToggle: () => void;
  children: React.ReactNode;
}>) {
  const k = rad.korning;
  const kolumner = 6;
  return (
    <>
      <tr className={cn(tabellRad, "cursor-pointer")} onClick={onToggle}>
        <Cell titel>
          <button
            type="button"
            aria-expanded={oppen}
            aria-controls={`korning-${rad.job_id}`}
            onClick={(e) => {
              e.stopPropagation();
              onToggle();
            }}
            className="focus-ring -mx-1 inline-flex min-h-11 items-center rounded-input px-1 text-left"
          >
            <span className="num tabular-nums">{nar(rad.created_at)}</span>
            {rad.is_test ? <span className={cn(meta, "ml-2")}>test</span> : null}
            <span className="sr-only">{oppen ? ", dölj detaljer" : ", visa detaljer"}</span>
          </button>
        </Cell>
        {children}
      </tr>
      {oppen ? (
        <tr id={`korning-${rad.job_id}`}>
          <td colSpan={kolumner} className="bg-paper2/60 px-4 py-5">
            <div className="grid gap-8 md:grid-cols-2">
              <div>
                <h3 className="text-[1.0625rem] font-semibold">Levererade bolag</h3>
                {k?.jobs?.length ? (
                  <ul className="mt-3 divide-y divide-ink/12 border-y border-ink/15">
                    {k.jobs.map((j) => (
                      <li key={j.job_id} className="flex items-center justify-between gap-3 py-2.5">
                        <span className="min-w-0 truncate">{j.company_name ?? j.prospect_id ?? j.job_id}</span>
                        {j.prospect_id ? (
                          <Link href={bas} className="shrink-0 text-[13px] underline underline-offset-4">
                            Till Bolag
                          </Link>
                        ) : null}
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className={cn(meta, "mt-3")}>
                    {rad.scope === "lista" ? "Raderna finns under Bolag › Listor." : "Inga bolag levererade."}
                  </p>
                )}
                {rad.error ? (
                  <p className="mt-4 text-[15px] text-danger" role="alert">
                    {rad.error}
                  </p>
                ) : null}
                {k?.klar && k.slut_orsak ? (
                  <p className={cn(meta, "mt-4")}>{SLUT_ETIKETT[k.slut_orsak] ?? k.slut_orsak}</p>
                ) : null}
              </div>
              <div>
                <h3 className="text-[1.0625rem] font-semibold">
                  Bortvalda <span className={cn(meta, "font-normal")}>{(k?.tratt ?? []).length}</span>
                </h3>
                {k?.tratt?.length ? (
                  <ul className="mt-3 divide-y divide-ink/12 border-y border-ink/15">
                    {k.tratt.map((t, i) => (
                      <li key={`${t.namn}-${i}`} className="py-2.5">
                        <div className="flex items-baseline justify-between gap-3">
                          <span className="min-w-0 truncate font-medium">{t.namn}</span>
                          <span className={cn(meta, "shrink-0")}>{t.steg}</span>
                        </div>
                        <p className="mt-0.5 text-[0.9375rem] text-ink-muted">{t.skal}</p>
                        {t.belagg ? <p className={cn(meta, "mt-0.5 italic")}>{t.belagg}</p> : null}
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className={cn(meta, "mt-3")}>Inget bolag valdes bort.</p>
                )}
              </div>
            </div>
            <p className={cn(meta, "mt-5 font-mono text-[0.8125rem]")}>
              {rad.job_id} · uppdaterad {nar(rad.updated_at)}
            </p>
          </td>
        </tr>
      ) : null}
    </>
  );
}
