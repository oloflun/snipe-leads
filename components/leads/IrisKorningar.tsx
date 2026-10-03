"use client";

import Link from "next/link";
import { usePathname, useSearchParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { Cell, Nyckeltal, Tabell, Tomt, btnSecondary, meta, tabellRad } from "@/components/ui";
import { felmeddelande, readJsonBody } from "@/lib/http/json";
import { useLocale, type Locale, type Localized } from "@/lib/i18n";
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

const T = {
  hamtar: { sv: "Hämtar körningar…", en: "Loading runs…" },
  hamtaFel: { sv: "Körningarna gick inte att hämta.", en: "The runs could not be loaded." },
  tillBolag: { sv: "Till Leads", en: "To Leads" },
  tomt: {
    sv: "Inga körningar än. Starta en under Leads, så syns den här med förlopp och resultat.",
    en: "No runs yet. Start one under Leads and it shows up here with progress and results."
  },
  tabell: { sv: "Körningar", en: "Runs" },
  kolStartad: { sv: "Startad", en: "Started" },
  kolTyp: { sv: "Typ", en: "Type" },
  kolBestallt: { sv: "Beställt", en: "Ordered" },
  kolLeads: { sv: "Leads · undersökta", en: "Leads · researched" },
  kolStatus: { sv: "Status", en: "Status" },
  kolUtfall: { sv: "Utfall", en: "Outcome" },
  pagar: { sv: "Pågår", en: "Running" },
  researcharNasta: { sv: "Researchar nästa bolag", en: "Researching the next company" },
  letarFler: { sv: "Letar fler bolag", en: "Looking for more companies" },
  seListor: { sv: "Se Leads › Listor", en: "See Leads › Lists" },
  klar: { sv: "Klar", en: "Done" },
  leadsKlara: { sv: "Leads klara", en: "Leads done" },
  bolagUndersokta: { sv: "Bolag undersökta", en: "Companies researched" },
  bortvalda: { sv: "Bortvalda", en: "Dropped" },
  justNu: { sv: "Just nu", en: "Right now" },
  researchar: { sv: "Researchar", en: "Researching" },
  letar: { sv: "Letar", en: "Searching" },
  tak: { sv: "tak", en: "cap" },
  underResearch: { sv: "bolag under research", en: "companies in research" },
  sokrunda: { sv: "sökrunda", en: "search round" },
  fortsatter: {
    sv: "Körningen fortsätter på servern. Du kan lämna sidan och komma tillbaka hit.",
    en: "The run continues on the server. You can leave this page and come back."
  },
  test: { sv: "test", en: "test" },
  doljDetaljer: { sv: ", dölj detaljer", en: ", hide details" },
  visaDetaljer: { sv: ", visa detaljer", en: ", show details" },
  undersoktaBolag: { sv: "Undersökta bolag", en: "Companies researched" },
  raderUnderListor: { sv: "Raderna finns under Leads › Listor.", en: "The rows are under Leads › Lists." },
  ingaUndersokta: { sv: "Inga bolag undersökta.", en: "No companies researched." },
  ingetBortvalt: { sv: "Inget bolag valdes bort.", en: "No company was dropped." },
  uppdaterad: { sv: "uppdaterad", en: "updated" },
  av: { sv: "av", en: "of" }
} satisfies Record<string, Localized>;

const STATUS_ETIKETT: Record<KorningsRad["status"], Localized> = {
  queued: { sv: "Köad", en: "Queued" },
  processing: { sv: "Pågår", en: "Running" },
  completed: { sv: "Klar", en: "Done" },
  failed: { sv: "Misslyckades", en: "Failed" }
};

/** Motorns slutorsaker (app/leads/korning.py) i kundens ord. */
const SLUT_ETIKETT: Record<string, Localized> = {
  klar: { sv: "Målet nått", en: "Target reached" },
  tak: {
    sv: "Taket nått: fyra gånger så många bolag undersökta som beställda",
    en: "Cap reached: four times as many companies researched as ordered"
  },
  slut_pa_kandidater: { sv: "Inga fler bolag att pröva i målgruppen", en: "No more companies to try in the target group" },
  sokningen_foll: { sv: "Sökningen gick inte att genomföra", en: "The search could not be completed" },
  budget: { sv: "Dagens budget för körningar är slut", en: "Today's budget for runs is used up" }
};

function nar(iso: string | null, locale: Locale): string {
  if (!iso) return "–";
  return new Date(iso).toLocaleString(locale === "en" ? "en-GB" : "sv-SE", { dateStyle: "short", timeStyle: "short" });
}

function typ(rad: KorningsRad): Localized {
  if (rad.scope === "lista") return { sv: "Leadslista", en: "Lead list" };
  if (!rad.korning) return { sv: "Egna bolag", en: "Own companies" };
  return rad.korning.scope === "research_and_draft"
    ? { sv: "Iris · research och utkast", en: "Iris · research and drafts" }
    : { sv: "Iris · research", en: "Iris · research" };
}

/** Pågår? Både liggarens status och motorns eget `klar` räknas: raden kan
 *  stå i 'completed' från sökjobbet medan motorn fortfarande fyller på. */
function pagar(rad: KorningsRad): boolean {
  if (rad.status === "queued" || rad.status === "processing") return true;
  return Boolean(rad.korning && !rad.korning.klar && rad.status !== "failed");
}

export function IrisKorningar() {
  const { locale, text } = useLocale();
  const pathname = usePathname() ?? "/dashboard/aktivitet";
  const sok = useSearchParams();
  // Samma vy under /dashboard och /admin: Leads-länken följer basen. Vyn
  // renderas i Aktivitet sedan Snajp Suite (2026-10-03).
  const bas = pathname.replace(/\/(aktivitet|iris)(\/.*)?$/, "/leads");
  const [rader, setRader] = useState<KorningsRad[] | null>(null);
  const [fel, setFel] = useState<string | null>(null);
  const [oppen, setOppen] = useState<string | null>(sok?.get("id") ?? null);
  // Stoppad = sessionen är borta (401/403) eller vyn saknas (404): att polla
  // vidare var tredje sekund ger bara samma svar.
  const [stoppad, setStoppad] = useState(false);

  const hamta = useCallback(async () => {
    try {
      const response = await fetch("/api/snajp-support/leads/korningar?limit=30", { cache: "no-store" });
      const kropp = await readJsonBody<{ korningar?: KorningsRad[]; detail?: string }>(response);
      if (!response.ok || !kropp?.korningar) {
        if ([401, 403, 404].includes(response.status)) setStoppad(true);
        setFel(kropp?.detail ?? text(T.hamtaFel));
        return;
      }
      setFel(null);
      setRader(kropp.korningar);
    } catch (cause) {
      setFel(felmeddelande(cause));
    }
  }, [text]);

  useEffect(() => {
    void hamta();
  }, [hamta]);

  // Poll bara när något pågår, och nästa hämtning schemaläggs först när den
  // förra svarat: ett intervall överlappade sig självt vid kallstart (proxyn
  // tillåter 60 s) och kunde skriva ett äldre svar över ett nyare.
  const nagotPagar = !stoppad && (rader ?? []).some(pagar);
  useEffect(() => {
    if (!nagotPagar) return;
    let timer = 0;
    let aktiv = true;
    const varv = async () => {
      await hamta();
      if (aktiv) timer = window.setTimeout(() => void varv(), 3000);
    };
    timer = window.setTimeout(() => void varv(), 3000);
    return () => {
      aktiv = false;
      window.clearTimeout(timer);
    };
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

  if (fel && rader === null) {
    return (
      <p role="alert" className="text-[15px] text-danger">
        {fel}
      </p>
    );
  }
  if (rader === null) {
    return <p className={meta}>{text(T.hamtar)}</p>;
  }
  if (rader.length === 0) {
    return (
      <Tomt
        action={
          <Link href={bas} className={btnSecondary}>
            {text(T.tillBolag)}
          </Link>
        }
      >
        {text(T.tomt)}
      </Tomt>
    );
  }

  const aktiv = rader.find(pagar) ?? null;

  return (
    <div className="space-y-10">
      {fel ? (
        <p role="alert" className="text-[15px] text-danger">
          {fel}
        </p>
      ) : null}
      {aktiv ? <Pagaende rad={aktiv} /> : null}

      <Tabell
        ariaLabel={text(T.tabell)}
        kolumner={[
          { rubrik: text(T.kolStartad), bredd: "16%" },
          { rubrik: text(T.kolTyp), bredd: "22%" },
          { rubrik: text(T.kolBestallt), bredd: "10%", hoger: true },
          { rubrik: text(T.kolLeads), bredd: "16%", hoger: true },
          { rubrik: text(T.kolStatus), bredd: "12%" },
          { rubrik: text(T.kolUtfall) }
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
              <Cell>{text(typ(rad))}</Cell>
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
                  {pagar(rad) ? text(T.pagar) : text(STATUS_ETIKETT[rad.status])}
                </span>
              </Cell>
              <Cell className="text-ink-muted">
                {rad.error
                  ? rad.error
                  : k?.klar
                    ? (k.sammanfattning ?? (SLUT_ETIKETT[k.slut_orsak ?? ""] ? text(SLUT_ETIKETT[k.slut_orsak ?? ""]) : text(T.klar)))
                    : k
                      ? k.pagaende
                        ? text(T.researcharNasta)
                        : text(T.letarFler)
                      : rad.scope === "lista"
                        ? text(T.seListor)
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
  const { locale, text } = useLocale();
  const k = rad.korning;
  if (!k) {
    return (
      <p className="text-[15px] text-ink-muted" role="status">
        {text({
          sv: `En körning pågår sedan ${nar(rad.created_at, locale)}.`,
          en: `A run has been going since ${nar(rad.created_at, locale)}.`
        })}
      </p>
    );
  }
  return (
    <div role="status" aria-live="polite">
      <Nyckeltal
        poster={[
          { etikett: text(T.leadsKlara), varde: `${k.levererade} ${text(T.av)} ${k.mal}` },
          { etikett: text(T.bolagUndersokta), varde: k.undersokta, notis: k.tak ? `${text(T.tak)} ${k.tak}` : undefined },
          { etikett: text(T.bortvalda), varde: (k.tratt ?? []).length },
          {
            etikett: text(T.justNu),
            varde: k.pagaende ? text(T.researchar) : text(T.letar),
            notis: k.pagaende ? `${k.pagaende} ${text(T.underResearch)}` : `${text(T.sokrunda)} ${(k.rundor ?? 0) + 1}`
          }
        ]}
      />
      <p className={cn(meta, "mt-3")}>{text(T.fortsatter)}</p>
    </div>
  );
}

/**
 * En rad som fälls ut till sin detalj: undersökta bolag med länk, tratten rad
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
  const { locale, text } = useLocale();
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
            <span className="num tabular-nums">{nar(rad.created_at, locale)}</span>
            {rad.is_test ? <span className={cn(meta, "ml-2")}>{text(T.test)}</span> : null}
            <span className="sr-only">{oppen ? text(T.doljDetaljer) : text(T.visaDetaljer)}</span>
          </button>
        </Cell>
        {children}
      </tr>
      {oppen ? (
        <tr id={`korning-${rad.job_id}`}>
          <td colSpan={kolumner} className="bg-paper2/60 px-4 py-5">
            <div className="grid gap-8 md:grid-cols-2">
              <div>
                <h3 className="text-[1.0625rem] font-semibold">{text(T.undersoktaBolag)}</h3>
                {k?.jobs?.length ? (
                  <ul className="mt-3 divide-y divide-ink/12 border-y border-ink/15">
                    {k.jobs.map((j) => (
                      <li key={j.job_id} className="flex items-center justify-between gap-3 py-2.5">
                        <span className="min-w-0 truncate">{j.company_name ?? j.prospect_id ?? j.job_id}</span>
                        {j.prospect_id ? (
                          <Link href={bas} className="shrink-0 text-[13px] underline underline-offset-4">
                            {text(T.tillBolag)}
                          </Link>
                        ) : null}
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className={cn(meta, "mt-3")}>
                    {rad.scope === "lista" ? text(T.raderUnderListor) : text(T.ingaUndersokta)}
                  </p>
                )}
                {rad.error ? (
                  <p className="mt-4 text-[15px] text-danger" role="alert">
                    {rad.error}
                  </p>
                ) : null}
                {k?.klar && k.slut_orsak ? (
                  <p className={cn(meta, "mt-4")}>
                    {SLUT_ETIKETT[k.slut_orsak] ? text(SLUT_ETIKETT[k.slut_orsak]) : k.slut_orsak}
                  </p>
                ) : null}
              </div>
              <div>
                <h3 className="text-[1.0625rem] font-semibold">
                  {text(T.bortvalda)} <span className={cn(meta, "font-normal")}>{(k?.tratt ?? []).length}</span>
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
                        {t.belagg ? <p className={cn(meta, "mt-0.5")}>{t.belagg}</p> : null}
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className={cn(meta, "mt-3")}>{text(T.ingetBortvalt)}</p>
                )}
              </div>
            </div>
            <p className={cn(meta, "mt-5 font-mono text-[0.8125rem]")}>
              {rad.job_id} · {text(T.uppdaterad)} {nar(rad.updated_at, locale)}
            </p>
          </td>
        </tr>
      ) : null}
    </>
  );
}
