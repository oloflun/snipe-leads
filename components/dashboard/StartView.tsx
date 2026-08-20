"use client";

import { PageShell } from "@/components/AppShell";
import { useDashboard } from "@/components/dashboard/DashboardContext";
import { DuoSummary } from "@/components/dashboard/DuoSummary";
import { LeadsOversikt, SupportOversikt } from "@/components/dashboard/Oversikt";
import { KunskapsbasKort } from "@/components/settings/Kunskapsbas";
import { useLocale } from "@/lib/i18n";
import type { Localized } from "@/lib/i18n";

/**
 * Startsidan — en ÖVERSIKT, inte agentens råa arbetsvy.
 *
 * ## Två omtag, och varför det här är det rätta
 *
 * Först renderade `/dashboard` en sammanfattning ur `lib/mock-data.ts` ovanför
 * de riktiga vyerna: ett extra klick varje gång, till siffror som inte kom ur
 * kundens data.
 *
 * Sedan blev startsidan agentens arbetsvy rakt av och sammanfattningen sköts
 * in i `/settings/arbetsyta`. Det löste mock-problemet genom att ta bort
 * översikten, vilket är en annan sorts fel: inloggningen landade i
 * discovery-formulärets tomläge ("Inget här ännu"), och den enda vy som
 * svarade på "vad har hänt" gick att nå först efter tre klick i
 * inställningarna. Uppmätt i skärmdump.
 *
 * Nu: startsidan svarar på **vad har hänt och vad väntar på mig**, med siffror
 * ur kundens egen tenant (se components/dashboard/Oversikt.tsx). Arbetsvyerna
 * ligger kvar på `/dashboard/leads` och `/dashboard/support` och gör jobbet.
 * Båda flikarna finns för alla kunder sedan `duoOnly` togs bort i
 * lib/routes.ts — utan dem hade en enproduktskund inte nått sin arbetsvy alls.
 *
 * ## Demoytan
 *
 * `demo` går vidare till översikterna, som byter ut backend-anropen mot
 * exempeldata i webbläsaren. Utan den flaggan anropade startsidan den
 * inloggade backenden från /demo, där ingen session finns — och panelen svarade
 * "Du måste vara inloggad" mitt i produktdemon.
 *
 * ## Duo-kunder
 *
 * Med båda paketen styr scope-växeln vad som visas, och `DuoSummary` ligger
 * högst upp när båda är på.
 */

const copy = {
  kicker: { sv: "Översikt", en: "Overview" },
  titleLeads: { sv: "Leads", en: "Leads" },
  titleSupport: { sv: "Kundtjänst", en: "Support" },
  titleBoth: { sv: "Arbetsytan", en: "Workspace" },
  descBoth: {
    sv: "Läget i båda agenterna, och vad som väntar på dig. Byt vad som visas uppe till höger.",
    en: "Where both agents stand, and what is waiting for you. Change what is shown at the top right."
  },
  descLeads: {
    sv: "Vad agenten hittat, vad den grundade urvalet i, och vad som väntar på ditt godkännande.",
    en: "What the agent found, what it based the selection on, and what is waiting for your approval."
  },
  descSupport: {
    sv: "Vad som kommit in, hur mycket agenten klarade själv, och vad som ligger hos dig.",
    en: "What came in, how much the agent handled on its own, and what is waiting for you."
  },
  freshBody: {
    sv: "Arbetsytan är tom. Beskriv vad ni säljer och vem ni säljer till, så kan Snajp börja föreslå bolag och skriva utkast.",
    en: "The workspace is empty. Describe what you sell and who you sell to, and Snajp can start suggesting companies and drafting emails."
  },
  freshSupport: {
    sv: "Kundtjänstagenten behöver en kunskapsbas att svara ur. Lägg in era vanligaste svar, så börjar den sortera inkorgen.",
    en: "The support agent needs a knowledge base to answer from. Add your most common replies and it will start sorting the inbox."
  },
  leadsHeading: { sv: "Leads", en: "Leads" },
  supportHeading: { sv: "Kundtjänst", en: "Support" }
} satisfies Record<string, Localized>;

export function StartView({ demo = false }: Readonly<{ demo?: boolean }>) {
  const { text } = useLocale();
  const { shows, scope } = useDashboard();

  const bada = shows("leads") && shows("support");
  const title = bada ? copy.titleBoth : shows("leads") ? copy.titleLeads : copy.titleSupport;
  const description = bada ? copy.descBoth : shows("leads") ? copy.descLeads : copy.descSupport;

  return (
    <PageShell kicker={text(copy.kicker)} title={text(title)} description={text(description)}>
      <div className="space-y-14">
        {/* Högst upp bland vyerna, och bara när båda produkterna visas.
            Komponenten returnerar null av sig själv annars — se DuoSummary. */}
        <DuoSummary />

        {shows("leads") ? (
          <section>
            {scope === "both" ? (
              <h2 className="mb-6 text-[1.125rem] font-semibold tracking-[-0.01em]">
                {text(copy.leadsHeading)}
              </h2>
            ) : null}
            <LeadsOversikt demo={demo} />
          </section>
        ) : null}

        {shows("support") ? (
          <section>
            {scope === "both" ? (
              <h2 className="mb-6 text-[1.125rem] font-semibold tracking-[-0.01em]">
                {text(copy.supportHeading)}
              </h2>
            ) : null}
            <SupportOversikt demo={demo} />
          </section>
        ) : null}

        {/* Underlaget SIST, inte först.
            Kortet låg tidigare överst, före allt annat på startsidan. Det är
            rätt prioritering första dagen och fel varje dag därefter: en kund
            med en fylld bas fick en uppladdningsruta mellan sig och sina
            siffror. Nu står bristen i tillståndsraden högst upp (0 dokument
            markeras), och verktyget för att åtgärda den ligger här.
            Inte på demoytan: där finns ingen session att ladda upp till. */}
        {demo ? null : <KunskapsbasKort />}
      </div>
    </PageShell>
  );
}
