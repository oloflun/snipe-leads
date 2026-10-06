"use client";

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
import { Nyckeltal, Sektion, btnLiten, btnSecondary, meta } from "@/components/ui";
import { readJsonBody } from "@/lib/http/json";
import { useLocale, type Localized } from "@/lib/i18n";
import type { SuiteProspekt } from "@/lib/leads/suite";
import { cn } from "@/lib/utils";

/**
 * Leads › Översikt (Sebbes beställning 2026-10-06): EN första flik med allt —
 * nyckeltal överst (samma form som Min arbetsyta), pågående körningar i en
 * egen ruta med länk till den fulla vyn, utkasten att godkänna (med
 * flerval), alla Iris-leads i färgsystemet, och listorna/säljlistan under en
 * egen rubrik. Iris-leads och list-leads står tydligt åtskilda i varsin
 * sektion men bor på samma sida.
 *
 * De gamla flikarna Leads och Utkast är borta: tabellen och granskningen
 * lever här, och utkastet nås också inne på varje lead som förut.
 */

const T = {
  leads: { sv: "Leads", en: "Leads" },
  utkastVantar: { sv: "Utkast att godkänna", en: "Drafts to approve" },
  pagaendeKorningar: { sv: "Pågående körningar", en: "Runs in progress" },
  korningar: { sv: "Körningar", en: "Runs" },
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
    <section
      aria-labelledby="leads-korningsruta"
      className="rounded-card border border-ink/12 bg-paper2/40 p-4 sm:p-5"
    >
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
  const [antalLeads, setAntalLeads] = useState<number | null>(null);
  const [antalUtkast, setAntalUtkast] = useState<number | null>(null);
  const [antalPagaende, setAntalPagaende] = useState<number | null>(null);

  // Flytt till main: bara plattformsadminens egen vy, aldrig demo eller
  // kundbesök. I main svarar flyttvägen själv med ett tydligt nej.
  const flyttbar = isPlatformAdmin && vy === "admin" && !impersonation && !arDemo;

  return (
    // flex-kolumn, inte grid: ett grid-items min-width:auto lät tabellernas
    // minsta bredd växa hela sidan i sidled (uppmätt 1318 px vid 1280).
    <div className="flex min-w-0 flex-col gap-10">
      <Nyckeltal
        poster={[
          { etikett: text(T.leads), varde: antalLeads ?? "–" },
          { etikett: text(T.utkastVantar), varde: antalUtkast ?? "–" },
          { etikett: text(T.pagaendeKorningar), varde: arDemo ? 0 : (antalPagaende ?? "–") }
        ]}
      />

      {arDemo ? null : <KorningsRuta onOppna={(jobId) => onOppnaKorningar?.(jobId)} onPagaende={setAntalPagaende} />}

      {/* Utkasten: inte en egen flik längre — de godkänns här (flera åt
          gången) eller inne på varje lead. Sektionen syns bara när något
          väntar, annars är den bara brus ovanför leadsen. */}
      {antalUtkast === null || antalUtkast > 0 || arDemo ? (
        <Sektion title={`${text(T.utkastVantar)}${antalUtkast ? ` (${antalUtkast})` : ""}`}>
          <IrisGranskning demo={arDemo} onAntal={setAntalUtkast} />
        </Sektion>
      ) : null}

      <Sektion title={text(T.irisLeads)}>
        <p className={cn(meta, "-mt-2 mb-4 max-w-[70ch]")}>{text(T.irisLeadsText)}</p>
        <LeadsTabell
          demo={demo}
          valdId={valdId}
          exempel={exempel}
          onValj={onValjLead}
          flyttbar={flyttbar}
          onAntal={setAntalLeads}
        />
      </Sektion>

      <Sektion title={text(T.listorRubrik)} className="border-t border-ink/15 pt-10">
        {harListaddon || arDemo ? (
          <LeadslistorView demo={demo} crmOppen={crmOppen} />
        ) : (
          <div className="grid gap-8">
            <SaljlistaUtforska />
            <CrmKundlista startOppen={crmOppen} />
            <ListorUpsell />
          </div>
        )}
      </Sektion>
    </div>
  );
}
