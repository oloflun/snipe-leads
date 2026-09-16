import { ShieldCheck } from "lucide-react";

/**
 * Integritetsnotisen — samma text som huvudappens komponent och backendens
 * `INTEGRITETSNOTIS` (app/agent/kvitto_agent.py). Formuleringen är medvetet
 * exakt i stället för absolut: kvittotexten tolkas av en extern AI-modell,
 * så "allt sker lokalt" hade varit en vilseledande claim. Ändras texten ska
 * alla tre ställena ändras i samma commit.
 */
export function Integritetsnotis() {
  return (
    <p className="flex items-start gap-2.5 rounded-[10px] border border-ink/12 bg-paper2/40 px-4 py-3.5 text-[0.8125rem] leading-6 text-ink/65">
      <ShieldCheck className="mt-0.5 h-4 w-4 shrink-0 text-moss" aria-hidden />
      <span>
        <strong className="font-semibold text-ink/80">Dina mejl stannar dina.</strong>{" "}
        Vi läser med read-only-åtkomst, säljer aldrig din data och delar den
        aldrig med tredje part utöver den AI-tjänst som tolkar kvittotexten,
        under personuppgiftsbiträdesavtal. Mejlens text sparas inte — det som
        lagras är de utlästa kvittofälten, avsändare och ämnesrad samt en
        kontrollsumma.
      </span>
    </p>
  );
}
