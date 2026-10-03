"use client";

import { ArrowRight, Check } from "lucide-react";
import Link from "next/link";
import { PageShell } from "@/components/AppShell";
import { PAKET } from "@/lib/pricing";
import type { ProductKey } from "@/lib/routes";
import { useLocale, type Localized } from "@/lib/i18n";

/**
 * Vyn bakom en MÖRKLAGD menypost: agenten arbetsytan inte har.
 *
 * Klicket ska inte vara en 404 — posten står i menyn med flit (säljytan),
 * och den som klickar har just visat intresse. Vyn säger vad agenten gör,
 * vad den kostar och hur man provar eller lägger till den. Ingen grind
 * öppnas här: entitlementen sätts bara via paketbytet i Inställningar →
 * Plan (set_workspace_products), och tills dess svarar varje datayta för
 * agenten som förut.
 */

const AGENT_FOR_PRODUKT: Record<ProductKey, { paketId: string; demoVag: string; vad: Localized }> = {
  leads: {
    paketId: "leads",
    demoVag: "/demo/leads",
    vad: {
      sv: "Iris hittar rätt bolag för er, gör researchen och skriver första mejlet — ni läser igenom och godkänner innan något går ut.",
      en: "Iris finds the right companies for you, does the research and writes the first email. You read it through and approve it before anything goes out."
    }
  },
  support: {
    paketId: "support",
    demoVag: "/demo/support",
    vad: {
      sv: "Kundtjänstagenten svarar era kunder ur er egen kunskapsbas, dygnet runt, och lämnar över till en människa när det behövs.",
      en: "The support agent answers your customers from your own knowledge base, around the clock, and hands over to a person when needed."
    }
  },
  bookkeeping: {
    paketId: "bookkeeping",
    demoVag: "/demo/kvitton",
    vad: {
      sv: "Kvittohanteraren läser kvittona ur er inkorg, läser av belopp och moms, och exporterar färdigt underlag till bokföringen.",
      en: "The receipt handler reads the receipts from your inbox, reads amounts and VAT, and exports finished records to your bookkeeping."
    }
  }
};

export function AgentLast({ product }: Readonly<{ product: ProductKey }>) {
  const { locale, text } = useLocale();
  const agent = AGENT_FOR_PRODUKT[product];
  const paket = PAKET.find((p) => p.id === agent.paketId);
  if (!paket) return null;

  return (
    <PageShell title={paket.namn}>
      <p className="mb-8 text-[0.9375rem] text-ink-subtle">
        {text({ sv: "Ingår inte i ert paket ännu.", en: "Not included in your plan yet." })}
      </p>
      <div className="max-w-[720px]">
        <p className="max-w-[62ch] text-[1.0625rem] leading-[1.7] text-ink-muted">{text(agent.vad)}</p>

        <ul className="mt-8 max-w-[560px]">
          {paket.ingar.map((rad) => (
            <li
              key={rad.sv}
              className="flex items-center gap-3 border-t border-ink/15 py-3 text-[15px]"
            >
              <Check className="h-4 w-4 shrink-0 text-moss" aria-hidden />
              {text(rad)}
            </li>
          ))}
        </ul>

        <div className="mt-8 flex flex-wrap items-baseline gap-x-3 border-t border-ink/15 pt-6">
          {paket.prisPerManad === null ? (
            <span className="text-[1.0625rem] font-semibold">
              {text({ sv: "Pris vid kontakt", en: "Price on request" })}
            </span>
          ) : (
            <>
              <span className="text-[15px] text-ink-muted">{text({ sv: "från", en: "from" })}</span>
              <span className="font-display text-[2.5rem] font-semibold leading-none text-warning">
                {paket.prisPerManad.toLocaleString(locale === "en" ? "en-GB" : "sv-SE")}
              </span>
              <span className="text-[15px] text-ink-muted">{text({ sv: "kr/mån", en: "SEK/mo" })}</span>
            </>
          )}
          <span className="basis-full text-[14px] leading-6 text-ink-subtle">
            {text({
              sv: "Läggs till på ert befintliga paket — bytet gäller direkt, och er gratisperiod påverkas inte.",
              en: "Added to your current plan. The change applies right away and your free trial is not affected."
            })}
          </span>
        </div>

        <div className="mt-8 flex flex-wrap items-center gap-4">
          <Link
            href="/settings/billing"
            className="focus-ring inline-flex min-h-12 items-center gap-2 rounded-input bg-ink px-7 text-[0.9375rem] font-semibold text-paper transition-colors hover:bg-ink2"
          >
            {text({ sv: "Lägg till i ert paket", en: "Add to your plan" })}
            <ArrowRight className="h-4 w-4" aria-hidden />
          </Link>
          <a
            href={agent.demoVag}
            target="_blank"
            rel="noopener"
            className="focus-ring inline-flex min-h-12 items-center rounded-input border border-ink/15 px-6 text-[0.9375rem] font-medium text-ink transition-colors hover:border-ink/30"
          >
            {text({ sv: "Prova i demon först", en: "Try the demo first" })}
          </a>
        </div>
      </div>
    </PageShell>
  );
}
