"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useDashboard } from "@/components/dashboard/DashboardContext";
import {
  Aktivitetsgraf,
  KpiKort,
  Munkdiagram,
  forandring,
  type Andel,
  type Kpi,
  type Vecka
} from "@/components/dashboard/OversiktPaneler";
import { CrmKundlista } from "@/components/leads/CrmKundlista";
import { IrisGranskning } from "@/components/leads/IrisGranskning";
import {
  KORNINGSSTATUS,
  korningsTyp,
  pagar,
  statusText,
  utfallston,
  type KorningsRad
} from "@/components/leads/IrisKorningar";
import { ListorUpsell } from "@/components/leads/IrisBolag";
import { LeadsTabell } from "@/components/leads/LeadsTabell";
import { LeadslistorView } from "@/components/leads/LeadslistorView";
import { SaljlistaUtforska } from "@/components/leads/Saljlista";
import { SmalKolumn } from "@/components/leads/smal";
import { btnLiten, btnSecondary, meta } from "@/components/ui";
import { demoOversiktSvar } from "@/lib/demo/oversikt";
import { readJsonBody } from "@/lib/http/json";
import { useLocale, type Localized } from "@/lib/i18n";
import { kontaktvagAv, type SuiteProspekt } from "@/lib/leads/suite";
import { STATUS_ETIKETT } from "@/lib/prospekt";
import { cn } from "@/lib/utils";

/**
 * Leads › Översikt (Sebbes beställning 2026-10-06, omgjord 2026-10-07).
 *
 *   nyckeltal som i Min arbetsyta (kort med förändring och sparkline)
 *   aktivitet per vecka · munkdiagram för status och kontaktväg
 *   de tre senaste utkasten (expanderbar, skicka direkt) · körningarna
 *   Iris-leads | listor och säljlista   (split view från 1280 px)
 *
 * Sebbe 2026-10-07: utkasten och de platta siffrorna tog all plats, och
 * leads och listor byggde på höjden. Utkasten är nu en liten ruta som visar
 * de tre senaste och fäller ut till alla; leads och listor står bredvid
 * varandra i varsin rullbar kolumn, där tabellerna visar sina kort
 * (SmalKolumn) eftersom kolumnen är smal fast fönstret är brett.
 */

const T = {
  utkastVantar: { sv: "Utkast att godkänna", en: "Drafts to approve" },
  vantarPaDig: { sv: "väntar på ditt ja", en: "waiting for your yes" },
  skickade: { sv: "Skickade mejl", en: "Emails sent" },
  svar: { sv: "Svar från leads", en: "Replies from leads" },
  nyaLeads: { sv: "Nya leads", en: "New leads" },
  aktivitet: { sv: "Aktivitet per vecka", en: "Activity per week" },
  ingenAktivitet: { sv: "Ingen aktivitet att visa än.", en: "No activity to show yet." },
  fordelning: { sv: "Fördelning", en: "Breakdown" },
  status: { sv: "Status", en: "Status" },
  kontaktvag: { sv: "Kontaktväg", en: "Contact path" },
  leadsMitt: { sv: "leads", en: "leads" },
  utkastRubrik: { sv: "Senaste utkasten", en: "Latest drafts" },
  pagaendeKorningar: { sv: "Pågående körningar", en: "Runs in progress" },
  senasteKorning: { sv: "Senaste körningen", en: "Latest run" },
  ingaKorningar: { sv: "Inga körningar än.", en: "No runs yet." },
  oppna: { sv: "Öppna", en: "Open" },
  allaKorningar: { sv: "Alla körningar", en: "All runs" },
  irisLeads: { sv: "Iris-leads", en: "Iris leads" },
  irisLeadsText: {
    sv: "Bolagen Iris researchat åt dig, med status i samma färger som säljlistan.",
    en: "The companies Iris has researched for you, with status in the same colours as the sales list."
  },
  listorRubrik: { sv: "Listor och säljlista", en: "Lists and sales list" },
  av: { sv: "av", en: "of" },
  leadsKlara: { sv: "leads klara", en: "leads done" }
} satisfies Record<string, Localized>;

