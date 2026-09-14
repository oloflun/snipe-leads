"use client";

import { useLocale } from "@/lib/i18n";
import type { Localized } from "@/lib/i18n";
import {
  BINDNINGSTID_MANADER,
  EXTRA_BOKFORINGSAGENT_PRIS,
  EXTRA_MEJL_PRIS,
  EXTRA_PROSPEKT_PRIS,
  PAKET,
  PRISER_AR_PRELIMINARA,
  PRIS_PREFIX,
  PRIS_SAKNAS,
  UPPSTARTSAVGIFT,
  besparingPerManad,
  formateraPris
} from "@/lib/pricing";
import { mejlaOss } from "@/components/marketing/copy";
import { cn } from "@/lib/utils";

/**
 * Prissektionen.
 *
 * ALL data kommer från `lib/pricing.ts`. Den här filen innehåller ingen enda
 * prissiffra, och ska inte göra det — se resonemanget i pricing.ts.
 *
 * Ingen köpknapp. Vi har ingen betallösning kopplad (Stripe-koden ligger kvar i
 * den icke-mergade kvotgrenen), och en knapp som ser ut att gå att trycka på
 * men leder till ett mejlformulär är sämre än en tydlig kontaktuppmaning.
 */

/**
 * Räkneord, inte siffra. Rubriken är display-typografi och "5 paket." läser
 * som ett formulärfält — men en handskriven rubrik är precis det som gick
 * fel förut, så ordet slås upp ur antalet i stället för att skrivas.
 * Utanför tabellen faller den tillbaka på siffran, vilket är fult men sant.
 */
const RAKNEORD: Record<number, Localized> = {
  1: { sv: "Ett", en: "One" },
  2: { sv: "Två", en: "Two" },
  3: { sv: "Tre", en: "Three" },
  4: { sv: "Fyra", en: "Four" },
  5: { sv: "Fem", en: "Five" },
  6: { sv: "Sex", en: "Six" }
};

const antalPaket = RAKNEORD[PAKET.length] ?? {
  sv: String(PAKET.length),
  en: String(PAKET.length)
};

const copy = {
  kicker: { sv: "Priser", en: "Pricing" },
  //: Antalet räknas ur PAKET och skrivs inte. Rubriken sade "Tre paket."
  //: medan listan renderade fyra kort — bokföringen kom till utan att
  //: rubriken följde med, och ingen såg det. Nu kan de inte gå isär.
  rubrik: {
    sv: `${antalPaket.sv} paket.`,
    en: `${antalPaket.en} packages.`
  },
  lede: {
    sv: "Månadsavgift per arbetsyta. Uppstarten är engångs och täcker kunskapsbas och konfiguration.",
    en: "Monthly fee per workspace. Onboarding is a one-off covering knowledge base and configuration."
  },
  perManad: { sv: "/mån", en: "/mo" },
  ingar: { sv: "Ingår", en: "Included" },
  populärast: { sv: "Populärast", en: "Most popular" },
  uppstart: {
    sv: "Uppstart, engångs — kunskapsbas och konfiguration",
    en: "Onboarding, one-off — knowledge base and configuration"
  },
  extraProspekt: { sv: "per extra prospekt", en: "per extra prospect" },
  extraMejl: { sv: "per extra mejl", en: "per extra email" },
  //: Noll har en egen lydelse. "0 månaders bindningstid" är formellt rätt och
  //: läses ändå som ett fel; mallen gäller från en månad och uppåt.
  bindning:
    BINDNINGSTID_MANADER === 0
      ? { sv: "0 månader bindningstid", en: "No minimum term" }
      : {
          sv: `${BINDNINGSTID_MANADER} månaders bindningstid`,
          en: `${BINDNINGSTID_MANADER} months minimum term`
        },
  preliminart: {
    sv: "Priserna är preliminära under pilotperioden och kan komma att ändras. Vi hör av oss innan något ändras för dig som redan är kund.",
    en: "Prices are provisional during the pilot period and may change. We will contact you before anything changes for existing customers."
  },
  ctaRubrik: {
    sv: "Osäker på vilket paket som passar?",
    en: "Not sure which package fits?"
  },
  ctaBody: {
    sv: "Beskriv er verksamhet så hjälper vi er med ett skräddarsytt paket.",
    en: "Tell us about your business and we will put together a package that fits."
  },
  ctaKnapp: { sv: "Hör av dig", en: "Get in touch" }
} satisfies Record<string, Localized>;

