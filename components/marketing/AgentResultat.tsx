"use client";

import { AlertTriangle, ArrowUpRight, CheckCircle2 } from "lucide-react";
import { useLocale } from "@/lib/i18n";
import type { Localized } from "@/lib/i18n";
import type { ProductKey } from "@/lib/routes";
import { cn } from "@/lib/utils";

/**
 * Resultatvyn — vad kunden ser när agenten har arbetat ett tag.
 *
 * ## Varför sektionen finns
 *
 * Demon ovanför visar HUR agenten arbetar; den här visar VAD arbetet ger.
 * Förebilderna är uttalade i briefen: Artisan för leads (resultat, inte
 * API-anrop; varma svar som färdiga kort en människa tar över), Digits för
 * bokföringen (rapporten live och avvikelser i klarspråk i stället för en rå
 * transaktionslista), Intercom Fin för kundtjänsten (lösningsgrad och hur
 * många ärenden som aldrig behövde nå en människa, inte ärendekön i sig).
 *
 * ## Honest-proof-regeln gäller (DESIGN.md)
 *
 * Varje siffra här är exempeldata och SÄGER det, i en egen rad under panelen.
 * Siffrorna bor inuti produktpanelen, aldrig i marknadscopyn runt den: "62 %
 * öppnade" i en rubrik vore ett resultatlöfte; samma tal inuti en illustrerad
 * arbetsyta märkt "exempeldata" är en bild av produkten. Ingen fejkad
 * webbläsar-chrome runt panelen, av samma skäl — panelen är produktens egen
 * yta, inte en skärmdump av en.
 */

type Stat = { varde: string; etikett: Localized };

const ACCENT = /\*([^*]+)\*/g;

function Accent({ text: value }: Readonly<{ text: string }>) {
  return (
    <>
      {value.split(ACCENT).map((part, i) =>
        i % 2 === 1 ? (
          <span key={i} className="italic-disp text-ochre">
            {part}
          </span>
        ) : (
          <span key={i}>{part}</span>
        )
      )}
    </>
  );
}

/** Nyckeltalsraden: stora tabulära tal i Fraunces, ochre — DESIGN.md:s "ochre at display scale". */
function StatRad({ stats }: Readonly<{ stats: Stat[] }>) {
  const { text } = useLocale();
  return (
    <dl className="grid grid-cols-2 gap-x-6 gap-y-6 border-y border-ink/15 py-6 sm:grid-cols-4">
      {stats.map((stat) => (
        <div key={stat.etikett.sv} className="min-w-0">
          <dd className="numeral text-[clamp(1.75rem,3.2vw,2.75rem)] font-semibold text-ochre">
            {stat.varde}
          </dd>
          <dt className="mt-2 text-[0.8125rem] leading-snug text-ink/60">{text(stat.etikett)}</dt>
        </div>
      ))}
    </dl>
  );
}

function Panel({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <div className="overflow-hidden rounded-panel border border-ink/12 bg-paper">
      {children}
    </div>
  );
}

function PanelHuvud({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <div className="border-b border-ink/10 bg-paper2/60 px-5 py-3">
      <span className="text-[0.8125rem] font-medium text-ink/55">{children}</span>
    </div>
  );
}

/* ------------------------------------------------------------------ Leads */

/**
 * Artisan-greppet: varma svar dyker upp som färdiga kort, redo att tas över
 * av en människa — inte som rader i en logg.
 */
function LeadsPanel() {
  const { text } = useLocale();

  const kort = [
    {
      namn: "Karin Ahlberg",
      // Fiktivt bolag. Inte "Nordform" eller något annat namn som förekommit
      // i riktiga körningar — exempeldata får aldrig bära verkliga bolag.
      bolag: "Vestera Industri AB",
      rad: {
        sv: "”Ja, det här är aktuellt för oss. Kan ni ta ett möte i nästa vecka?”",
        en: "”Yes, this is relevant for us. Could we take a meeting next week?”"
      },
      tid: { sv: "Svar för 2 tim sedan", en: "Replied 2 hrs ago" }
    },
    {
      namn: "Jonas Vikström",
      bolag: "Baltzar Logistik AB",
      rad: {
        sv: "”Skicka gärna prisexempel, vi jämför leverantörer just nu.”",
        en: "”Please send pricing examples, we are comparing vendors right now.”"
      },
      tid: { sv: "Svar i går", en: "Replied yesterday" }
    }
  ];

  return (
    <Panel>
      <PanelHuvud>{text({ sv: "Varma svar, redo att ta över", en: "Warm replies, ready to take over" })}</PanelHuvud>
      <div className="divide-y divide-ink/10">
        {kort.map((k) => (
          <div key={k.namn} className="px-5 py-4">
            <div className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
              <p className="font-semibold tracking-[-0.01em]">
                {k.namn}
                <span className="ml-2 font-normal text-ink/55">{k.bolag}</span>
              </p>
              <p className="text-[0.8125rem] text-ink/45">{text(k.tid)}</p>
            </div>
            <p className="mt-2 max-w-[58ch] text-[0.9375rem] leading-[1.6] text-ink/75">{text(k.rad)}</p>
            <p className="mt-3 inline-flex items-center gap-1.5 text-[0.875rem] font-semibold text-ink">
              {text({ sv: "Ta över tråden", en: "Take over the thread" })}
              <ArrowUpRight className="h-4 w-4 text-ochre" aria-hidden />
            </p>
          </div>
        ))}
      </div>
    </Panel>
  );
}

