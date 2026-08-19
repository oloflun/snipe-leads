"use client";

import Link from "next/link";
import { PageShell } from "@/components/AppShell";
import { useDashboard } from "@/components/dashboard/DashboardContext";
import { DuoSummary } from "@/components/dashboard/DuoSummary";
import { Dashboard as SupportDashboard } from "@/components/snajp/Dashboard";
import { LeadsBody } from "@/components/WorkspaceViews";
import { useLocale } from "@/lib/i18n";
import type { Localized } from "@/lib/i18n";

/**
 * Startsidan — agentens vy, inte en sammanfattning av den.
 *
 * ## Vad som ändrades
 *
 * `/dashboard` renderade tidigare "Min arbetsyta": en panel med veckosiffror
 * och ett bolagsregister ur `lib/mock-data.ts`, ovanför de riktiga vyerna. För
 * en kund med ETT paket betydde det att startsidan var en sammanfattning av
 * den enda sida de ändå skulle till — ett extra klick varje gång, till en
 * siffra som inte kom från deras data.
 *
 * Nu gäller: en leads-kund landar i leads-vyn, en supportkund i kundtjänst-
 * vyn, och båda flikarna heter **Översikt**. Sammanfattningen finns kvar, men
 * som inställning (`/settings/arbetsyta`) — den är en rapport, inte ett
 * arbetsläge.
 *
 * ## Demoytan
 *
 * `demo` går vidare till båda vyerna. Utan den anropade startsidan den
 * inloggade backenden från /demo, där ingen session finns — panelen svarade
 * "Du måste vara inloggad" mitt i produktdemon. Undersidorna (/demo/support,
 * /demo/kontroll) hade redan flaggan; startsidan var den som saknade den.
 *
 * ## Duo-kunder
 *
 * Med båda paketen styr scope-växeln vad som visas, precis som förut, och
 * `DuoSummary` ligger kvar högst upp när båda är på. Det är också bara för
 * duo-kunder som flikarna "Leads" och "Kundtjänst" renderas (se `duoOnly` i
 * lib/routes.ts) — för alla andra ÄR Översikt den fliken.
 */

const copy = {
  kicker: { sv: "Översikt", en: "Overview" },
  titleLeads: { sv: "Leads", en: "Leads" },
  titleSupport: { sv: "Inkorg och utkast", en: "Inbox and drafts" },
  titleBoth: { sv: "Arbetsytan", en: "Workspace" },
  descBoth: {
    sv: "Leads och kundtjänst i samma vy. Byt vad som visas uppe till höger.",
    en: "Leads and support in one view. Change what is shown at the top right."
  },
  descLeads: {
    sv: "Bolag agenten hittat, vad den grundade urvalet i, och vad som väntar på dig.",
    en: "Companies the agent found, what it based the selection on, and what is waiting for you."
  },
  descSupport: {
    sv: "Inkommande ärenden, agentens klassificering och de svar som väntar på godkännande.",
    en: "Incoming cases, the agent's classification and the replies awaiting approval."
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

export function StartView({ demo = false }: Readonly<{ demo?: boolean }>) {
  const { text } = useLocale();
  const { variant, shows, scope } = useDashboard();

  const bada = shows("leads") && shows("support");
  const title = bada ? copy.titleBoth : shows("leads") ? copy.titleLeads : copy.titleSupport;
  const description = bada ? copy.descBoth : shows("leads") ? copy.descLeads : copy.descSupport;

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
    <PageShell kicker={text(copy.kicker)} title={text(title)} description={text(description)}>
      <div className="space-y-12">
        {/* Högst upp, och bara när båda produkterna visas. Komponenten
            returnerar null av sig själv annars — se DuoSummary. */}
        <DuoSummary />

        {shows("leads") ? (
          <section>
            {scope === "both" ? (
              <h2 className="mb-5 text-[1.125rem] font-semibold tracking-[-0.01em]">
                {text(copy.leadsHeading)}
              </h2>
            ) : null}
            <LeadsBody demo={demo} />
          </section>
        ) : null}

        {shows("support") ? (
          <section>
            {scope === "both" ? (
              <h2 className="mb-5 text-[1.125rem] font-semibold tracking-[-0.01em]">
                {text(copy.supportHeading)}
              </h2>
            ) : null}
            <SupportDashboard demo={demo} />
          </section>
        ) : null}
      </div>
    </PageShell>
  );
}
