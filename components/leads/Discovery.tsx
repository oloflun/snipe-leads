"use client";

import { useDashboard } from "@/components/dashboard/DashboardContext";
import { ExempelbolagDemo } from "@/components/leads/ExempelbolagDemo";
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
 * riktig körning. Exempelbolag skapas inte här.
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

      {/* Två kolumner på bred skärm: formuläret till vänster (fälten är capade
          760px sedan tidigare, resten av bredden stod tom), exempellistan till
          höger. Den visar hur ett färdigt resultat ser ut innan man bränt en
          körning — varje rad är märkt "Exempel" och kan aldrig mejlas, se
          ExempelbolagDemo. Under xl staplas listan under formuläret, så
          mobilvyn är oförändrad. */}
      <div className="grid grid-cols-1 gap-8 xl:grid-cols-2 xl:items-start">
        {/* Demovyn räknas som testkörning: den är vår egen provkörning mot
            demokontot och ska inte synas som kundvolym i portföljvyn. */}
        <LeadsRunForm isTest={isDemo || vy === "demo"} demo={demo} />
        <ExempelbolagDemo />
      </div>
    </section>
  );
}
