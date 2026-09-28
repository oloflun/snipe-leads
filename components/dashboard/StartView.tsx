"use client";

import { PageShell } from "@/components/AppShell";
import { useDashboard } from "@/components/dashboard/DashboardContext";
import { LeadsOversikt, SupportOversikt } from "@/components/dashboard/Oversikt";
import { KunskapsbasKort } from "@/components/settings/Kunskapsbas";
import { Sektion } from "@/components/ui";
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
 * ## En anatomi oavsett antal produkter (2026-09-27)
 *
 * Rubriken är alltid "Arbetsytan" och varje produkt är en `Sektion` under den,
 * även när arbetsytan bara har en. Tidigare bytte sidrubriken till "Leads"
 * eller "Kundtjänst" för en enproduktskund och sektionsrubriken föll bort, så
 * samma översikt hade två olika rubrikstrukturer och delrubrikerna i
 * Oversikt.tsx hoppade från h1 till h3. Nu ser en sektion likadan ut för alla.
 *
 * `DuoSummary` (kortet "Gemensam översikt" med två länkkort till Leads och
 * Kundtjänst) renderas inte längre: korten upprepade railens navigering, och
 * märkningen ovanför upprepade arbetsytans namn som redan står i railen
 * (plans/2026-09-27-appytor-enhetlighet.md, regel 4). Varje sektion bär i
 * stället sina egna länkar där de används — granskningskön, inkorgen.
 */

const copy = {
  title: { sv: "Arbetsytan", en: "Workspace" },
  // Samma namn som railen: agenten heter Iris överallt, inte Leads på en yta och Iris på nästa.
  leadsHeading: { sv: "Iris", en: "Iris" },
  supportHeading: { sv: "Kundtjänst", en: "Support" }
} satisfies Record<string, Localized>;

export function StartView({ demo = false }: Readonly<{ demo?: boolean }>) {
  const { text } = useLocale();
  const { shows } = useDashboard();

  return (
    <PageShell title={text(copy.title)}>
      {shows("leads") ? (
        <Sektion title={text(copy.leadsHeading)}>
          <LeadsOversikt demo={demo} />
        </Sektion>
      ) : null}

      {shows("support") ? (
        <Sektion title={text(copy.supportHeading)}>
          <SupportOversikt demo={demo} />
        </Sektion>
      ) : null}

      {/* Underlaget SIST, inte först.
          Kortet låg tidigare överst, före allt annat på startsidan. Det är
          rätt prioritering första dagen och fel varje dag därefter: en kund
          med en fylld bas fick en uppladdningsruta mellan sig och sina
          siffror. Nu står bristen i statusraden i varje sektion (0 dokument
          markeras), och verktyget för att åtgärda den ligger här.
          Inte på demoytan: där finns ingen session att ladda upp till. */}
      {demo ? null : (
        <div className="mt-12">
          <KunskapsbasKort />
        </div>
      )}
    </PageShell>
  );
}
