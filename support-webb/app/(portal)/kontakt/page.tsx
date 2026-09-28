import { Mail } from "lucide-react";
import type { Metadata } from "next";
import { PageHeader } from "@/components/PageHeader";
import { btnPrimary } from "@/components/ui";

export const metadata: Metadata = { title: "Kontakt" };

/** Samma adress som huvudappens sidfot (components/marketing/copy.ts). */
const KONTAKT_MEJL = "kontakt@snajp.se";

export default function Sida() {
  return (
    <div className="space-y-8">
      <PageHeader rubrik="Kontakt" />

      <section className="max-w-[38rem]">
        <div className="border-y border-ink/15 py-6">
          <p className="text-[0.875rem] font-medium text-ink/55">Mejla oss</p>
          <a
            href={`mailto:${KONTAKT_MEJL}`}
            className="focus-ring mt-1 inline-block rounded-[4px] font-display text-[1.5rem] text-ink underline decoration-ochre/50 decoration-1 underline-offset-8 transition-colors hover:text-ink/70"
          >
            {KONTAKT_MEJL}
          </a>
          <a href={`mailto:${KONTAKT_MEJL}?subject=${encodeURIComponent("Snajp Support")}`} className={`${btnPrimary} mt-5`}>
            <Mail className="h-4 w-4" aria-hidden />
            Skriv till oss
          </a>
        </div>
      </section>
    </div>
  );
}
