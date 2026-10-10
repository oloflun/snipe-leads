"use client";

import { AppShell } from "@/components/AppShell";
import { useLocale } from "@/lib/i18n";

/**
 * Laddningsläget för de inloggade ytorna — det `loading.tsx` renderar.
 *
 * Utan en loading-gräns visade en flikklick INGENTING förrän hela server-
 * renderingen kommit tillbaka: sidan stod still, menyn markerade den gamla
 * fliken, och en långsam vy (körningsloggen, agentanvändningen) kändes som
 * att klicket inte tagits emot. Med gränsen byter Next adress och rail-
 * markering direkt, och innehållet fylls på när det kommer.
 *
 * Skelettet har ungefär sidornas form (rubrik, en rad nyckeltal, en panel) så
 * att inget hoppar när den riktiga vyn ersätter det.
 */
function Skelett() {
  const { t } = useLocale();
  return (
    <div role="status" aria-live="polite" aria-busy="true">
      <span className="sr-only">{t("state.loading")}</span>
      <div className="h-8 w-48 animate-pulse rounded-input bg-ink/[0.06]" aria-hidden />
      <div className="mt-6 grid grid-cols-2 gap-3 md:grid-cols-4" aria-hidden>
        {[0, 1, 2, 3].map((i) => (
          <div key={i} className="h-20 animate-pulse rounded-card bg-ink/[0.05]" />
        ))}
      </div>
      <div className="mt-4 h-64 animate-pulse rounded-card bg-ink/[0.04]" aria-hidden />
    </div>
  );
}

/** Kundens yta och inställningarna: varje vy bär sitt eget AppShell (PageShell). */
export function LaddarArbetsyta() {
  return (
    <AppShell>
      <section className="mx-auto w-full max-w-[1200px] px-4 py-6 md:px-8 md:py-8">
        <Skelett />
      </section>
    </AppShell>
  );
}

/** Adminytan: skalet och containern bor redan i app/admin/layout.tsx. */
export function LaddarAdmin() {
  return <Skelett />;
}
