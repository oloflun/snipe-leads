"use client";

import { LeadsRunForm } from "@/components/leads/LeadsRunForm";
import { LeadsSnabbsok } from "@/components/leads/LeadsSnabbsok";
import { useLocale } from "@/lib/i18n";

/**
 * Provkörning av Iris inifrån adminytan.
 *
 * ## Varför den finns
 *
 * Att veta att agenten SVARAR har annars krävt en riktig kund eller ett
 * curl-anrop med en API-nyckel — så den testades i praktiken bara när något
 * redan gått fel.
 *
 * ## Varför körningarna märks
 *
 * Varje körning skriver en rad i `agent_runs`, och portföljvyn räknar dem.
 * `is_test` (migration 036) skiljer provkörningar från kundvolym; siffror som
 * inte går att lita på är värre än inga siffror.
 *
 * ## Vad som togs bort 2026-09-22 (kundtest)
 *
 * Exempelbolagen (tre påhittade .example-bolag) och den separata
 * "Kundtjänstagenten"-rutan. Kundtjänsten provas redan per konto i
 * arbetsytans flikar Testmail och Testchatt — en tredje väg till samma sak
 * var bara en yta till att hålla i takt. Själva testkörningarna för Iris, som
 * aldrig blandas med de ordinarie, står kvar.
 *
 * ## Varför leads-formuläret ligger i components/leads
 *
 * Kundens leads-flik och den här ytan delar `LeadsRunForm`, med `is_test` som
 * enda skillnad — två kopior av ett formulär med tio fält glider isär.
 */
export function Testkorningar() {
  const { text } = useLocale();
  return (
    <div className="grid gap-12">
      <p className="max-w-[70ch] text-[15px] leading-7 text-mineral">
        {text({ sv: "Körningar startade härifrån märks", en: "Runs started from here are marked" })}{" "}
        <code className="font-mono text-[13px]">is_test</code>{" "}
        {text({
          sv: "och räknas aldrig som kundvolym i Översikten. Inställningarna gäller bara den enskilda körningen — arbetsytans sparade målgrupp rörs inte.",
          en: "and never count as customer volume in the Overview. The settings apply to this run only. The workspace's saved audience is not touched."
        })}
      </p>

      {/* Två kolumner på bred skärm: körningsformuläret till vänster,
          snabbsöket i högerkolumnen. Under xl staplas de. */}
      <section className="border-t border-ink/15 pt-8">
        <div className="grid grid-cols-1 gap-8 xl:grid-cols-2 xl:items-start">
          <LeadsRunForm
            isTest
            rubrik={
              <>
                <h2 className="font-display text-2xl tracking-[-0.02em]">
                  {text({ sv: "Iris, leadsagenten", en: "Iris, the leads agent" })}
                </h2>
                <p className="mt-2 max-w-[65ch] text-[15px] text-mineral">
                  {text({
                    sv: "Kör research över prospekten. Lämna ett fält tomt för att använda arbetsytans sparade värde.",
                    en: "Runs research across the prospects. Leave a field empty to use the workspace's saved value."
                  })}
                </p>
              </>
            }
          />
          <LeadsSnabbsok isTest />
        </div>
      </section>
    </div>
  );
}
