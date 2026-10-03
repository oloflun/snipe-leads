"use client";

import { IrisGranskning } from "@/components/leads/IrisGranskning";
import { IrisInkorg } from "@/components/leads/IrisInkorg";
import { useLocale } from "@/lib/i18n";

/**
 * Att göra — det som väntar på ett beslut från dig (Snajp Suite 2026-10-03).
 *
 * Ersätter Iris › Granskning och Iris › Inkorg, som var två menyposter för
 * samma fråga: vad behöver jag göra nu? Båda delarna är befintliga komponenter
 * oförändrade; sidan ger dem bara en gemensam plats.
 *
 * ponytail: bara Iris i dag. Planens fas 2 lägger till kundtjänstens utkast,
 * eskaleringar och förfallna uppgifter via /api/att-gora, och då blir
 * menyposten delad i stället för leads-grindad (lib/routes.ts).
 */
export function AttGora({ demo = false }: Readonly<{ demo?: boolean }>) {
  const { text } = useLocale();
  return (
    <div className="grid gap-12">
      <section aria-labelledby="att-gora-utkast">
        <h2 id="att-gora-utkast" className="mb-5 text-[1.125rem] font-semibold tracking-[-0.01em] text-ink">
          {text({ sv: "Utkast att godkänna", en: "Drafts to approve" })}
        </h2>
        <IrisGranskning demo={demo} />
      </section>

      {/* Leadsmejlen kräver en brevlåda och en session; demon har ingen. */}
      {demo ? null : (
        <section aria-labelledby="att-gora-mejl" className="border-t border-ink/15 pt-8">
          <h2 id="att-gora-mejl" className="mb-5 text-[1.125rem] font-semibold tracking-[-0.01em] text-ink">
            {text({ sv: "Mejl från leads", en: "Email from leads" })}
          </h2>
          <IrisInkorg />
        </section>
      )}
    </div>
  );
}
