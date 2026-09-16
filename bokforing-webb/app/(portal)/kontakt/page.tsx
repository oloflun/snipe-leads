import { Mail } from "lucide-react";
import type { Metadata } from "next";
import { PageHeader } from "@/components/PageHeader";
import { btnPrimary } from "@/components/ui";

export const metadata: Metadata = { title: "Kontakt" };

/** Samma adress som huvudappens sidfot (components/marketing/copy.ts:
 *  KONTAKT_MEJL). Ändras den där ska den ändras här. */
const KONTAKT_MEJL = "kontakt@snajp.se";

export default function Sida() {
  return (
    <div className="space-y-8">
      <PageHeader
        rubrik="Kontakt"
        beskrivning="Snajp Kvitton är en tjänst från Snajp. Frågor, fel och önskemål går rakt till oss."
      />

      <section className="max-w-[38rem]">
        <div className="border-y border-ink/15 py-6">
          <p className="text-[0.875rem] font-medium text-ink/55">Mejla oss</p>
          <a
            href={`mailto:${KONTAKT_MEJL}`}
            className="focus-ring mt-1 inline-block rounded-[4px] font-display text-[1.5rem] text-ink underline decoration-ochre/50 decoration-1 underline-offset-8 transition-colors hover:text-ink/70"
          >
            {KONTAKT_MEJL}
          </a>
          <p className="mt-3 max-w-[52ch] text-[0.9375rem] leading-6 text-ink/62">
            Skriv vad det gäller och vilken period det handlar om, så blir svaret bättre. Gäller
            det ett underlag som lästs fel: nämn filnamnet — själva filen har vi aldrig kvar.
          </p>
          <a href={`mailto:${KONTAKT_MEJL}?subject=${encodeURIComponent("Snajp Kvitton")}`} className={`${btnPrimary} mt-5`}>
            <Mail className="h-4 w-4" aria-hidden />
            Skriv till oss
          </a>
        </div>

        <div className="py-6">
          <h2 className="font-display text-[1.25rem]">Bra att veta</h2>
          <ul className="mt-3 space-y-3 text-[0.9375rem] leading-6 text-ink/62">
            <li>
              Förslag, inte bokföring: agentens avläsningar är förslag som du eller din
              redovisningskonsult godkänner — de ersätter inte en auktoriserad konsult.
            </li>
            <li>
              Dina filer sparas aldrig. Agenten läser dem i minnet, sparar de avlästa fälten och
              kastar filen.
            </li>
            <li>
              Du kan när som helst rensa en period under PDF-filer — raderingen är äkta och
              omedelbar.
            </li>
          </ul>
        </div>
      </section>
    </div>
  );
}
