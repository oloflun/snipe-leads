"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { Logo } from "@/components/Logo";
import { useLocale } from "@/lib/i18n";
import type { ProductKey } from "@/lib/routes";
import { productKeys } from "@/lib/routes";
import { productCopy, shared } from "@/components/marketing/copy";
import { imagery, photo, sectionCopy } from "@/components/marketing/copy-sections";
import { ProductSwitch } from "@/components/marketing/ProductSwitch";
import { useReveal } from "@/components/marketing/useReveal";
import { cn } from "@/lib/utils";

/**
 * VERSION E2 — photograph-led.
 *
 * Method taken from the anti-slop-design demos (horai, calyx), read rather than
 * recalled: a real photograph carries the hero at full bleed, display type sits
 * directly on it in paper-white with roman and italic mixed inside one headline,
 * and a mono micro-label anchors the corner. No card, no scrim panel, no
 * "hero illustration".
 *
 * Photographs are verified-existing Unsplash IDs, each one looked at before it
 * was chosen. See copy-sections.ts.
 */

const pathForProduct: Record<ProductKey, string> = { leads: "/leads", support: "/support" };

function Display({ text: value, accentClass = "italic-disp text-ochre" }: Readonly<{ text: string; accentClass?: string }>) {
  return (
    <>
      {value.split(/\*([^*]+)\*/g).map((part, i) =>
        i % 2 === 1 ? (
          <span key={i} className={accentClass}>
            {part}
          </span>
        ) : (
          <span key={i}>{part}</span>
        )
      )}
    </>
  );
}

function Label({ children, tone = "ink" }: Readonly<{ children: React.ReactNode; tone?: "ink" | "paper" }>) {
  return (
    <p className={cn("text-[0.8125rem] font-medium tracking-[0.02em]", tone === "ink" ? "text-ink/45" : "text-paper/60")}>
      {children}
    </p>
  );
}