/* ---------------------------------------------------------------- Support */

/**
 * Intercom Fin-greppet: effekten av agenten — lösningsgrad, nöjdhet och hur
 * många ärenden som aldrig behövde nå en människa — inte ärendekön i sig.
 */
function SupportPanel() {
  const { text } = useLocale();

  const rader = [
    { kategori: { sv: "Leverans & frakt", en: "Delivery & shipping" }, losta: "9 av 10" },
    { kategori: { sv: "Betalning & faktura", en: "Payment & invoicing" }, losta: "8 av 10" },
    { kategori: { sv: "Teknisk support", en: "Technical support" }, losta: "6 av 10" }
  ];

  return (
    <Panel>
      <PanelHuvud>{text({ sv: "Veckan i kundtjänsten", en: "The week in support" })}</PanelHuvud>
      <div className="divide-y divide-ink/10">
        {rader.map((rad) => (
          <div key={rad.kategori.sv} className="grid grid-cols-12 items-baseline gap-x-4 px-5 py-3.5">
            <p className="col-span-7 truncate text-[0.9375rem]">{text(rad.kategori)}</p>
            <p className="num col-span-5 text-right text-[0.9375rem] text-ink/70">
              {rad.losta}{" "}
              <span className="text-[0.8125rem] text-ink/45">
                {text({ sv: "löst utan människa", en: "resolved without a human" })}
              </span>
            </p>
          </div>
        ))}
        <div className="flex items-start gap-3 px-5 py-4">
          <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-moss" aria-hidden />
          <p className="text-[0.875rem] leading-[1.55] text-ink/70">
            {text({
              sv: "Resten eskalerades med färdigt utkast och full ärendehistorik. Ingen fråga lämnades obesvarad.",
              en: "The rest were escalated with a ready draft and the full case history. No question was left unanswered."
            })}
          </p>
        </div>
      </div>
    </Panel>
  );
}

/* -------------------------------------------------------------- Bokföring */

/**
 * Digits-greppet: rapporten live och avvikelser flaggade i klarspråk med
 * förslag på rättning — i stället för en rå transaktionslista.
 */
function BokforingPanel() {
  const { text } = useLocale();

  const rader = [
    { etikett: { sv: "Intäkter", en: "Revenue" }, varde: "312 400 kr" },
    { etikett: { sv: "Kostnader", en: "Costs" }, varde: "228 100 kr" },
    { etikett: { sv: "Resultat före skatt", en: "Profit before tax" }, varde: "84 300 kr", stark: true },
    { etikett: { sv: "Moms att betala", en: "VAT to pay" }, varde: "23 150 kr" }
  ];

  return (
    <Panel>
      <PanelHuvud>{text({ sv: "Perioden, räknad ur underlagen", en: "The period, computed from the documents" })}</PanelHuvud>
      <div className="divide-y divide-ink/10">
        {rader.map((rad) => (
          <div key={rad.etikett.sv} className="grid grid-cols-12 items-baseline gap-x-4 px-5 py-3.5">
            <p className={cn("col-span-7 truncate text-[0.9375rem]", rad.stark && "font-semibold")}>
              {text(rad.etikett)}
            </p>
            <p className={cn("num col-span-5 text-right text-[0.9375rem]", rad.stark ? "font-semibold" : "text-ink/70")}>
              {rad.varde}
            </p>
          </div>
        ))}
        <div className="flex items-start gap-3 bg-ochre/[0.07] px-5 py-4">
          <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-ochre" aria-hidden />
          <div className="min-w-0">
            <p className="text-[0.875rem] font-semibold">
              {text({ sv: "3 underlag behöver din blick", en: "3 documents need your eye" })}
            </p>
            <p className="mt-1 text-[0.875rem] leading-[1.55] text-ink/70">
              {text({
                sv: "Ett kvitto saknar momsrad, en faktura har oläsligt datum och ett belopp balanserar inte. Agenten gissar aldrig, den frågar.",
                en: "One receipt is missing its VAT line, one invoice has an unreadable date and one amount does not balance. The agent never guesses, it asks."
              })}
            </p>
          </div>
        </div>
      </div>
    </Panel>
  );
}

/* ------------------------------------------------------------------ Sektion */