const PERIOD = 4;

const KONTAKT: { id: ReturnType<typeof kontaktvagAv>; etikett: Localized; farg: string }[] = [
  { id: "bada", etikett: { sv: "Tel och mejl", en: "Phone and email" }, farg: "oklch(var(--moss))" },
  { id: "telefon", etikett: { sv: "Tel", en: "Phone" }, farg: "oklch(var(--chart-blue))" },
  { id: "mejl", etikett: { sv: "Mejl", en: "Email" }, farg: "oklch(var(--chart-ochre))" },
  { id: "saknas", etikett: { sv: "Saknas", en: "Missing" }, farg: "oklch(var(--danger))" }
];

/** Pipelinens steg i ordning: blå rampa ljust till mörkt, förlorad i grått. */
const STATUSFARG: Record<string, string> = {
  new: "oklch(var(--chart-ramp-1))",
  researching: "oklch(var(--chart-ramp-2))",
  ready: "oklch(var(--chart-ramp-3))",
  contacted: "oklch(var(--chart-ramp-4))",
  replied: "oklch(var(--chart-ramp-5))",
  meeting: "oklch(var(--chart-ramp-6))",
  won: "oklch(var(--moss))",
  lost: "oklch(var(--ink-subtle))"
};

const kort = "rounded-card border border-ink/12 bg-paper p-4 sm:p-5";

function summa(veckor: Vecka[], nyckel: keyof Vecka, fran: number, till: number): number {
  return veckor.slice(fran, till).reduce((s, v) => s + Number(v[nyckel] ?? 0), 0);
}

/** Bredare än 1280 px: leads och listor står bredvid varandra. */
function useBred(): boolean {
  const [bred, setBred] = useState(false);
  useEffect(() => {
    const mq = window.matchMedia("(min-width: 1280px)");
    const satt = () => setBred(mq.matches);
    satt();
    mq.addEventListener("change", satt);
    return () => mq.removeEventListener("change", satt);
  }, []);
  return bred;
}

/** Översiktens egna tal. Ett fel blir null, och rutan visar tankstreck. */
function useOversiktsdata(demo: boolean) {
  const [prospekt, setProspekt] = useState<SuiteProspekt[] | null>(null);
  const [veckor, setVeckor] = useState<Vecka[] | null>(null);

  const hamta = useCallback(
    async <T,>(path: string): Promise<T | null> => {
      if (demo) return (demoOversiktSvar(path) as T | undefined) ?? null;
      try {
        const response = await fetch(`/api/snajp-support${path}`, { cache: "no-store" });
        if (!response.ok) return null;
        return await readJsonBody<T>(response);
      } catch {
        return null;
      }
    },
    [demo]
  );

  const ladda = useCallback(async () => {
    const [p, w] = await Promise.all([
      hamta<{ prospects?: SuiteProspekt[] }>("/leads/prospects?limit=500"),
      hamta<{ weeks?: Vecka[] }>("/analytics/weekly?weeks=24")
    ]);
    setProspekt(p ? (p.prospects ?? []) : []);
    setVeckor(w ? (w.weeks ?? []) : []);
  }, [hamta]);

  useEffect(() => {
    void ladda();
    // En körning eller ett skickat utkast flyttar talen medan man tittar.
    const uppdatera = () => void ladda();
    window.addEventListener("snipra:leads-korning-klar", uppdatera);
    return () => window.removeEventListener("snipra:leads-korning-klar", uppdatera);
  }, [ladda]);

  return { prospekt, veckor };
}

/**
 * Rutan med pågående körningar: kompakta rader, pollas var tionde sekund så
 * länge någon pågår. Klicket öppnar den fulla vyn (fliken Körningar).
 */
