"use client";

import { ChevronDown } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import { useDashboard } from "@/components/dashboard/DashboardContext";
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
import { Nyckeltal, btnLiten, btnSecondary, meta, rubrikPanel } from "@/components/ui";
import { readJsonBody } from "@/lib/http/json";
import { useLocale, type Localized } from "@/lib/i18n";
import type { SuiteProspekt } from "@/lib/leads/suite";
import { cn } from "@/lib/utils";

/**
 * Leads › Översikt (Sebbes beställning 2026-10-06, omgjord 2026-10-07).
 *
 *   en rad nyckeltal (hårlinjer, inga kort)
 *   de tre senaste utkasten (expanderbar, skicka direkt) · körningarna
 *   Iris-leads i full bredd (tabellen från lg)
 *   listor och säljlista
 *
 * Kritik 2 samma dag (24/40): högerkolumnen (säljlista, CRM, beställning)
 * blev 7 400 px och tryckte ner utkasten, och delad vy tvingade fram kort så
 * att tabellen aldrig syntes på 1280. Ordningen är nu nyckeltal → utkast och
 * körningar → Iris-leads i full bredd (tabellen) → listor och säljlista.
 *
 * Impeccable-kritiken 2026-10-07 (26/40): första skärmen var statistik och
 * listan började under vecket. Listan står nu först; aktivitetsdiagrammet och
 * munkdiagrammen flyttade till Aktivitet, under Iris rubrik
 * (components/leads/LeadsDiagram.tsx). Kolumnerna rullar inte längre inuti
 * sidan: två rullningar i varandra var svåra att styra.
 *
 * Sebbe 2026-10-07: utkasten är en liten ruta som visar de tre senaste och
 * fäller ut till alla.
 */

const T = {
  utkastVantar: { sv: "Utkast att godkänna", en: "Drafts to approve" },
  vantarPaDig: { sv: "väntar på ditt ja", en: "waiting for your yes" },
  skickade: { sv: "Skickade mejl", en: "Emails sent" },
  svar: { sv: "Svar från leads", en: "Replies from leads" },
  leadsIListan: { sv: "Leads i listan", en: "Leads in the list" },
  exempelLeads: { sv: "bland exempelleadsen", en: "among the example leads" },
  utkastRubrik: { sv: "Senaste utkasten", en: "Latest drafts" },
  pagaendeKorningar: { sv: "Pågående körningar", en: "Runs in progress" },
  senasteKorning: { sv: "Senaste körningen", en: "Latest run" },
  ingaKorningar: { sv: "Inga körningar än.", en: "No runs yet." },
  oppna: { sv: "Öppna", en: "Open" },
  allaKorningar: { sv: "Alla körningar", en: "All runs" },
  irisLeads: { sv: "Iris-leads", en: "Iris leads" },
  // Poängen förklaras där den visas (kritiken: poäng och nivå förklarades
  // ingenstans). Samma vikter som app/leads/rangpoang.py.
  irisLeadsText: {
    sv: "De bästa överst. Poängen väger hur väl bolaget passar, styrkta citat från sajten, kontakten och om tidpunkten är rätt. Ny är bolag Iris just hittat, Redo de du granskat och vill kontakta.",
    en: "Best first. The score weighs how well the company fits, verified quotes from its site, the contact and whether the timing is right. New is companies Iris just found, Ready the ones you have reviewed and want to contact."
  },
  listorRubrik: { sv: "Listor och säljlista", en: "Lists and sales list" },
  listorInnehall: {
    sv: "Säljlistan, kundlistor från ditt CRM och beställda listor.",
    en: "The sales list, customer lists from your CRM and ordered lists."
  },
  av: { sv: "av", en: "of" },
  test: { sv: "test", en: "test" },
  leadsKlara: { sv: "leads klara", en: "leads done" }
} satisfies Record<string, Localized>;

const PERIOD = 4;

