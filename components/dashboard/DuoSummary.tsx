"use client";

import Link from "next/link";
import { useLocale } from "@/lib/i18n";
import type { Localized } from "@/lib/i18n";
import { useDashboard } from "@/components/dashboard/DashboardContext";
import { useArbetsvag } from "@/components/AppShell";

/**
 * Den gemensamma översikten högst upp när en arbetsyta har BÅDA produkterna.
 *
 * ## Varför den behövs
 *
 * Utan den är duo-vyn två separata dashboards staplade på varandra. Kunden
 * betalar för att de hör ihop, och det enda som visade det var att de låg på
 * samma sida. Den här remsan är stället där de faktiskt möts: ett ärende och
 * ett utskick som rör samma bolag är samma kundrelation, inte två.
 *
 * ## Varför den ALDRIG renderas för en enproduktskund
 *
 * `shows()` kräver att arbetsytan äger produkten, och komponenten kräver att
 * BÅDA visas. En kund som bara har support ska inte ens ana att leads-ytan
 * finns — inte se den utgråad. Att gråa ut något är att berätta vad någon inte
 * betalar för, och det är en säljteknik vi inte använder mot befintliga kunder.
 *
 * Det är samma regel som `app/dashboard/[[...slug]]/page.tsx` upprätthåller
 * med `notFound()` på routenivå. Den här komponenten är det andra lagret, inte
 * det bärande — en dold ruta är inte ett skydd.
 */

const copy = {
  rubrik: { sv: "Gemensam översikt", en: "Shared overview" },
  lede: {
    sv: "Båda agenterna arbetar mot samma kunddata. Ett bolag som hör av sig till kundtjänsten syns här även om det kom in som ett prospekt.",
    en: "Both agents work against the same customer data. A company that contacts support shows up here even if it arrived as a prospect."
  },
  leads: { sv: "Leads", en: "Leads" },
  leadsRad: { sv: "Prospekt, utkast och granskningskö", en: "Prospects, drafts and review queue" },
  support: { sv: "Kundtjänst", en: "Support" },
  supportRad: { sv: "Ärenden, inkorg och kunskapsbas", en: "Cases, inbox and knowledge base" },
  tillLeads: { sv: "Öppna leads", en: "Open leads" },
  tillSupport: { sv: "Öppna kundtjänst", en: "Open support" },
  paketet: { sv: "Snajp Duo", en: "Snajp Duo" }
} satisfies Record<string, Localized>;

export function DuoSummary() {
  const { text } = useLocale();
  const { shows, workspaceName } = useDashboard();
  const vag = useArbetsvag();

  // Båda krävs. Se komponentens docstring om varför det inte finns något
  // utgråat mellanläge.
  if (!shows("leads") || !shows("support")) {
    return null;
  }

  return (
    <section
      aria-labelledby="duo-oversikt"
      className="rounded-card border border-ochre/40 bg-paper2/60 p-6 md:p-8"
    >
      <div className="flex flex-wrap items-baseline justify-between gap-x-6 gap-y-2">
        <h2 id="duo-oversikt" className="text-[1.125rem] font-semibold tracking-[-0.01em]">
          {text(copy.rubrik)}
        </h2>
        <span className="kicker rounded-input bg-ochre/12 px-2.5 py-1 text-ochre">
          {text(copy.paketet)}
          {workspaceName ? ` · ${workspaceName}` : ""}
        </span>
      </div>

      <p className="mt-3 max-w-[68ch] text-[0.9375rem] leading-[1.6] text-ink/70">
        {text(copy.lede)}
      </p>

      <div className="mt-6 grid gap-4 sm:grid-cols-2">
        <Kort
          rubrik={text(copy.leads)}
          rad={text(copy.leadsRad)}
          href={vag("/dashboard/leads")}
          knapp={text(copy.tillLeads)}
        />
        <Kort
          rubrik={text(copy.support)}
          rad={text(copy.supportRad)}
          href={vag("/dashboard/support")}
          knapp={text(copy.tillSupport)}
        />
      </div>
    </section>
  );
}

function Kort({
  rubrik,
  rad,
  href,
  knapp
}: Readonly<{ rubrik: string; rad: string; href: string; knapp: string }>) {
  return (
    <div className="flex flex-col rounded-input border border-ink/15 bg-paper p-5">
      <p className="text-[0.9375rem] font-semibold">{rubrik}</p>
      <p className="mt-1.5 text-[0.875rem] leading-[1.5] text-ink/65">{rad}</p>
      <Link
        href={href}
        className="focus-ring mt-4 inline-flex min-h-10 w-fit items-center rounded-input border border-ink/20 px-4 text-[0.875rem] font-medium transition-colors hover:bg-paper2"
      >
        {knapp}
      </Link>
    </div>
  );
}
