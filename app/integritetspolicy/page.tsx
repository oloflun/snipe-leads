import type { Metadata } from "next";
import { notFoundOnTenant } from "@/lib/tenants/server";
import { IntegritetspolicySida } from "./IntegritetspolicySida";

export const metadata: Metadata = {
  title: "Integritetspolicy — Snajp",
  description:
    "Så behandlar Snajp personuppgifter: vilka uppgifter, varför, vilka underleverantörer som är inblandade och vilka rättigheter du har.",
  alternates: { canonical: "/integritetspolicy" }
};

/**
 * OBS: `notFoundOnTenant` — sidan är SNAJPS policy, inte kundens. På kundens
 * domän hade den beskrivit fel personuppgiftsansvarig för fel behandling.
 * Samma grind som app/support/page.tsx använder.
 *
 * Texten bor i IntegritetspolicySida.tsx på svenska och engelska (Antons
 * beslut 2026-10-02); den engelska är en översättning av den svenska.
 */
/* TODO: juridiskt granskad text krävs innan publicering.
    Sidan har rättslig betydelse och är skriven av en agent, inte av en
    jurist. Kontrollera särskilt tre saker, i den ordningen:
      1. Underleverantörernas dataregion och avtalsnivå (lib/bolag.ts —
         fälten är platshållare och UTELÄMNAS i vyn tills de fylls i).
      2. Påståendet om modelleverantörens träning: det STÅR INTE här, och
         får inte skrivas tillbaka utan att någon läst avtalet.
         Se docs/JURIDIK_ATGARDER.md, P0.1c.
      3. Gallringstiden 24 månader mot det gallringsjobbet faktiskt kör
         (supabase/migrations/048_gallring.sql). Två tal som glidit isär är
         värre än inget tal alls.
    Den gula utkastrutan är BORTTAGEN UR VYN på begäran 2026-08-25 och ska
    inte skrivas tillbaka. Den här markeringen är för utvecklaren, inte för
    besökaren. Granskningen gäller båda språkversionerna. */
export default async function Page() {
  await notFoundOnTenant();

  return <IntegritetspolicySida />;
}
