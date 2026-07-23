"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";
import { Logo } from "@/components/Logo";
import { useLocale } from "@/lib/i18n";
import { appRoutes } from "@/lib/routes";
import { businessContext, companies } from "@/lib/mock-data";
import { cn } from "@/lib/utils";

const commandSuggestions = [
  "Hitta byggbolag i Malmö med expansionssignal",
  "Skriv mediumvariant för Byggkompaniet Syd",
  "Visa leads där reply rate ligger över 14 %",
  "Pausa uppföljning om kontakt har svarat"
];

export function AppShell({ children }: Readonly<{ children: React.ReactNode }>) {
  const pathname = usePathname();
  const { t, text, locale, toggleLocale } = useLocale();
  const [paletteOpen, setPaletteOpen] = useState(false);

  return (
    <div className="min-h-screen bg-paper text-ink">
      <header className="sticky top-0 z-30 border-b border-ink/15 bg-paper/88 backdrop-blur-md">
        <div className="mx-auto grid max-w-[1480px] grid-cols-12 items-center gap-x-6 px-6 py-4 md:px-8">
          <Link href="/" className="col-span-8 min-w-0 focus-ring md:col-span-3">
            <Logo />
          </Link>
          <nav className="kicker col-span-12 order-3 mt-4 flex min-w-0 gap-5 overflow-x-auto text-ink/70 md:order-none md:col-span-6 md:mt-0 md:justify-center md:overflow-visible">
            {appRoutes.slice(0, 9).map((route) => {
              const active = pathname === route.href || pathname.startsWith(`${route.href}/`);
              return (
                <Link
                  key={route.href}
                  href={route.href}
                  className={cn("whitespace-nowrap transition hover:text-ochre", active ? "text-ochre" : "")}
                >
                  {t(route.labelKey)}
                </Link>
              );
            })}
          </nav>
          <div className="col-span-4 flex min-w-0 items-center justify-end gap-2 md:col-span-3">
            <button
              type="button"
              onClick={toggleLocale}
              className="focus-ring border border-ink/15 bg-paper2 px-3 py-2 font-mono text-xs font-medium uppercase tracking-[0.16em] text-ink transition hover:border-ochre hover:text-ochre"
            >
              {locale === "sv" ? "EN" : "SV"}
            </button>
            <button
              type="button"
              onClick={() => setPaletteOpen(true)}
              className="focus-ring hidden border border-ink/15 bg-ink px-4 py-2 font-mono text-xs uppercase tracking-[0.16em] text-paper transition hover:bg-ochre hover:text-ink md:inline-flex"
            >
              Command
            </button>
          </div>
        </div>
      </header>

      <div className="border-b border-ink/15">
        <div className="kicker mx-auto grid max-w-[1480px] grid-cols-12 gap-x-8 px-6 py-4 text-mineral md:px-8">
          <div className="col-span-12 min-w-0 md:col-span-3">Business context</div>
          <div className="col-span-12 mt-2 min-w-0 break-words md:col-span-5 md:mt-0">{text(businessContext.icp)}</div>
          <div className="col-span-12 mt-2 min-w-0 break-words md:col-span-4 md:mt-0 md:text-right">{text(companies[0].latestSignal)}</div>
        </div>
      </div>

      <main>{children}</main>

      {paletteOpen ? (
        <div className="fixed inset-0 z-40 bg-ink/35 p-4 backdrop-blur-sm" onClick={() => setPaletteOpen(false)}>
          <div
            className="mx-auto mt-20 max-w-3xl border border-ink/20 bg-paper shadow-lift"
            onClick={(event) => event.stopPropagation()}
          >
            <div className="grid grid-cols-12 border-b border-ink/15">
              <div className="kicker col-span-12 border-b border-ink/15 px-5 py-4 text-mineral md:col-span-3 md:border-b-0 md:border-r">
                Styr Snipra
              </div>
              <div className="col-span-12 md:col-span-9">
                <input
                  autoFocus
                  className="h-16 w-full bg-transparent px-5 text-[18px] outline-none placeholder:text-ink/35"
                  placeholder="Sök, analysera, skriv eller pausa..."
                />
              </div>
            </div>
            <div className="divide-y divide-ink/15">
              {commandSuggestions.map((item, index) => (
                <button
                  key={item}
                  type="button"
                  className="row grid w-full grid-cols-12 gap-x-6 px-5 py-4 text-left transition hover:bg-ochre/5"
                >
                  <span className="kicker col-span-2 text-mineral">0{index + 1}</span>
                  <span className="ticker col-span-10 text-[15px]">{item}</span>
                </button>
              ))}
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}

export function PageShell({
  kicker,
  title,
  description,
  children,
  action
}: Readonly<{ kicker: string; title: string; description: string; children: React.ReactNode; action?: React.ReactNode }>) {
  return (
    <AppShell>
      <section className="mx-auto max-w-[1480px] px-6 py-12 md:px-8 md:py-16">
        <div className="grid grid-cols-12 gap-x-8">
          <aside className="col-span-12 min-w-0 md:col-span-3">
            <div className="kicker text-mineral">{kicker}</div>
            <div className="rule mt-3 text-ink" />
            {action ? <div className="mt-6">{action}</div> : null}
          </aside>
          <div className="col-span-12 mt-8 min-w-0 md:col-span-9 md:mt-0">
            <h1 className="max-w-[980px] break-words font-display text-[clamp(2.15rem,10vw,7rem)] leading-[0.92] tighten">{title}</h1>
            <p className="mt-7 max-w-[62ch] text-[17px] leading-[1.65] text-ink/75">{description}</p>
          </div>
        </div>
        <div className="mt-14">{children}</div>
      </section>
    </AppShell>
  );
}
