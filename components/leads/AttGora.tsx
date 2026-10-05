"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useArbetsvag } from "@/components/AppShell";
import { useDashboard } from "@/components/dashboard/DashboardContext";
import { Dashboard } from "@/components/snajp/Dashboard";
import { chip, chipInaktiv } from "@/components/ui";
import { readJsonBody } from "@/lib/http/json";
import { useLocale, type Localized } from "@/lib/i18n";
import { cn } from "@/lib/utils";

/**
 * Att göra — det som väntar på ett beslut från dig, i viktordning (plan
 * 2026-10-05, fas 5).
 *
 * Antons granskning: sidan var en oändlig scroll förbi fullständiga listor,
 * och leadsinkorgen och utkasten låg längst ner. Nu:
 *
 * - En summeringsrad överst säger hur mycket som väntar var, med länkar.
 * - Kundtjänstens köer i viktordning — eskalerat, svar att godkänna, larm —
 *   fem rader var, resten bakom "Visa alla". Likadana larm blir en rad med
 *   räknare.
 * - Leadsinkorgen och Iris utkast bor under Leads (egna flikar); här står
 *   bara hur många som väntar, med en länk dit.
 */

const TAK = 5;

type Antal = { eskalerade: number | null; vantar: number | null; larm: number | null; leadsvar: number | null; utkast: number | null };

export function AttGora({ demo = false }: Readonly<{ demo?: boolean }>) {
  const { products } = useDashboard();
  const { text } = useLocale();
  const vag = useArbetsvag();
  const iris = products.includes("leads");
  const support = products.includes("support");
  const [antal, setAntal] = useState<Antal>({ eskalerade: null, vantar: null, larm: null, leadsvar: null, utkast: null });

  // Leadsdelen räknas här, inte genom att rendera listorna: de bor under Leads.
  useEffect(() => {
    if (!iris || demo) return;
    let avbruten = false;
    async function rakna() {
      const [svar, ko] = await Promise.allSettled([
        fetch("/api/snajp-support/inbox?klass=lead&limit=200", { cache: "no-store" }).then((r) =>
          readJsonBody<{ emails?: { hanterad_at?: string | null }[] }>(r)
        ),
        fetch("/api/snajp-support/leads/queue", { cache: "no-store" }).then((r) => readJsonBody<{ items?: unknown[] }>(r))
      ]);
      if (avbruten) return;
      setAntal((a) => ({
        ...a,
        leadsvar: svar.status === "fulfilled" ? (svar.value?.emails ?? []).filter((e) => !e.hanterad_at).length : null,
        utkast: ko.status === "fulfilled" ? (ko.value?.items ?? []).length : null
      }));
    }
    void rakna();
    return () => {
      avbruten = true;
    };
  }, [iris, demo]);

  const sammanfattning: { id: string; etikett: Localized; antal: number | null; href: string }[] = [
    ...(support
      ? [
          { id: "kundtjanst-eskalerat", etikett: { sv: "eskalerade ärenden", en: "escalated cases" }, antal: antal.eskalerade, href: "#kundtjanst-eskalerat" },
          { id: "kundtjanst-utkast", etikett: { sv: "svar att godkänna", en: "replies to approve" }, antal: antal.vantar, href: "#kundtjanst-utkast" },
          { id: "kundtjanst-larm", etikett: { sv: "larm", en: "alerts" }, antal: antal.larm, href: "#kundtjanst-larm" }
        ]
      : []),
    ...(iris && !demo
      ? [
          { id: "leads-svar", etikett: { sv: "svar från leads", en: "replies from leads" }, antal: antal.leadsvar, href: vag("/dashboard/leads?vy=inkorg") },
          { id: "leads-utkast", etikett: { sv: "leadsutkast", en: "lead drafts" }, antal: antal.utkast, href: vag("/dashboard/leads?vy=utkast") }
        ]
      : [])
  ];

  return (
    <div className="grid gap-10">
      <nav aria-label={text({ sv: "Det som väntar", en: "What is waiting" })}>
        <ul className="flex flex-wrap gap-2">
          {sammanfattning.map((s) => (
            <li key={s.id}>
              <Link href={s.href} className={cn(chip, chipInaktiv, s.antal === 0 && "text-ink-subtle")}>
                <span className="num font-semibold tabular-nums">{s.antal ?? "…"}</span>
                <span className="ml-1.5">{text(s.etikett)}</span>
              </Link>
            </li>
          ))}
        </ul>
      </nav>

      {support ? (
        <Del id="kundtjanst-eskalerat" rubrik={{ sv: "Eskalerat till dig", en: "Escalated to you" }} forst>
          <Dashboard lager="eskalerade" demo={demo} tak={TAK} onAntal={(n) => setAntal((a) => ({ ...a, eskalerade: n }))} />
        </Del>
      ) : null}
      {support ? (
        <Del id="kundtjanst-utkast" rubrik={{ sv: "Svar att godkänna", en: "Replies to approve" }}>
          <Dashboard lager="vantar" demo={demo} tak={TAK} onAntal={(n) => setAntal((a) => ({ ...a, vantar: n }))} />
        </Del>
      ) : null}
      {/* Larmen (migration 078): avvisade utskick, systemfel. Skilda från
          eskaleringarna, som är kundärenden agenten lämnat över. */}
      {support ? (
        <Del id="kundtjanst-larm" rubrik={{ sv: "Larm", en: "Alerts" }}>
          <Dashboard lager="att_hantera" demo={demo} tak={TAK} onAntal={(n) => setAntal((a) => ({ ...a, larm: n }))} />
        </Del>
      ) : null}
      {iris && !support ? (
        <p className="text-[0.9375rem] leading-7 text-ink-muted">
          {text({
            sv: "Svar från leads och Iris utkast finns under Leads, i flikarna Inkorg och Utkast.",
            en: "Replies from leads and Iris drafts live under Leads, in the Inbox and Drafts tabs."
          })}
        </p>
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
    <section aria-labelledby={`${id}-rubrik`} id={id} className={cn("scroll-mt-24", forst ? undefined : "border-t border-ink/15 pt-8")}>
      <h2 id={`${id}-rubrik`} className="mb-4 text-[1.125rem] font-semibold tracking-[-0.01em] text-ink">
        {text(rubrik)}
      </h2>
      {children}
    </section>
  );
}
