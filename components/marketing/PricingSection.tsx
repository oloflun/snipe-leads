"use client";

import { useLocale } from "@/lib/i18n";
import type { Localized } from "@/lib/i18n";
import {
  BINDNINGSTID_MANADER,
  EXTRA_MEJL_PRIS,
  EXTRA_PROSPEKT_PRIS,
  PAKET,
  PRISER_AR_PRELIMINARA,
  UPPSTARTSAVGIFT,
  formateraPris
} from "@/lib/pricing";
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

const copy = {
  kicker: { sv: "Priser", en: "Pricing" },
  rubrik: {
    sv: "Tre paket. Inga dolda avgifter.",
    en: "Three packages. No hidden fees."
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
  bindning: {
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
    sv: "Beskriv verksamheten så säger vi vad som är rimligt. Vi säljer hellre rätt paket än det dyraste.",
    en: "Tell us about your business and we will say what makes sense. We would rather sell the right package than the most expensive one."
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

              <p className="mt-6 flex items-baseline gap-1.5">
                <span className="font-display text-[2.5rem] font-semibold leading-none tracking-[-0.03em]">
                  {formateraPris(paket.prisPerManad)}
                </span>
                <span className="text-[0.9375rem] text-mineral">{text(copy.perManad)}</span>
              </p>

              {paket.notis ? (
                <p className="mt-2 text-[0.875rem] font-medium text-moss">{text(paket.notis)}</p>
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
            alla tre paket, och tre kopior av samma rad är tre ställen att
            glömma uppdatera. */}
        <dl className="mt-8 grid gap-px overflow-hidden rounded-input border border-ink/12 bg-ink/12 sm:grid-cols-2 lg:grid-cols-4">
          {[
            { term: formateraPris(UPPSTARTSAVGIFT), desc: text(copy.uppstart) },
            { term: formateraPris(EXTRA_PROSPEKT_PRIS), desc: text(copy.extraProspekt) },
            { term: formateraPris(EXTRA_MEJL_PRIS), desc: text(copy.extraMejl) },
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
            href="mailto:hej@snajp.se?subject=Fr%C3%A5ga%20om%20priser"
            className="focus-ring inline-flex min-h-12 shrink-0 items-center justify-center rounded-input bg-ink px-7 text-[0.9375rem] font-semibold text-paper transition-colors hover:bg-ink2"
          >
            {text(copy.ctaKnapp)}
          </a>
        </div>
      </div>
    </section>
  );
}
