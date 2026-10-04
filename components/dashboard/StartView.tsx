"use client";

import { PageShell } from "@/components/AppShell";
import { Oversikten } from "@/components/dashboard/Oversikt";

/**
 * Startsidan — en ÖVERSIKT, inte agentens råa arbetsvy.
 *
 * Svarar på "vad har hänt och vad väntar på mig" med siffror ur kundens egen
 * tenant (components/dashboard/Oversikt.tsx). Arbetsvyerna (Leads, Kundtjänst,
 * Kvitton) gör jobbet.
 *
 * Snajp Suite (2026-10-03): EN översikt för alla agenter, nyckeltalen överst.
 * Borta: "Gemensam översikt" (två länkkort utan data, DuoSummary), de staplade
 * leads- och kundtjänstdelarna med var sitt "N utkast väntar"-kort, och
 * kunskapsbaskortet längst ned (uppladdningen bor i Inställningar ›
 * Kunskapsbas; en tom bas syns som larm i lägesraden och som Kom igång-rad).
 *
 * `demo` går vidare till översikten, som byter ut backend-anropen mot
 * exempeldata i webbläsaren — utan den anropade /demo den inloggade backenden.
 */
export function StartView({ demo = false }: Readonly<{ demo?: boolean }>) {
  return (
    <PageShell title={{ sv: "Översikt", en: "Overview" }}>
      <Oversikten demo={demo} />
    </PageShell>
  );
}