export function PricingSection() {
  const { text } = useLocale();

  return (
    <section id="priser" className="border-t border-ink/12 bg-paper" aria-labelledby="priser-rubrik">
      <div className="mx-auto max-w-[1480px] px-6 py-24 md:px-10 md:py-32">
        <p className="kicker text-mineral">{text(copy.kicker)}</p>
        <h2
          id="priser-rubrik"
          className="mt-4 max-w-[24ch] font-display text-[clamp(2rem,4.2vw,3.25rem)] font-semibold leading-[1.04] tracking-[-0.03em]"
        >
          {text(copy.rubrik)}
        </h2>
        <p className="mt-5 max-w-[54ch] text-[1.0625rem] leading-[1.7] text-ink/80">
          {text(copy.lede)}
        </p>

        <div className="mt-14 grid gap-6 lg:grid-cols-3">
          {PAKET.map((paket) => (
            <article
              key={paket.id}
              className={cn(
                "flex flex-col rounded-input border p-7",
                paket.populärast
                  ? "border-ochre/50 bg-paper2 shadow-[0_1px_0_oklch(var(--ochre)/0.25)]"
                  : "border-ink/12 bg-paper"
              )}
            >
              <div className="flex min-h-7 items-start justify-between gap-3">
                <h3 className="font-display text-[1.375rem] font-semibold tracking-[-0.015em]">
                  {paket.namn}
                </h3>
                {paket.populärast ? (
                  <span className="kicker shrink-0 rounded-input bg-ochre/12 px-2.5 py-1 text-ochre">
                    {text(copy.populärast)}
                  </span>
                ) : null}
              </div>

              <p className="mt-3 min-h-[3.25rem] max-w-[38ch] text-[0.9375rem] leading-[1.6] text-ink/75">
                {text(paket.beskrivning)}
              </p>

              {/* "från" före beloppet: paketpriserna är ingångspriser och
                  sätts efter volym. Ordet kommer ur pricing.ts, så prislistans
                  tre kort och raden under dem säger samma sak. */}
              {/* Ett paket utan pris säger det, i stället för att visa "0 kr".
                  Se `prisPerManad: number | null` i lib/pricing.ts — noll är
                  ett pris, och det står då bredvid tre riktiga. */}
              {/* Priset till vänster, kampanjen litet till höger om det.
                  `items-end` och inte `items-baseline`: kampanjtexten går på
                  två rader i kortets bredd, och en baslinjejustering hade
                  hängt upp dess FÖRSTA rad i höjd med prisets baslinje — alltså
                  en rad text som sticker upp ovanför siffran. */}
              <div className="mt-6 flex flex-wrap items-end justify-between gap-x-4 gap-y-2">
              {paket.prisPerManad === null ? (
                <p>
                  <span className="font-display text-[2rem] font-semibold leading-none tracking-[-0.03em]">
                    {text(PRIS_SAKNAS)}
                  </span>
                </p>
              ) : (
                <p className="flex items-baseline gap-1.5">
                  <span className="text-[0.9375rem] text-mineral">{text(PRIS_PREFIX)}</span>
                  <span className="font-display text-[2.5rem] font-semibold leading-none tracking-[-0.03em]">
                    {formateraPris(paket.prisPerManad)}
                  </span>
                  <span className="text-[0.9375rem] text-mineral">{text(copy.perManad)}</span>
                </p>
              )}
              {/* Fast bredd, uppmätt. Kortets innehållsbredd är 374px och
                  priset 208; med gapet på 16 blir 144 det bredaste som ryms
                  bredvid utan att raden bryts. Måttet är inte hämtat ur
                  luften och tål inte att priset blir mycket bredare.
                  `max-w-[24ch]` stod här först och gav 175px — 399 totalt, och
                  texten föll ned under priset. `flex-1 basis-[7rem]` gav i sin
                  tur `flex: 0 1 0%` och en ruta på noll pixlar med texten
                  staplad på höjden. Den här varianten är trist och mätbar. */}
              {paket.kampanj ? (
                <p className="w-36 shrink-0 text-right text-[0.6875rem] leading-[1.4] text-moss">
                  {text(paket.kampanj).replace(
                    "{belopp}",
                    formateraPris(EXTRA_BOKFORINGSAGENT_PRIS)
                  )}
                </p>
              ) : null}
              </div>

              {paket.notisMall ? (
                <p className="mt-2 text-[0.875rem] font-medium text-moss">
                  {text(paket.notisMall).replace("{belopp}", formateraPris(besparingPerManad(paket.id)))}
                </p>
              ) : (
                <p className="mt-2 text-[0.875rem] text-transparent" aria-hidden="true">
                  &nbsp;
                </p>
              )}

              <p className="kicker mt-7 text-mineral">{text(copy.ingar)}</p>
              <ul className="mt-3 flex flex-col gap-2.5">
                {paket.ingar.map((rad, index) => (
                  <li
                    key={index}
                    className="flex gap-2.5 text-[0.9375rem] leading-[1.5] text-ink/85"
                  >
                    <span aria-hidden="true" className="mt-[0.55em] h-1 w-1 shrink-0 rounded-full bg-ochre" />
                    {text(rad)}
                  </li>
                ))}
              </ul>
            </article>
          ))}
        </div>

        {/* Rörliga priser och engångsavgift. Egen rad, inte i korten: de gäller
            samtliga paket, och en kopia per kort är lika många ställen att
            glömma uppdatera. */}
        <dl className="mt-8 grid gap-px overflow-hidden rounded-input border border-ink/12 bg-ink/12 sm:grid-cols-2 lg:grid-cols-4">
          {[
            { term: `${text(PRIS_PREFIX)} ${formateraPris(UPPSTARTSAVGIFT)}`, desc: text(copy.uppstart) },
            { term: `${text(PRIS_PREFIX)} ${formateraPris(EXTRA_PROSPEKT_PRIS)}`, desc: text(copy.extraProspekt) },
            { term: `${text(PRIS_PREFIX)} ${formateraPris(EXTRA_MEJL_PRIS)}`, desc: text(copy.extraMejl) },
            { term: `${BINDNINGSTID_MANADER} mån`, desc: text(copy.bindning) }
          ].map((rad) => (
            <div key={rad.desc} className="bg-paper px-5 py-4">
              <dt className="font-display text-[1.25rem] font-semibold tracking-[-0.02em]">
                {rad.term}
              </dt>
              <dd className="mt-1 text-[0.875rem] leading-[1.5] text-ink/70">{rad.desc}</dd>
            </div>
          ))}
        </dl>

        {PRISER_AR_PRELIMINARA ? (
          <p className="mt-6 max-w-[62ch] text-[0.875rem] leading-[1.6] text-mineral">
            {text(copy.preliminart)}
          </p>
        ) : null}

        <div className="mt-12 flex flex-col gap-5 rounded-input border border-ink/12 bg-paper2 px-7 py-8 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <p className="font-display text-[1.25rem] font-semibold tracking-[-0.02em]">
              {text(copy.ctaRubrik)}
            </p>
            <p className="mt-2 max-w-[52ch] text-[0.9375rem] leading-[1.6] text-ink/75">
              {text(copy.ctaBody)}
            </p>
          </div>
          <a
            href={mejlaOss("Fråga om priser")}
            className="focus-ring inline-flex min-h-12 shrink-0 items-center justify-center rounded-input bg-ink px-7 text-[0.9375rem] font-semibold text-paper transition-colors hover:bg-ink2"
          >
            {text(copy.ctaKnapp)}
          </a>
        </div>
      </div>
    </section>
  );
}
