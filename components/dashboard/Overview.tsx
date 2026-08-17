"use client";

import Link from "next/link";
import { PageShell } from "@/components/AppShell";
import { useDashboard } from "@/components/dashboard/DashboardContext";
import { DuoSummary } from "@/components/dashboard/DuoSummary";
import { Dashboard as SupportDashboard } from "@/components/snajp/Dashboard";
import { DashboardBody } from "@/components/WorkspaceViews";
import { useLocale } from "@/lib/i18n";
import type { Localized } from "@/lib/i18n";

const copy = {
  kicker: { sv: "Översikt", en: "Overview" },
  title: { sv: "Arbetsytan", en: "Workspace" },
  descBoth: {
    sv: "Leads och kundtjänst i samma vy. Byt vad som visas uppe till höger.",
    en: "Leads and support in one view. Change what is shown at the top right."
  },
  descLeads: {
    sv: "Prioriterade bolag, svar och nästa handling.",
    en: "Priority accounts, replies and next action."
  },
  descSupport: {
    sv: "Inkommande ärenden, utkast och vad som väntar på en människa.",
    en: "Incoming cases, drafts and what is waiting on a human."
  },
  freshTitle: { sv: "Inget här ännu", en: "Nothing here yet" },
  freshBody: {
    sv: "Arbetsytan är tom. Beskriv vad ni säljer och vem ni säljer till, så kan Snajp börja föreslå bolag och skriva utkast.",
    en: "The workspace is empty. Describe what you sell and who you sell to, and Snajp can start suggesting companies and drafting emails."
  },
  freshCta: { sv: "Fyll i affärskontext", en: "Add business context" },
  freshSupport: {
    sv: "Kundtjänstagenten behöver en kunskapsbas att svara ur. Lägg in era vanligaste svar, så börjar den sortera inkorgen.",
    en: "The support agent needs a knowledge base to answer from. Add your most common replies and it will start sorting the inbox."
  },
  leadsHeading: { sv: "Leads", en: "Leads" },
  supportHeading: { sv: "Kundtjänst", en: "Support" }
} satisfies Record<string, Localized>;

export function Overview() {
  const { text } = useLocale();
  const { variant, shows, scope } = useDashboard();

  const description =
    scope === "both" ? copy.descBoth : scope === "leads" ? copy.descLeads : copy.descSupport;

  if (variant === "fresh") {
    return (
      <PageShell
        kicker={text(copy.kicker)}
        title={text(copy.freshTitle)}
        description={text(shows("leads") ? copy.freshBody : copy.freshSupport)}
      >
        <div className="rounded-card bg-paper2/60 p-6 md:p-8">
          <p className="max-w-[60ch] text-[0.9375rem] leading-[1.6] text-ink/65">
            {text(shows("leads") ? copy.freshBody : copy.freshSupport)}
          </p>
          <Link
            href="/onboarding"
            className="focus-ring mt-6 inline-flex min-h-11 items-center rounded-input bg-ink px-5 text-[0.9375rem] font-semibold text-paper transition-colors hover:bg-ink2"
          >
            {text(copy.freshCta)}
          </Link>
        </div>
      </PageShell>
    );
  }

  return (
    <PageShell kicker={text(copy.kicker)} title={text(copy.title)} description={text(description)}>
      <div className="space-y-12">
        {/* Högst upp, och bara när båda produkterna finns. Komponenten
            returnerar null av sig själv annars — se DuoSummary. */}
        <DuoSummary />

        {shows("leads") ? (
          <section>
            {scope === "both" ? (
              <h2 className="mb-5 text-[1.125rem] font-semibold tracking-[-0.01em]">
                {text(copy.leadsHeading)}
              </h2>
            ) : null}
            <DashboardBody />
          </section>
        ) : null}

        {shows("support") ? (
          <section>
            {scope === "both" ? (
              <h2 className="mb-5 text-[1.125rem] font-semibold tracking-[-0.01em]">
                {text(copy.supportHeading)}
              </h2>
            ) : null}
            <SupportDashboard />
          </section>
        ) : null}
      </div>
    </PageShell>
  );
}
