import { ArrowRight, Check } from "lucide-react";
import Link from "next/link";
import { PageShell } from "@/components/AppShell";
import { PAKET } from "@/lib/pricing";
import type { ProductKey } from "@/lib/routes";

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

const AGENT_FOR_PRODUKT: Record<ProductKey, { paketId: string; demoVag: string; vad: string }> = {
  leads: {
    paketId: "leads",
    demoVag: "/demo/iris",
    vad: "Iris hittar rätt bolag för er, gör researchen och skriver första mejlet — ni läser igenom och godkänner innan något går ut."
  },
  support: {
    paketId: "support",
    demoVag: "/demo/support",
    vad: "Kundtjänstagenten svarar era kunder ur er egen kunskapsbas, dygnet runt, och lämnar över till en människa när det behövs."
  },
  bookkeeping: {
    paketId: "bookkeeping",
    demoVag: "/demo/kvitton",
    vad: "Kvittohanteraren läser kvittona ur er inkorg, läser av belopp och moms, och exporterar färdigt underlag till bokföringen."
  }
};

export function AgentLast({ product }: Readonly<{ product: ProductKey }>) {
  const agent = AGENT_FOR_PRODUKT[product];
  const paket = PAKET.find((p) => p.id === agent.paketId);
  if (!paket) return null;

  return (
    <PageShell kicker="Ingår inte i ert paket ännu" title={paket.namn}>
      <div className="max-w-[720px]">
        <p className="max-w-[62ch] text-[1.0625rem] leading-[1.7] text-ink-muted">{agent.vad}</p>

        <ul className="mt-8 max-w-[560px]">
          {paket.ingar.map((rad) => (
            <li
              key={rad.sv}
              className="flex items-center gap-3 border-t border-ink/15 py-3 text-[15px]"
            >
              <Check className="h-4 w-4 shrink-0 text-moss" aria-hidden />
              {rad.sv}
            </li>
          ))}
        </ul>

        <div className="mt-8 flex flex-wrap items-baseline gap-x-3 border-t border-ink/15 pt-6">
          {paket.prisPerManad === null ? (
            <span className="text-[1.0625rem] font-semibold">Pris vid kontakt</span>
          ) : (
            <>
              <span className="text-[15px] text-ink-muted">från</span>
              <span className="font-display text-[2.5rem] font-semibold leading-none text-warning">
                {paket.prisPerManad.toLocaleString("sv-SE")}
              </span>
              <span className="text-[15px] text-ink-muted">kr/mån</span>
            </>
          )}
          <span className="basis-full text-[14px] leading-6 text-ink-subtle">
            Läggs till på ert befintliga paket — bytet gäller direkt, och er
            gratisperiod påverkas inte.
          </span>
        </div>

        <div className="mt-8 flex flex-wrap items-center gap-4">
          <Link
            href="/settings/billing"
            className="focus-ring inline-flex min-h-12 items-center gap-2 rounded-input bg-ink px-7 text-[0.9375rem] font-semibold text-paper transition-colors hover:bg-ink2"
          >
            Lägg till i ert paket
            <ArrowRight className="h-4 w-4" aria-hidden />
          </Link>
          <a
            href={agent.demoVag}
            target="_blank"
            rel="noopener"
            className="focus-ring inline-flex min-h-12 items-center rounded-input border border-ink/15 px-6 text-[0.9375rem] font-medium text-ink transition-colors hover:border-ink/30"
          >
            Prova i demon först
          </a>
        </div>
      </div>
    </PageShell>
  );
}