export function LandingPhoto({
  initial,
  leadsDemo,
  supportDemo
}: Readonly<{ initial: ProductKey; leadsDemo: React.ReactNode; supportDemo: React.ReactNode }>) {
  const { text, locale, toggleLocale } = useLocale();
  const [product, setProduct] = useState<ProductKey>(initial);
  const demoRef = useRef<HTMLDivElement | null>(null);

  useReveal();

  useEffect(() => {
    const next = pathForProduct[product];
    if (window.location.pathname !== next) window.history.replaceState(null, "", next);
  }, [product]);

  const scrollToDemo = useCallback(() => {
    demoRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
  }, []);

  const copy = productCopy[product];
  const sec = sectionCopy[product];

  return (
    <div className="min-h-screen bg-paper text-ink">
      <a
        href="#demo"
        className="focus-ring sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-50 focus:rounded-input focus:bg-ink focus:px-4 focus:py-2 focus:text-paper"
      >
        {text(shared.skipToContent)}
      </a>

      {/* Header sits over the photograph, so it carries no ground of its own. */}
      <header className="absolute inset-x-0 top-0 z-30">
        <div className="mx-auto flex max-w-[1480px] items-center justify-between gap-4 px-6 py-5 md:px-10">
          <Link href="/" className="focus-ring inline-flex min-h-11 items-center rounded-input text-paper">
            <Logo tone="paper" />
          </Link>
          <div className="flex items-center gap-1 sm:gap-2">
            <button
              type="button"
              onClick={toggleLocale}
              className="focus-ring min-h-11 rounded-input px-3 text-sm font-medium text-paper/70 transition-colors hover:text-paper"
            >
              {locale === "sv" ? "EN" : "SV"}
            </button>
            <Link
              href="/login"
              className="focus-ring inline-flex min-h-11 items-center rounded-input px-3 text-sm font-medium text-paper/70 transition-colors hover:text-paper"
            >
              {text(shared.navLogin)}
            </Link>
            <a
              href="mailto:hej@snajp.se"
              className="focus-ring hidden min-h-11 items-center rounded-input border border-paper/35 px-5 text-sm font-semibold text-paper transition-colors hover:bg-paper hover:text-ink sm:inline-flex"
            >
              {text(shared.secondaryCta)}
            </a>
          </div>
        </div>
      </header>

      <main id="main">
        {/* HERO. The photograph is the design. Type sits on it directly. */}
        <section className="relative min-h-[92vh] overflow-hidden">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src={photo(imagery.hero.src)}
            alt={text(imagery.hero.alt)}
            className="absolute inset-0 h-full w-full bg-ink object-cover object-center"
            fetchPriority="high"
          />
          {/* Two scrims: one for the header, one carrying the headline block. */}
          <div
            className="absolute inset-0"
            aria-hidden="true"
            style={{
              background:
                "linear-gradient(to bottom, oklch(var(--ink) / 0.55) 0%, oklch(var(--ink) / 0.18) 28%, oklch(var(--ink) / 0.30) 55%, oklch(var(--ink) / 0.82) 100%)"
            }}
          />

          <div className="relative mx-auto flex min-h-[92vh] max-w-[1480px] flex-col justify-end px-6 pb-14 pt-32 md:px-10 md:pb-20">
            <div className="max-w-[min(100%,980px)]">
              <p className="font-display text-[clamp(2.25rem,5.9vw,5.75rem)] font-semibold leading-[0.99] tracking-[-0.035em] text-paper">
                <Display text={text(copy.headline)} />
              </p>
            </div>

            <div className="mt-10 grid grid-cols-12 gap-y-8 lg:gap-x-10">
              <div className="col-span-12 lg:col-span-5">
                <p className="max-w-[46ch] text-[1.0625rem] leading-[1.65] text-paper/85">
                  {text(copy.lede)}
                </p>
                <div className="mt-8 flex flex-wrap items-center gap-3">
                  <button
                    type="button"
                    onClick={scrollToDemo}
                    className="focus-ring inline-flex min-h-12 items-center rounded-input bg-paper px-6 text-[0.9375rem] font-semibold text-ink transition-colors hover:bg-paper2"
                  >
                    {text(copy.cta)}
                  </button>
                  <a
                    href="mailto:hej@snajp.se"
                    className="focus-ring inline-flex min-h-12 items-center rounded-input border border-paper/40 px-6 text-[0.9375rem] font-semibold text-paper transition-colors hover:border-paper"
                  >
                    {text(shared.secondaryCta)}
                  </a>
                </div>
              </div>

              <div className="col-span-12 self-end lg:col-span-3 lg:col-start-10">
                <div className="font-display text-[1.5rem] leading-[1.15] tracking-[-0.02em] text-paper">
                  <ProductSwitch value={product} onChange={setProduct} tone="paper" />
                </div>
                <div className="mt-4 border-t border-paper/25 pt-3">
                  {/* Jurisdiction, not address. The two offices are named in the
                      place section; four items would wrap in this column. */}
                  <Label tone="paper">Sverige · GDPR · RLS</Label>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* PROBLEM. Named before the solution is offered. */}
        <section className="border-b border-ink/12">
          <div className="mx-auto max-w-[1480px] px-6 py-24 md:px-10 md:py-32">
            <div className="grid grid-cols-12 gap-y-10 lg:gap-x-12">
              <div className="col-span-12 lg:col-span-7">
                <Label>{text(sec.problemLabel)}</Label>
                <h2 className="rise mt-5 max-w-[16ch] font-display text-[clamp(2.25rem,5vw,4rem)] font-semibold leading-[1.02] tracking-[-0.03em]">
                  <Display text={text(sec.problemHeading)} />
                </h2>
              </div>
              <div className="col-span-12 lg:col-span-4 lg:col-start-9">
                <p className="rise rise-1 text-[1.0625rem] leading-[1.7] text-ink/75">{text(sec.problemBody)}</p>
                <ul className="mt-8">
                  {sec.problemPoints.map((point) => (
                    <li key={point.sv} className="hrule py-4 text-[0.9375rem] leading-[1.55] text-ink/65">
                      {text(point)}
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          </div>
        </section>


        {/* STATEMENT. One line, a photograph almost fully darkened behind it.
            The page needs a moment that is not information. */}
        <section className="relative overflow-hidden">
          <div
            className="parallax absolute inset-0 bg-ink"
            aria-hidden="true"
            style={{ backgroundImage: `url(${photo(imagery.street.src)})` }}
          />
          <div
            className="absolute inset-0"
            aria-hidden="true"
            style={{ background: "linear-gradient(to bottom, oklch(var(--ink) / 0.93), oklch(var(--ink) / 0.86))" }}
          />
          <div className="relative mx-auto max-w-[1480px] px-6 py-28 text-center md:px-10 md:py-40">
            <p className="text-[0.8125rem] font-medium tracking-[0.14em] text-ochre">
              {text(sec.statementLabel).toUpperCase()}
            </p>
            <p className="rise mx-auto mt-8 max-w-[20ch] font-display text-[clamp(2rem,5.2vw,4.5rem)] font-semibold leading-[1.12] tracking-[-0.005em] text-paper">
              {text(sec.statement)}
            </p>
          </div>
        </section>

        {/* DEMO. */}
        <section id="demo" ref={demoRef} className="scroll-mt-16 bg-paper2/45">
          <div className="mx-auto max-w-[1480px] px-6 py-24 md:px-10 md:py-28">
            <div className="max-w-[46ch]">
              <h2 className="font-display text-[clamp(1.875rem,3.6vw,2.875rem)] font-semibold leading-[1.06] tracking-[-0.028em]">
                <Display text={text(copy.demoHeading)} />
              </h2>
              <p className="mt-4 text-[1.0625rem] leading-[1.65] text-ink/70">{text(copy.demoLede)}</p>
            </div>
            <div className="mt-10 overflow-hidden rounded-panel border border-ink/12 bg-paper">
              <div className="flex items-center justify-between gap-4 border-b border-ink/10 bg-paper2/60 px-5 py-3.5">
                <span className="text-[0.8125rem] font-medium tracking-[0.02em] text-ink/55">
                  {product === "leads" ? "Email Studio" : "Snajp Support"}
                </span>
                {/* No status claim here: the support chat reports its own mode,
                    and the backend may be in simulation. Two sources of truth on
                    one panel is one too many. */}
                <span className="text-[0.8125rem] text-ink/40">
                  {text({ sv: "Interaktiv demo", en: "Interactive demo" })}
                </span>
              </div>
              <div className="p-4 sm:p-6 md:p-8">
              {productKeys.map((key) => (
                <div
                  key={key}
                  id={`product-panel-${key}`}
                  role="tabpanel"
                  aria-labelledby={`product-tab-${key}`}
                  hidden={key !== product}
                >
                  {key === "leads" ? leadsDemo : supportDemo}
                </div>
              ))}
              </div>
            </div>
            {/* Label renders its own <p>, so the wrapper is a div. It was a <p>
                and nested paragraphs are invalid HTML: React bailed out of
                hydration and re-rendered the whole page on the client. */}
            <div className="mt-4"><Label>{text(copy.exampleNote)}</Label></div>
          </div>
        </section>

        {/* PLACE. Photograph and copy share the row; the image is content here,
            not decoration, so it carries a real alt. */}
        <section>
          <div className="mx-auto grid max-w-[1480px] grid-cols-12 items-center gap-y-10 px-6 py-24 md:px-10 md:py-32 lg:gap-x-14">
            <figure className="col-span-12 lg:col-span-7 lg:-ml-6 xl:-ml-10">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src={photo(imagery.street.src)}
                alt={text(imagery.street.alt)}
                loading="lazy"
                className="h-[380px] w-full rounded-panel bg-paper2 object-cover md:h-[600px] lg:rounded-l-none"
              />
            </figure>
            <div className="col-span-12 lg:col-span-4 lg:col-start-9">
              <Label>{text(sec.placeLabel)}</Label>
              <h2 className="rise mt-5 max-w-[15ch] font-display text-[clamp(2rem,4.2vw,3.25rem)] font-semibold leading-[1.04] tracking-[-0.03em]">
                <Display text={text(sec.placeHeading)} />
              </h2>
              <p className="mt-6 max-w-[44ch] text-[1.0625rem] leading-[1.7] text-ink/75">
                {text(sec.placeBody)}
              </p>
            </div>
          </div>
        </section>

        {/* STEPS. */}
        <section className="border-t border-ink/15">
          <div className="mx-auto max-w-[1480px] px-6 py-24 md:px-10 md:py-28">
            <h2 className="rise max-w-[20ch] font-display text-[clamp(1.875rem,3.6vw,2.875rem)] font-semibold leading-[1.06] tracking-[-0.028em]">
              <Display text={text(copy.stepsHeading)} />
            </h2>
            <div className="mt-12 grid grid-cols-1 gap-x-12 md:grid-cols-3">
              {copy.steps.map((step, index) => (
                <div key={step.title.sv} className="rise hrule py-8 md:py-10">
                  <div className="grid grid-cols-[auto_1fr] gap-x-5">
                    <span className="numeral text-[clamp(2.5rem,4vw,3.5rem)]">
                      {String(index + 1).padStart(2, "0")}
                    </span>
                    <div className="min-w-0">
                      <h3 className="font-display text-[1.3125rem] font-semibold leading-tight tracking-[-0.015em]">
                        {text(step.title)}
                      </h3>
                      <p className="mt-2.5 text-[0.9375rem] leading-[1.6] text-ink/70">{text(step.body)}</p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* DIVIDER. A facade of identical windows under a heavy scrim: the flat
            run of text sections needed one more break, and the image rhymes with
            "the same email to a hundred companies". */}
        <section className="relative h-[220px] overflow-hidden md:h-[300px]">
          <div
            className="parallax absolute inset-0 bg-seal"
            aria-hidden="true"
            style={{ backgroundImage: `url(${photo(imagery.grid.src)})` }}
          />
          <div
            className="absolute inset-0"
            aria-hidden="true"
            style={{
              background:
                "linear-gradient(to bottom, oklch(var(--ink) / 0.90), oklch(var(--ink) / 0.80)), radial-gradient(120% 100% at 50% 100%, oklch(var(--ochre) / 0.22) 0%, transparent 70%)"
            }}
          />
        </section>

        {/* OBJECTIONS. Real questions, answered plainly. */}
        <section className="border-t border-ink/12 bg-paper2/40">
          <div className="mx-auto max-w-[1480px] px-6 py-24 md:px-10 md:py-32">
            <div className="grid grid-cols-12 gap-y-12 lg:gap-x-14">
              <div className="col-span-12 lg:col-span-4">
                <h2 className="rise max-w-[14ch] font-display text-[clamp(1.875rem,3.6vw,2.875rem)] font-semibold leading-[1.06] tracking-[-0.028em]">
                  <Display text={text(sec.objectionsHeading)} />
                </h2>
              </div>
              <dl className="col-span-12 lg:col-span-7 lg:col-start-6">
                {sec.objections.map((item) => (
                  <div key={item.q.sv} className="rise hrule py-7 first:border-t-0 first:pt-0">
                    <dt className="font-display text-[1.25rem] font-semibold leading-snug tracking-[-0.015em]">
                      {text(item.q)}
                    </dt>
                    <dd className="mt-3 max-w-[62ch] text-[1rem] leading-[1.7] text-ink/70">
                      {text(item.a)}
                    </dd>
                  </div>
                ))}
              </dl>
            </div>
          </div>
        </section>

        {/* LIMITS on ink, then the close. */}
        <section className="bg-ink text-paper">
          <div className="mx-auto max-w-[1480px] px-6 py-24 md:px-10 md:py-28">
            <h2 className="max-w-[22ch] font-display text-[clamp(1.875rem,3.6vw,2.875rem)] font-semibold leading-[1.06] tracking-[-0.028em]">
              {text(copy.limitsHeading)}
            </h2>
            <ul className="mt-10 grid grid-cols-1 gap-x-14 md:grid-cols-2">
              {copy.limits.map((limit, index) => (
                <li key={limit.sv} className="flex gap-5 border-t border-paper/15 py-5">
                  <span className="numeral shrink-0 text-[1.5rem]">
                    {String(index + 1).padStart(2, "0")}
                  </span>
                  <span className="text-[1rem] leading-[1.6] text-paper/75">{text(limit)}</span>
                </li>
              ))}
            </ul>
          </div>
        </section>

        <section className="relative overflow-hidden">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src={photo(imagery.desk.src)}
            alt={text(imagery.desk.alt)}
            loading="lazy"
            className="absolute inset-0 h-full w-full bg-paper2 object-cover"
          />
          <div
            className="absolute inset-0"
            aria-hidden="true"
            style={{ background: "linear-gradient(to right, oklch(var(--paper) / 0.94) 0%, oklch(var(--paper) / 0.72) 38%, oklch(var(--paper) / 0.10) 78%, transparent 100%)" }}
          />
          <div className="relative mx-auto min-h-[520px] max-w-[1480px] px-6 py-28 md:min-h-[600px] md:px-10 md:py-36">
            <div className="max-w-[30ch]">
              <h2 className="font-display text-[clamp(2.25rem,5vw,3.75rem)] font-semibold leading-[1.02] tracking-[-0.03em]">
                <Display text={text(shared.closingHeading)} />
              </h2>
              <p className="mt-6 max-w-[46ch] text-[1.0625rem] leading-[1.7] text-ink/80">
                {text(shared.closingBody)}
              </p>
              <a
                href="mailto:hej@snajp.se"
                className="focus-ring mt-9 inline-flex min-h-12 items-center rounded-input bg-ink px-7 text-[1rem] font-semibold text-paper transition-colors hover:bg-ink2"
              >
                {text(shared.closingCta)}
              </a>
            </div>
          </div>
        </section>
      </main>

      <footer className="border-t border-ink/12">
        <div className="mx-auto flex max-w-[1480px] flex-wrap items-center justify-between gap-4 px-6 py-8 md:px-10">
          <Logo compact />
          <Label>{text(shared.footerNote)}</Label>
        </div>
      </footer>
    </div>
  );
}
