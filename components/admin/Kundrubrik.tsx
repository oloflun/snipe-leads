"use client";

import { a } from "@/lib/admin/sprak";
import { useLocale } from "@/lib/i18n";

/**
 * Rubrik och ingress för Kunder & Data.
 *
 * Egen klientkomponent av ett enda skäl: sidan är en server-komponent (den
 * hämtar), och rubriken måste ändå byta språk med EN/SV-knappen. Att flytta
 * hela sidan till klienten för två textstycken hade betytt att hämtningen
 * också flyttade dit.
 */
export function Kundrubrik() {
  const { locale } = useLocale();
  return (
    <>
      <h1 className="font-display text-4xl tracking-[-0.03em]">{a("kunderRubrik", locale)}</h1>
      <p className="mt-3 max-w-[70ch] text-[15px] leading-7 text-mineral">
        {a("kunderIngress", locale)}
      </p>
    </>
  );
}

/**
 * Fotnoten längst ned.
 *
 * Intäkter och utgifter har MEDVETET ingen sektion på den här sidan: det finns
 * ingen riktig betal- eller bokföringskälla i systemet ännu (betalsätten är
 * simulerade testkort, fakturor finns inte i kod). Uppskattad månadsintäkt och
 * tokenkostnad — tydligt märkta som uppskattningar — ligger under Översikt.
 * Bygg inte in siffror här förrän en riktig datakälla är vald.
 *
 * Volymtalen i tabellen ovan är något annat: de är räknade ur agent_runs och
 * ss_tickets, och de rader som saknar aktivitet är märkta "Exempel". Ett
 * påhittat intäktstal utan märkning är det den här fotnoten varnar för.
 */
export function Kundfotnot() {
  const { text } = useLocale();
  return (
    <p className="mt-14 max-w-[70ch] border-t border-ink/15 pt-5 text-[0.8125rem] leading-6 text-mineral">
      {text({
        sv: "Intäkter och utgifter visas inte här ännu: det finns ingen riktig betal- eller bokföringskälla i systemet, och påhittade siffror är värre än inga. Uppskattad månadsintäkt och tokenkostnad finns under Översikt, märkta som uppskattningar.",
        en: "Revenue and expenses are not shown here yet: there is no real payment or accounting source in the system, and invented figures are worse than none. Estimated monthly revenue and token cost live under Overview, labelled as estimates."
      })}
    </p>
  );
}