type SektionsCopy = {
  rubrik: Localized;
  brod: Localized;
  stats: Stat[];
  panel: React.ReactNode;
};

export function AgentResultat({ product }: Readonly<{ product: ProductKey }>) {
  const { text } = useLocale();

  const perProdukt: Record<ProductKey, SektionsCopy> = {
    leads: {
      rubrik: {
        sv: "Ni ser *resultaten*, inte maskineriet.",
        en: "You see the *results*, not the machinery."
      },
      brod: {
        sv: "Arbetsytan visar vad utskicken gav: vilka som öppnade, vilka som svarade och vilka som vill ses. Ett varmt svar dyker upp som ett färdigt kort med hela tråden, redo för en människa att ta över.",
        en: "The workspace shows what the outreach produced: who opened, who replied and who wants to meet. A warm reply appears as a finished card with the whole thread, ready for a person to take over."
      },
      stats: [
        { varde: "62 %", etikett: { sv: "öppnade mejlet", en: "opened the email" } },
        { varde: "18 %", etikett: { sv: "svarade", en: "replied" } },
        { varde: "7", etikett: { sv: "möten bokade denna månad", en: "meetings booked this month" } },
        { varde: "34", etikett: { sv: "bolag i pipeline", en: "companies in pipeline" } }
      ],
      panel: <LeadsPanel />
    },
    support: {
      rubrik: {
        sv: "Effekten syns: färre ärenden som *behöver er*.",
        en: "The effect is visible: fewer cases that *need you*."
      },
      brod: {
        sv: "Vyn handlar inte om kön utan om utfallet: hur stor andel som löstes direkt, hur nöjda kunderna var och vad som skickades vidare till en människa, med färdigt utkast.",
        en: "The view is not about the queue but the outcome: how much was resolved outright, how satisfied customers were, and what was handed to a person, draft included."
      },
      stats: [
        { varde: "71 %", etikett: { sv: "löstes utan människa", en: "resolved without a human" } },
        { varde: "26 s", etikett: { sv: "till första svar", en: "to first reply" } },
        { varde: "4,6", etikett: { sv: "kundnöjdhet av 5", en: "satisfaction out of 5" } },
        { varde: "182", etikett: { sv: "ärenden denna vecka", en: "cases this week" } }
      ],
      panel: <SupportPanel />
    },
    bookkeeping: {
      rubrik: {
        sv: "Rapporten *lever*, avvikelserna talar klarspråk.",
        en: "The report is *live*, and deviations speak plainly."
      },
      brod: {
        sv: "Resultat, moms och kostnader räknas ur underlagen och uppdateras när nya kommer in. Avviker något flaggas det i klarspråk med förslag på rättning, i stället för att gömma sig i en transaktionslista.",
        en: "Profit, VAT and costs are computed from the documents and update as new ones arrive. Anything off is flagged in plain language with a suggested fix, instead of hiding in a transaction list."
      },
      stats: [
        { varde: "128", etikett: { sv: "underlag bokförda", en: "documents booked" } },
        { varde: "3", etikett: { sv: "avvikelser att granska", en: "deviations to review" } },
        { varde: "100 %", etikett: { sv: "moms räknad i kod", en: "VAT computed in code" } },
        { varde: "0", etikett: { sv: "gissade fält", en: "guessed fields" } }
      ],
      panel: <BokforingPanel />
    }
  };

  const copy = perProdukt[product];

  return (
    <section aria-labelledby="agentresultat-rubrik" className="border-t border-ink/12">
      <div className="mx-auto max-w-[1480px] px-6 py-24 md:px-10 md:py-32">
        <div className="grid grid-cols-12 gap-y-12 lg:gap-x-14">
          <div className="col-span-12 lg:col-span-5">
            <h2
              id="agentresultat-rubrik"
              className="rise max-w-[16ch] font-display text-[clamp(2rem,4.2vw,3.25rem)] font-semibold leading-[1.04] tracking-[-0.03em]"
            >
              <Accent text={text(copy.rubrik)} />
            </h2>
            <p className="rise rise-1 mt-6 max-w-[48ch] text-[1.0625rem] leading-[1.7] text-ink/75">
              {text(copy.brod)}
            </p>
            <div className="rise rise-2 mt-10">
              <StatRad stats={copy.stats} />
            </div>
          </div>
          <div className="col-span-12 lg:col-span-6 lg:col-start-7">
            <div className="rise rise-1">{copy.panel}</div>
            {/* Honest-proof: siffrorna ovan är illustration, och det står. */}
            <p className="mt-4 text-[0.8125rem] font-medium text-ink/45">
              {text({
                sv: "Illustration med exempeldata, inte uppmätta resultat.",
                en: "Illustration with example data, not measured results."
              })}
            </p>
          </div>
        </div>
      </div>
    </section>
  );
}
