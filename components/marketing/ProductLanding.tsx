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

export function ProductLanding({
  initial,
  leadsDemo,
  supportDemo
}: Readonly<{ initial: ProductKey; leadsDemo: React.ReactNode; supportDemo: React.ReactNode }>) {
  const { text, locale, toggleLocale } = useLocale();
  const [product, setProduct] = useState<ProductKey>(initial);
  const demoRef = useRef<HTMLDivElement | null>(null);

  // Deep links stay shareable without a navigation: switching rewrites the path
  // in place so /leads and /support always reflect what is on screen.
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

      <header className="sticky top-0 z-30 bg-paper/80 backdrop-blur-xl">
        <div className="mx-auto flex max-w-[1200px] items-center justify-between gap-4 px-5 py-4 md:px-8">
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
        {/* Hero. The daylight wash is a gradient, never a blurred element: the root
            clips overflow and a positioned blur would be cut off. */}
        <section className="relative overflow-hidden">
          <div className="daylight" aria-hidden="true" />
          <div className="relative mx-auto max-w-[1200px] px-5 pb-16 pt-16 md:px-8 md:pb-24 md:pt-28">
            {/* leading >= 1.1 plus bottom reserve: the italic product word carries a
                descender ("Support"), and at 0.98 the glyph box overflowed the
                heading by 11px. */}
            <h1 className="font-display text-[clamp(2.75rem,9vw,5.75rem)] font-semibold leading-[1.1] tracking-[-0.03em] pb-1">
              <span className="text-ink">Snajp</span>{" "}
              <ProductSwitch value={product} onChange={setProduct} />
            </h1>

            <div className="mt-8 max-w-2xl md:mt-10">
              <p
                key={`${product}-headline`}
                className="reveal text-[clamp(1.5rem,3.4vw,2.35rem)] font-semibold leading-[1.15] tracking-[-0.02em]"
              >
                {text(copy.headline)}
              </p>
              <p key={`${product}-lede`} className="reveal reveal-delay-1 mt-5 text-[1.0625rem] leading-[1.65] text-ink/70">
                {text(copy.lede)}
              </p>
            </div>

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
                className="focus-ring inline-flex min-h-12 items-center rounded-input border border-ink/15 px-6 text-[0.9375rem] font-semibold text-ink transition-colors hover:border-ink/35"
              >
                {text(shared.secondaryCta)}
              </a>
            </div>

          </div>
        </section>

        {/* Demo. The proof on this page is the working product, so it gets the
            largest surface and the strongest plane. */}
        <section id="demo" ref={demoRef} className="scroll-mt-20">
          <div className="mx-auto max-w-[1200px] px-5 py-16 md:px-8 md:py-24">
            <h2 className="max-w-2xl text-[clamp(1.5rem,3.2vw,2.25rem)] font-semibold leading-[1.15] tracking-[-0.02em]">
              {text(copy.demoHeading)}
            </h2>
            <p className="mt-4 max-w-2xl text-[1.0625rem] leading-[1.65] text-ink/70">{text(copy.demoLede)}</p>

            <div className="plane-panel mt-10 p-4 sm:p-6 md:p-8">
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

        {/* How it works. Wide rows rather than a three-card triad: the card grid
            with an icon on top is the most generic module in the category. */}
        <section className="border-t border-ink/10">
          <div className="mx-auto max-w-[1200px] px-5 py-16 md:px-8 md:py-24">
            <ol className="space-y-px">
              {copy.steps.map((step, index) => (
                <li
                  key={step.title.sv}
                  className="grid grid-cols-1 gap-3 rounded-card bg-paper2/60 px-5 py-8 md:grid-cols-12 md:gap-8 md:px-8 md:py-10"
                >
                  <span className="text-[0.9375rem] font-semibold tabular-nums text-ochre md:col-span-2">
                    {String(index + 1).padStart(2, "0")}
                  </span>
                  <h3 className="text-[1.25rem] font-semibold leading-tight tracking-[-0.01em] md:col-span-4">
                    {text(step.title)}
                  </h3>
                  <p className="text-[1.0625rem] leading-[1.65] text-ink/70 md:col-span-6">{text(step.body)}</p>
                </li>
              ))}
            </ol>
          </div>
        </section>

        {/* Limits, on an inverted plane. A page with no customer proof earns trust
            by being specific about what the product refuses to do. */}
        <section className="bg-ink text-paper">
          <div className="mx-auto max-w-[1200px] px-5 py-16 md:px-8 md:py-24">
            <h2 className="text-[clamp(1.5rem,3.2vw,2.25rem)] font-semibold leading-[1.15] tracking-[-0.02em]">
              {text(copy.limitsHeading)}
            </h2>
            <ul className="mt-10 grid grid-cols-1 gap-x-12 gap-y-6 md:grid-cols-2">
              {copy.limits.map((limit) => (
                <li key={limit.sv} className="text-[1.0625rem] leading-[1.6] text-paper/75">
                  {text(limit)}
                </li>
              ))}
            </ul>
          </div>
        </section>

        <section>
          <div className="mx-auto max-w-[1200px] px-5 py-16 md:px-8 md:py-24">
            <div className="max-w-2xl">
              <h2 className="text-[clamp(1.5rem,3.2vw,2.25rem)] font-semibold leading-[1.15] tracking-[-0.02em]">
                {text(shared.closingHeading)}
              </h2>
              <p className="mt-4 text-[1.0625rem] leading-[1.65] text-ink/70">{text(shared.closingBody)}</p>
              <a
                href="mailto:hej@snajp.se"
                className="focus-ring mt-8 inline-flex min-h-12 items-center rounded-input bg-ink px-6 text-[0.9375rem] font-semibold text-paper transition-colors hover:bg-ink2"
              >
                {text(shared.closingCta)}
              </a>
            </div>
          </div>
        </section>
      </main>

      <footer className="border-t border-ink/10">
        <div className="mx-auto flex max-w-[1200px] flex-wrap items-center justify-between gap-4 px-5 py-8 md:px-8">
          <Logo compact />
          <p className="text-sm text-ink/45">{text(shared.footerNote)}</p>
        </div>
      </footer>
    </div>
  );
}
