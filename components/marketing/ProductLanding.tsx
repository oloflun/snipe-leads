"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { Logo } from "@/components/Logo";
import { useLocale } from "@/lib/i18n";
import type { ProductKey } from "@/lib/routes";
import { productKeys } from "@/lib/routes";
import { productCopy, shared } from "@/components/marketing/copy";
import { ProductSwitch } from "@/components/marketing/ProductSwitch";
import { cn } from "@/lib/utils";

const pathForProduct: Record<ProductKey, string> = {
  leads: "/leads",
  support: "/support"
};

/**
 * Copy may mark one word per headline with *asterisks*. That word renders italic
 * ochre. It is the page's single expressive typographic move, and it is what the
 * first redesign pass was missing: ochre appeared 0 times at display scale, against
 * 30 times in the editorial draft it replaced.
 */
function Display({ text: value, className }: Readonly<{ text: string; className?: string }>) {
  const parts = value.split(/\*([^*]+)\*/g);
  return (
    <span className={className}>
      {parts.map((part, i) =>
        i % 2 === 1 ? (
          <span key={i} className="disp-accent">
            {part}
          </span>
        ) : (
          <span key={i}>{part}</span>
        )
      )}
    </span>
  );
}

export function ProductLanding({
  initial,
  leadsDemo,
  supportDemo
}: Readonly<{ initial: ProductKey; leadsDemo: React.ReactNode; supportDemo: React.ReactNode }>) {
  const { text, locale, toggleLocale } = useLocale();
  const [product, setProduct] = useState<ProductKey>(initial);
  const demoRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    const next = pathForProduct[product];
    if (window.location.pathname !== next) {
      window.history.replaceState(null, "", next);
    }
  }, [product]);

  const scrollToDemo = useCallback(() => {
    demoRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
  }, []);

  const copy = productCopy[product];

  return (
    <div className="min-h-screen bg-paper text-ink">
      <a
        href="#demo"
        className="focus-ring sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-50 focus:rounded-input focus:bg-ink focus:px-4 focus:py-2 focus:text-paper"
      >
        {text(shared.skipToContent)}
      </a>

      <header className="sticky top-0 z-30 border-b border-ink/10 bg-paper/85 backdrop-blur-xl">
        <div className="mx-auto flex max-w-[1320px] items-center justify-between gap-4 px-5 py-4 md:px-10">
          <Link href="/" className="focus-ring inline-flex min-h-11 items-center rounded-input">
            <Logo />
          </Link>
          <div className="flex items-center gap-1 sm:gap-2">
            <button
              type="button"
              onClick={toggleLocale}
              className="focus-ring min-h-11 rounded-input px-3 text-sm font-medium text-ink/60 transition-colors hover:text-ink"
            >
              {locale === "sv" ? "EN" : "SV"}
            </button>
            <Link
              href="/login"
              className="focus-ring inline-flex min-h-11 items-center rounded-input px-3 text-sm font-medium text-ink/60 transition-colors hover:text-ink"
            >
              {text(shared.navLogin)}
            </Link>
            <a
              href="mailto:hej@snajp.se"
              className="focus-ring hidden min-h-11 items-center rounded-input bg-ink px-5 text-sm font-semibold text-paper transition-colors hover:bg-ink2 sm:inline-flex"
            >
              {text(shared.secondaryCta)}
            </a>
          </div>
        </div>
      </header>

      <main id="main">
        {/* HERO. Two real columns. The right rail carries the honest-proof list,
            which is where the editorial draft put its metrics: same compositional
            weight, true content instead of invented numbers. */}
        <section className="relative overflow-hidden">
          <div className="daylight" aria-hidden="true" />
          <div className="relative mx-auto max-w-[1320px] px-5 pb-20 pt-14 md:px-10 md:pb-28 md:pt-20">
            <h1 className="font-display text-[clamp(2rem,4.2vw,3rem)] font-semibold leading-[1.12] tracking-[-0.03em] pb-1">
              <span className="text-ink">Snajp</span>{" "}
              <ProductSwitch value={product} onChange={setProduct} />
            </h1>

            <div className="mt-10 grid grid-cols-12 items-start gap-y-14 md:mt-16 lg:gap-x-10">
              <div className="col-span-12 lg:col-span-7">
                <p
                  key={`${product}-headline`}
                  className="reveal font-display text-[clamp(2.5rem,5.4vw,4.25rem)] font-semibold leading-[1.05] tracking-[-0.03em]"
                >
                  <Display text={text(copy.headline)} />
                </p>
                <p
                  key={`${product}-lede`}
                  className="reveal reveal-delay-1 mt-7 max-w-[52ch] text-[1.125rem] leading-[1.6] text-ink/70"
                >
                  {text(copy.lede)}
                </p>

                <div className="mt-9 flex flex-wrap items-center gap-3">
                  <button
                    type="button"
                    onClick={scrollToDemo}
                    className="focus-ring inline-flex min-h-12 items-center rounded-input bg-ink px-6 text-[0.9375rem] font-semibold text-paper transition-colors hover:bg-ink2"
                  >
                    {text(copy.cta)}
                  </button>
                  <a
                    href="mailto:hej@snajp.se"
                    className="focus-ring inline-flex min-h-12 items-center rounded-input border border-ink/20 px-6 text-[0.9375rem] font-semibold text-ink transition-colors hover:border-ink/45"
                  >
                    {text(shared.secondaryCta)}
                  </a>
                </div>
              </div>

              {/* Right rail. Hairline-separated rows with display numerals: the
                  structural line language the first pass deleted. */}
              <aside className="col-span-12 lg:col-span-4 lg:col-start-9">
                <p className="text-[0.8125rem] font-medium text-ink/45">{text(copy.limitsHeading)}</p>
                <ul className="mt-5">
                  {copy.limits.map((limit, index) => (
                    <li
                      key={limit.sv}
                      className="hrule flex gap-5 py-4 first:border-t-0 first:pt-0"
                    >
                      <span className="numeral shrink-0 text-[1.75rem]">
                        {String(index + 1).padStart(2, "0")}
                      </span>
                      <span className="text-[0.9375rem] leading-[1.5] text-ink/75">{text(limit)}</span>
                    </li>
                  ))}
                </ul>
              </aside>
            </div>
          </div>
        </section>

        {/* DEMO. Breaks wider than the text column and sits on a hairline frame,
            so the product surface is the page's main visual rather than a panel
            buried below three screens of prose. */}
        <section id="demo" ref={demoRef} className="scroll-mt-20 border-t border-ink/10 bg-paper2/40">
          <div className="mx-auto max-w-[1320px] px-5 pb-24 pt-16 md:px-10 md:pb-32 md:pt-20">
            {/* Stacked, not split. The "big headline left, small paragraph right"
                section header is a banned default: one focused message per head. */}
            <div className="max-w-[46ch]">
              <h2 className="font-display text-[clamp(1.75rem,3vw,2.5rem)] font-semibold leading-[1.1] tracking-[-0.02em]">
                <Display text={text(copy.demoHeading)} />
              </h2>
              <p className="mt-4 text-[1.0625rem] leading-[1.6] text-ink/65">{text(copy.demoLede)}</p>
            </div>

            <div className="mt-10 rounded-panel border border-ink/12 bg-paper p-4 sm:p-6 md:p-8">
              {productKeys.map((key) => (
                <div
                  key={key}
                  id={`product-panel-${key}`}
                  role="tabpanel"
                  aria-labelledby={`product-tab-${key}`}
                  hidden={key !== product}
                  className={cn(key === product && "reveal")}
                >
                  {key === "leads" ? leadsDemo : supportDemo}
                </div>
              ))}
            </div>

            <p className="mt-4 text-sm text-ink/45">{text(copy.exampleNote)}</p>
          </div>
        </section>

        {/* HOW IT WORKS. Asymmetric spans and oversized ochre numerals rather than
            three identical bars. Padding deliberately heavier on top than bottom. */}
        <section>
          <div className="mx-auto max-w-[1320px] px-5 pb-20 pt-20 md:px-10 md:pb-24 md:pt-28">
            <div className="hrule-strong pt-10">
              <h2 className="max-w-[26ch] font-display text-[clamp(1.75rem,3.2vw,2.625rem)] font-semibold leading-[1.1] tracking-[-0.02em]">
                <Display text={text(copy.stepsHeading)} />
              </h2>
            </div>
            <ol className="mt-12">
              {copy.steps.map((step, index) => (
                <li
                  key={step.title.sv}
                  className="hrule grid grid-cols-12 items-baseline gap-y-2 py-9 last:border-b last:border-ink/14 md:gap-x-8 md:py-12"
                >
                  <span className="numeral col-span-12 text-[clamp(2.75rem,5vw,4rem)] md:col-span-1">
                    {String(index + 1).padStart(2, "0")}
                  </span>
                  <h3 className="col-span-12 font-display text-[1.375rem] font-semibold leading-tight tracking-[-0.015em] md:col-span-3">
                    {text(step.title)}
                  </h3>
                  <p className="col-span-12 max-w-[62ch] text-[1.0625rem] leading-[1.65] text-ink/70 md:col-span-8">
                    {text(step.body)}
                  </p>
                </li>
              ))}
            </ol>
          </div>
        </section>

        {/* CLOSE, inverted. The only full tonal break on the page. */}
        <section className="bg-ink text-paper">
          <div className="mx-auto max-w-[1320px] px-5 py-24 md:px-10 md:py-32">
            {/* Stacked centre. Every other section on the page is left-anchored;
                closing on a different composition stops the scroll reading as four
                repeats of one template, and makes the final action unmistakable. */}
            <div className="mx-auto max-w-[46ch] text-center">
              <h2 className="font-display text-[clamp(2.25rem,4.4vw,3.25rem)] font-semibold leading-[1.08] tracking-[-0.025em]">
                <Display text={text(shared.closingHeading)} />
              </h2>
              <p className="mx-auto mt-6 text-[1.0625rem] leading-[1.65] text-paper/70">
                {text(shared.closingBody)}
              </p>
              <a
                href="mailto:hej@snajp.se"
                className="focus-ring mt-9 inline-flex min-h-12 items-center rounded-input bg-paper px-7 text-[1rem] font-semibold text-ink transition-colors hover:bg-paper2"
              >
                {text(shared.closingCta)}
              </a>
            </div>
          </div>
        </section>
      </main>

      <footer className="border-t border-ink/10">
        <div className="mx-auto flex max-w-[1320px] flex-wrap items-center justify-between gap-4 px-5 py-8 md:px-10">
          <Logo compact />
          <p className="text-sm text-ink/45">{text(shared.footerNote)}</p>
        </div>
      </footer>
    </div>
  );
}
