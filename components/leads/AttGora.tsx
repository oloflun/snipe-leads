"use client";

import { useDashboard } from "@/components/dashboard/DashboardContext";
import { IrisGranskning } from "@/components/leads/IrisGranskning";
import { IrisInkorg } from "@/components/leads/IrisInkorg";
import { Dashboard } from "@/components/snajp/Dashboard";
import { useLocale, type Localized } from "@/lib/i18n";

/**
 * Att göra — allt som väntar på ett beslut från dig, från alla agenter
 * (Snajp Suite 2026-10-03).
 *
 * Ersätter Iris › Granskning, Iris › Inkorg och Kundtjänst › Att hantera:
 * tre ställen för samma fråga, vad behöver jag göra nu? Varje del är en
 * befintlig vy med sina egna åtgärder (godkänn, avvisa, ta över); sidan ger
 * dem bara en gemensam plats och visar bara agenter arbetsytan har.
 */
export function AttGora({ demo = false }: Readonly<{ demo?: boolean }>) {
  const { products } = useDashboard();
  const iris = products.includes("leads");
  const support = products.includes("support");

  return (
    <div className="grid gap-12">
      {support ? (
        <Del id="kundtjanst-utkast" rubrik={{ sv: "Kundtjänst: svar att godkänna", en: "Customer service: replies to approve" }} forst>
          <Dashboard lager="vantar" demo={demo} />
        </Del>
      ) : null}
      {support ? (
        <Del id="kundtjanst-eskalerat" rubrik={{ sv: "Kundtjänst: eskalerat till dig", en: "Customer service: escalated to you" }}>
          <Dashboard lager="eskalerade" demo={demo} />
        </Del>
      ) : null}
      {/* Larmen (migration 078): avvisade utskick, systemfel. Skilda från
          eskaleringarna, som är kundärenden agenten lämnat över. */}
      {support ? (
        <Del id="kundtjanst-larm" rubrik={{ sv: "Kundtjänst: larm", en: "Customer service: alerts" }}>
          <Dashboard lager="att_hantera" demo={demo} />
        </Del>
      ) : null}
      {iris ? (
        <Del id="iris-utkast" rubrik={{ sv: "Iris: utkast att godkänna", en: "Iris: drafts to approve" }} forst={!support}>
          <IrisGranskning demo={demo} />
        </Del>
      ) : null}
      {/* Leadsmejlen kräver en brevlåda och en session; demon har ingen. */}
      {iris && !demo ? (
        <Del id="iris-mejl" rubrik={{ sv: "Mejl från leads", en: "Email from leads" }}>
          <IrisInkorg />
        </Del>
      ) : null}
    </div>
  );
}

function Del({
  id,
  rubrik,
  forst = false,
  children
}: Readonly<{ id: string; rubrik: Localized; forst?: boolean; children: React.ReactNode }>) {
  const { text } = useLocale();
  return (
    <section aria-labelledby={id} className={forst ? undefined : "border-t border-ink/15 pt-8"}>
      <h2 id={id} className="mb-5 text-[1.125rem] font-semibold tracking-[-0.01em] text-ink">
        {text(rubrik)}
      </h2>
      {children}
    </section>
  );
}
