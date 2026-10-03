"use client";

import { useDashboard } from "@/components/dashboard/DashboardContext";
import { IrisKorningar } from "@/components/leads/IrisKorningar";
import { JournalVy } from "@/components/snajp/JournalVy";
import { useLocale } from "@/lib/i18n";

/**
 * Aktivitet — alla agenters körningar på ett ställe (Snajp Suite 2026-10-03).
 *
 * Ersätter Iris › Körningar och Kundtjänst › Journal. Två befintliga vyer,
 * oförändrade, var och en bara för en agent arbetsytan har. Kvitton har ingen
 * körningsvy att visa ännu och står därför inte här.
 */
export function Aktivitet() {
  const { products } = useDashboard();
  const { text } = useLocale();
  const iris = products.includes("leads");
  const support = products.includes("support");

  return (
    <div className="grid gap-12">
      {iris ? (
        <section aria-labelledby="aktivitet-iris">
          <h2 id="aktivitet-iris" className="mb-5 text-[1.125rem] font-semibold tracking-[-0.01em] text-ink">
            {text({ sv: "Iris körningar", en: "Iris runs" })}
          </h2>
          <IrisKorningar />
        </section>
      ) : null}

      {support ? (
        <section aria-labelledby="aktivitet-kundtjanst" className={iris ? "border-t border-ink/15 pt-8" : undefined}>
          <h2 id="aktivitet-kundtjanst" className="mb-5 text-[1.125rem] font-semibold tracking-[-0.01em] text-ink">
            {text({ sv: "Kundtjänstens journal", en: "Customer service journal" })}
          </h2>
          <JournalVy />
        </section>
      ) : null}

      {!iris && !support ? (
        <p className="text-[0.9375rem] text-ink-muted">
          {text({
            sv: "Ingen av era agenter har körningar att visa här ännu.",
            en: "None of your agents has runs to show here yet."
          })}
        </p>
      ) : null}
    </div>
  );
}