const kort = "rounded-card border border-ink/12 bg-paper p-4 sm:p-5";

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
    // En körning som startas medan sidan är öppen (Kör Iris) syns direkt,
    // inte först vid nästa sidladdning: formuläret signalerar varje steg.
    const uppdatera = () => {
      if (!stoppad.current) void hamta();
    };
    window.addEventListener("snipra:leads-korning-steg", uppdatera);
    window.addEventListener("snipra:leads-korning-klar", uppdatera);
    return () => {
      window.removeEventListener("snipra:leads-korning-steg", uppdatera);
      window.removeEventListener("snipra:leads-korning-klar", uppdatera);
    };
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

  // Senaste RIKTIGA körningen (Sebbe 2026-10-08): en testkörning från natten
  // stod här som "Stannade utan leads" över dagens arbete. Testkörningar
  // visas bara när det inte finns något annat, och märks då.
  const senaste = (rader ?? []).find((r) => !r.is_test) ?? (rader ?? [])[0];
  const visade = pagaende.length > 0 ? pagaende.slice(0, 4) : senaste ? [senaste] : [];

  return (
    <section aria-labelledby="leads-korningsruta" className={kort}>
      <div className="flex flex-wrap items-baseline justify-between gap-x-6 gap-y-2">
        <h2 id="leads-korningsruta" className={rubrikPanel}>
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
                  {rad.is_test ? <span className={cn(meta, "ml-2")}>{text(T.test)}</span> : null}
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
  const { text, locale } = useLocale();
  const arDemo = demo || isDemo || vy === "demo";
  const harListaddon = addons.includes("leadlists");
  // Listans egna tal (LeadsTabell.onAntal): samma rader som Alla och Ny visar,
  // och skickat/svar ur samma lista som Inkorg › Skickat (GET /leads/skickat,
  // de senaste fyra veckorna), så att nyckeltalen och listorna aldrig säger
  // två olika saker. Förut räknades Skickade ur veckoanalysen och stod på 0
  // medan Skickat-listan visade mejlen (2026-10-07). Tabellen hämtar om efter
  // varje massåtgärd, och talen följer med.
  const [antalLeads, setAntalLeads] = useState<{
    alla: number;
    nya: number;
    skickat: number | null;
    svarat: number | null;
    godkanda: number;
  } | null>(null);
  const [antalUtkast, setAntalUtkast] = useState<number | null>(null);
  const [listorOppna, setListorOppna] = useState(crmOppen);
  // Körningsrutan vet om en Iris-körning pågår; tabellen går då i livetakt.
  const [pagaendeKorningar, setPagaendeKorningar] = useState(0);

  // Flytt till main: bara plattformsadminens egen vy, aldrig demo eller
  // kundbesök. I main svarar flyttvägen själv med ett tydligt nej.
  const flyttbar = isPlatformAdmin && vy === "admin" && !impersonation && !arDemo;

  const fmt = (varde: number | null) => (varde === null ? "–" : varde.toLocaleString(locale === "en" ? "en-GB" : "sv-SE"));
  const senaste = text({ sv: `senaste ${PERIOD} veckorna`, en: `last ${PERIOD} weeks` });

  const nyckeltal = [
    {
      etikett: text(T.leadsIListan),
      varde: fmt(antalLeads?.alla ?? null),
      notis: antalLeads
        ? text({ sv: `${antalLeads.nya} ${antalLeads.nya === 1 ? "ny" : "nya"}`, en: `${antalLeads.nya} new` })
        : null
    },
    {
      etikett: text(T.utkastVantar),
      varde: fmt(antalUtkast),
      // Godkända utkast som väntar på sändfönstret (vardagar 08–16) syntes
      // förut ingenstans: de är inte "att godkänna" och inte skickade än.
      notis: antalLeads?.godkanda
        ? text({
            sv: `${antalLeads.godkanda} godkända väntar på sändfönstret`,
            en: `${antalLeads.godkanda} approved, waiting for the sending window`
          })
        : text(T.vantarPaDig)
    },
    // Demon räknar ur sina exempelleads; arbetsytan ur utskicksloggen.
    { etikett: text(T.skickade), varde: fmt(antalLeads?.skickat ?? null), notis: arDemo ? text(T.exempelLeads) : senaste },
    { etikett: text(T.svar), varde: fmt(antalLeads?.svarat ?? null), notis: arDemo ? text(T.exempelLeads) : senaste }
  ];

  const kolumn = cn(kort, "relative min-w-0");

  return (
    // flex-kolumn, inte grid: ett grid-items min-width:auto lät tabellernas
    // minsta bredd växa hela sidan i sidled (uppmätt 1318 px vid 1280).
    <div className="flex min-w-0 flex-col gap-6">
      <Nyckeltal poster={nyckeltal} />

      <div className={cn("grid min-w-0 items-start gap-4", !arDemo && "lg:grid-cols-2")}>
        <section aria-labelledby="leads-utkastruta" className={cn(kort, "min-w-0")}>
          <h2 id="leads-utkastruta" className={cn(rubrikPanel, "mb-3")}>
            {text(T.utkastRubrik)}
            {antalUtkast ? <>{" "}<span className="num ml-1 font-normal tabular-nums text-ink-subtle">{antalUtkast}</span></> : null}
          </h2>
          <IrisGranskning demo={arDemo} onAntal={setAntalUtkast} kompakt />
        </section>
        {arDemo ? null : <KorningsRuta onOppna={(jobId) => onOppnaKorningar?.(jobId)} onPagaende={setPagaendeKorningar} />}
      </div>

      <section aria-labelledby="leads-iris" className={kolumn}>
        <h2 id="leads-iris" className={rubrikPanel}>
          {text(T.irisLeads)}
        </h2>
        <p className={cn(meta, "mb-4 mt-1 max-w-[70ch]")}>{text(T.irisLeadsText)}</p>
        <LeadsTabell
          demo={demo}
          valdId={valdId}
          exempel={exempel}
          onValj={onValjLead}
          flyttbar={flyttbar}
          korningPagar={pagaendeKorningar > 0}
          onAntal={setAntalLeads}
        />
      </section>

      {/* Hopfälld under rubriken (kritik 4, Sebbes val): listdelen är ett eget
          arbete och lade ~3 000 px under leadsen. En länk till CRM-uppladdningen
          (crmOppen) fäller ut den direkt. */}
      <section aria-labelledby="leads-listor" className={kolumn}>
        <h2 id="leads-listor" className={rubrikPanel}>
          <button
            type="button"
            aria-expanded={listorOppna}
            aria-controls="leads-listor-innehall"
            onClick={() => setListorOppna((v) => !v)}
            className="focus-ring -mx-1 inline-flex min-h-9 items-center gap-1.5 rounded-input px-1 text-left hover:text-ink-muted"
          >
            {text(T.listorRubrik)}
            <ChevronDown aria-hidden className={cn("h-4 w-4 transition-transform", listorOppna && "rotate-180")} />
          </button>
        </h2>
        {listorOppna ? (
          <div id="leads-listor-innehall" className="mt-4">
            {harListaddon || arDemo ? (
              <LeadslistorView demo={demo} crmOppen={crmOppen} />
            ) : (
              <div className="grid gap-8">
                <SaljlistaUtforska />
                <CrmKundlista startOppen={crmOppen} />
                <ListorUpsell />
              </div>
            )}
          </div>
        ) : (
          <p className={cn(meta, "mt-1")}>{text(T.listorInnehall)}</p>
        )}
      </section>
    </div>
  );
}