function KorningsRuta({ onOppna, onPagaende }: Readonly<{ onOppna: (jobId: string | null) => void; onPagaende?: (antal: number) => void }>) {
  const { text } = useLocale();
  const [rader, setRader] = useState<KorningsRad[] | null>(null);
  const stoppad = useRef(false);

  const hamta = useCallback(async () => {
    try {
      const response = await fetch("/api/snajp-support/leads/korningar", { cache: "no-store" });
      if (!response.ok) {
        if ([401, 403, 404].includes(response.status)) stoppad.current = true;
        setRader((nu) => nu ?? []);
        return;
      }
      const svar = await readJsonBody<{ korningar?: KorningsRad[] }>(response);
      setRader(svar?.korningar ?? []);
    } catch {
      setRader((nu) => nu ?? []);
    }
  }, []);

  useEffect(() => {
    void hamta();
  }, [hamta]);

  const pagaende = (rader ?? []).filter(pagar);

  useEffect(() => {
    if (rader !== null) onPagaende?.(pagaende.length);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [rader, pagaende.length]);

  useEffect(() => {
    if (pagaende.length === 0 || stoppad.current) return;
    const id = window.setInterval(() => void hamta(), 10_000);
    return () => window.clearInterval(id);
  }, [pagaende.length, hamta]);

  const visade = pagaende.length > 0 ? pagaende.slice(0, 4) : (rader ?? []).slice(0, 1);

  return (
    <section aria-labelledby="leads-korningsruta" className={kort}>
      <div className="flex flex-wrap items-baseline justify-between gap-x-6 gap-y-2">
        <h2 id="leads-korningsruta" className="text-[1rem] font-semibold">
          {pagaende.length > 0 ? text(T.pagaendeKorningar) : text(T.senasteKorning)}
        </h2>
        <button
          type="button"
          onClick={() => onOppna(null)}
          className="focus-ring text-[0.8125rem] font-medium text-ink-muted underline underline-offset-4 hover:text-ink"
        >
          {text(T.allaKorningar)}
        </button>
      </div>
      {rader === null ? (
        <p className={cn(meta, "mt-3")}>…</p>
      ) : visade.length === 0 ? (
        <p className={cn(meta, "mt-3")}>{text(T.ingaKorningar)}</p>
      ) : (
        <ul className="mt-3 divide-y divide-ink/10">
          {visade.map((rad) => {
            const k = rad.korning;
            const ton = utfallston(rad);
            const rod = rad.status === "failed" || ton === "stannade";
            const gul = pagar(rad) || ton === "under";
            return (
              <li key={rad.job_id} className="flex flex-wrap items-center justify-between gap-x-6 gap-y-1 py-2.5">
                <span className="min-w-0">
                  <span className="text-[0.9375rem] font-medium">{text(korningsTyp(rad))}</span>
                  {k ? (
                    <span className={cn(meta, "num ml-2 tabular-nums")}>
                      {k.levererade} {text(T.av)} {k.mal} {text(T.leadsKlara)}
                    </span>
                  ) : null}
                </span>
                <span className="flex shrink-0 items-center gap-3">
                  <span
                    className={cn(
                      "inline-flex items-center gap-1.5 text-[0.8125rem]",
                      rod ? "text-danger" : gul ? "text-warning" : "text-ink-muted"
                    )}
                  >
                    <span
                      aria-hidden
                      className={cn("h-1.5 w-1.5 rounded-full", rod ? "bg-danger" : gul ? "bg-ochre" : "bg-moss")}
                    />
                    {text(pagar(rad) ? statusText(rad) : ton === "ok" ? KORNINGSSTATUS[rad.status] : statusText(rad))}
                  </span>
                  <button
                    type="button"
                    onClick={() => onOppna(rad.job_id)}
                    className={cn(btnSecondary, btnLiten)}
                  >
                    {text(T.oppna)}
                  </button>
                </span>
              </li>
            );
          })}
        </ul>
      )}
    </section>
  );
}

export function LeadsOversikt({
  demo = false,
  crmOppen = false,
  valdId = null,
  exempel = [],
  onValjLead,
  onOppnaKorningar
}: Readonly<{
  demo?: boolean;
  crmOppen?: boolean;
  valdId?: string | null;
  exempel?: SuiteProspekt[];
  onValjLead?: (id: string) => void;
  onOppnaKorningar?: (jobId: string | null) => void;
}>) {
  const { addons, isDemo, vy, isPlatformAdmin, impersonation } = useDashboard();
  const { text } = useLocale();
  const arDemo = demo || isDemo || vy === "demo";
  const harListaddon = addons.includes("leadlists");
  const bred = useBred();
  const { prospekt, veckor } = useOversiktsdata(arDemo);
  const [antalLeads, setAntalLeads] = useState<number | null>(null);
  const [antalUtkast, setAntalUtkast] = useState<number | null>(null);

  // Flytt till main: bara plattformsadminens egen vy, aldrig demo eller
  // kundbesök. I main svarar flyttvägen själv med ett tydligt nej.
  const flyttbar = isPlatformAdmin && vy === "admin" && !impersonation && !arDemo;

  const v = veckor ?? [];
  const n = v.length;
  const nu = (k: keyof Vecka) => summa(v, k, Math.max(0, n - PERIOD), n);
  const forra = (k: keyof Vecka) => summa(v, k, Math.max(0, n - 2 * PERIOD), Math.max(0, n - PERIOD));
  const serie = (k: keyof Vecka) => v.slice(-8).map((x) => Number(x[k] ?? 0));
  const harVeckor = veckor !== null && n > 0;
  const perioden: Localized = { sv: `de ${PERIOD} veckorna före`, en: `the ${PERIOD} weeks before` };
  const detalj: Localized = { sv: `senaste ${PERIOD} veckorna`, en: `last ${PERIOD} weeks` };

  const kpier: Kpi[] = [
    // Periodens nya leads, som i Min arbetsyta. Listans antal står som
    // detalj: veckotalet räknar även bortvalda, så de två är olika tal.
    {
      id: "leads",
      etikett: T.nyaLeads,
      varde: harVeckor ? nu("new_leads") : null,
      forandring: harVeckor ? forandring(nu("new_leads"), forra("new_leads")) : undefined,
      serie: harVeckor ? serie("new_leads") : undefined,
      detalj:
        antalLeads === null
          ? detalj
          : { sv: `${detalj.sv} · ${antalLeads} i listan`, en: `${detalj.en} · ${antalLeads} in the list` }
    },
    {
      id: "utkast",
      etikett: T.utkastVantar,
      varde: antalUtkast,
      larm: (antalUtkast ?? 0) > 0,
      detalj: T.vantarPaDig
    },
    {
      id: "skickat",
      etikett: T.skickade,
      varde: harVeckor ? nu("sent") : null,
      forandring: harVeckor ? forandring(nu("sent"), forra("sent")) : undefined,
      serie: harVeckor ? serie("sent") : undefined,
      detalj
    },
    {
      id: "svar",
      etikett: T.svar,
      varde: harVeckor ? nu("replies") : null,
      forandring: harVeckor ? forandring(nu("replies"), forra("replies")) : undefined,
      serie: harVeckor ? serie("replies") : undefined,
      detalj
    }
  ];

  const riktiga = [...exempel, ...(prospekt ?? [])].filter((p, i, alla) => alla.findIndex((q) => q.id === p.id) === i);
  const statusdelar: Andel[] = Object.keys(STATUSFARG).map((s) => ({
    id: s,
    etikett: STATUS_ETIKETT[s],
    antal: riktiga.filter((p) => (p.status ?? "new") === s).length,
    farg: STATUSFARG[s]
  }));
  const kontaktdelar: Andel[] = KONTAKT.map((k) => ({
    id: k.id,
    etikett: k.etikett,
    farg: k.farg,
    antal: riktiga.filter((p) => kontaktvagAv(p) === k.id).length
  }));

  const kolumn = cn(kort, "min-w-0", bred && "thin-scrollbar max-h-[56rem] overflow-y-auto");

  return (
    // flex-kolumn, inte grid: ett grid-items min-width:auto lät tabellernas
    // minsta bredd växa hela sidan i sidled (uppmätt 1318 px vid 1280).
    <div className="flex min-w-0 flex-col gap-6">
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {kpier.map((k) => (
          <KpiKort key={k.id} kpi={k} perioden={perioden} />
        ))}
      </div>

      <div className="grid min-w-0 gap-4 lg:grid-cols-12">
        <section aria-labelledby="leads-aktivitet" className={cn(kort, "min-w-0 lg:col-span-7")}>
          <h2 id="leads-aktivitet" className="mb-4 text-[1rem] font-semibold">
            {text(T.aktivitet)}
          </h2>
          {harVeckor ? (
            <Aktivitetsgraf
              veckor={v.slice(-12)}
              serier={[
                { nyckel: "new_leads", etikett: T.nyaLeads, ton: "chart-ochre" },
                { nyckel: "replies", etikett: T.svar, ton: "chart-blue" }
              ]}
            />
          ) : (
            <p className={meta}>{veckor === null ? "…" : text(T.ingenAktivitet)}</p>
          )}
        </section>
        <section aria-labelledby="leads-fordelning" className={cn(kort, "min-w-0 lg:col-span-5")}>
          <h2 id="leads-fordelning" className="mb-4 text-[1rem] font-semibold">
            {text(T.fordelning)}
          </h2>
          {prospekt === null ? (
            <p className={meta}>…</p>
          ) : (
            <div className="grid gap-6">
              <Munkdiagram delar={statusdelar} etikett={T.status} mitt={T.leadsMitt} />
              <Munkdiagram delar={kontaktdelar} etikett={T.kontaktvag} mitt={T.leadsMitt} />
            </div>
          )}
        </section>
      </div>

      <div className={cn("grid min-w-0 gap-4", !arDemo && "lg:grid-cols-2")}>
        <section aria-labelledby="leads-utkastruta" className={cn(kort, "min-w-0")}>
          <h2 id="leads-utkastruta" className="mb-3 text-[1rem] font-semibold">
            {text(T.utkastRubrik)}
            {antalUtkast ? <span className="num ml-2 font-normal tabular-nums text-ink-subtle">{antalUtkast}</span> : null}
          </h2>
          <IrisGranskning demo={arDemo} onAntal={setAntalUtkast} kompakt />
        </section>
        {arDemo ? null : <KorningsRuta onOppna={(jobId) => onOppnaKorningar?.(jobId)} />}
      </div>

      <SmalKolumn value={bred}>
        <div className="grid min-w-0 gap-4 xl:grid-cols-2">
          <section aria-labelledby="leads-iris" className={kolumn}>
            <h2 id="leads-iris" className="text-[1.0625rem] font-semibold tracking-[-0.01em]">
              {text(T.irisLeads)}
            </h2>
            <p className={cn(meta, "mb-4 mt-1 max-w-[70ch]")}>{text(T.irisLeadsText)}</p>
            <LeadsTabell
              demo={demo}
              valdId={valdId}
              exempel={exempel}
              onValj={onValjLead}
              flyttbar={flyttbar}
              onAntal={setAntalLeads}
            />
          </section>

          <section aria-labelledby="leads-listor" className={kolumn}>
            <h2 id="leads-listor" className="mb-4 text-[1.0625rem] font-semibold tracking-[-0.01em]">
              {text(T.listorRubrik)}
            </h2>
            {harListaddon || arDemo ? (
              <LeadslistorView demo={demo} crmOppen={crmOppen} />
            ) : (
              <div className="grid gap-8">
                <SaljlistaUtforska />
                <CrmKundlista startOppen={crmOppen} />
                <ListorUpsell />
              </div>
            )}
          </section>
        </div>
      </SmalKolumn>
    </div>
  );
}
