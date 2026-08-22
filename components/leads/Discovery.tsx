"use client";

import { useDashboard } from "@/components/dashboard/DashboardContext";
import { LeadsRunForm } from "@/components/leads/LeadsRunForm";

/**
 * Discovery på kundens yta — samma formulär och samma alternativ som adminytans
 * Testkörningar, för att det är samma sak som händer.
 *
 * Vad som fanns här innan: fyra knappar med texten "Bygg i Malmö", "Gym i
 * Stockholm", "Fastighet Uppsala" och "SaaS med rekrytering". De var `<button>`
 * utan `onClick`. Kunden kunde alltså inte starta en körning från sin egen yta
 * över huvud taget — bara från adminytan, som kunden inte har.
 *
 * `is_test` följer arbetsytan: en testarbetsyta märker sina körningar så att de
 * aldrig räknas som kundvolym i portföljvyn. En riktig kunds körning är en
 * riktig körning.
 */
export function Discovery({ demo = false }: Readonly<{ demo?: boolean }>) {
  const { isDemo, vy } = useDashboard();

  return (
    <section aria-labelledby="discovery">
      <div className="flex flex-wrap items-baseline justify-between gap-x-6 gap-y-2">
        <h2 id="discovery" className="text-[1.125rem] font-semibold tracking-[-0.01em]">
          Hitta bolag
        </h2>
        <p className="text-[13px] text-ink/45">
          Lämna ett fält tomt för att använda er sparade målgrupp
        </p>
      </div>

      {/* Demovyn räknas som testkörning: den är vår egen provkörning mot
          demokontot och ska inte synas som kundvolym i portföljvyn. */}
      <LeadsRunForm isTest={isDemo || vy === "demo"} demo={demo} />
    </section>
  );
}
