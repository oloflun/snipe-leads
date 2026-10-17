"use client";

import { PageShell } from "@/components/AppShell";
import { Aktivitet } from "@/components/dashboard/Aktivitet";

/**
 * Startsidan: Översikt.
 *
 * Antons beställning 2026-10-07: den förra översikten (hälsning, fyra
 * nyckeltal och "N saker väntar på dig") ersattes av Aktivitet, som fick
 * namnet Översikt och tog över fliken. Väntande saker bor i Att göra.
 *
 * Samma komponent på kundens /dashboard, adminens /admin/arbetsyta och /demo.
 * `demo` byter backend-anropen mot exempeldata i webbläsaren.
 */
export function StartView({ demo = false }: Readonly<{ demo?: boolean }>) {
  return (
    <PageShell title={{ sv: "Översikt", en: "Overview" }}>
      <Aktivitet demo={demo} />
    </PageShell>
  );
}
