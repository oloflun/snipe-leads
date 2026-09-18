"use client";

import { PageHeader } from "@/components/PageHeader";
import { KanalSektion } from "@/components/integrationer/Kanaler";
import { SystemSektion } from "@/components/integrationer/System";

/**
 * Integrationer (bd snipe-36u): kundens egna system och meddelandekanaler.
 *
 * Till skillnad från Inställningar är det här en REDIGERINGSYTA. Det finns
 * ingen annan: integrationerna och kanalerna konfigureras bara här.
 */
export function IntegrationerVy() {
  return (
    <div className="space-y-12">
      <PageHeader
        rubrik="Integrationer"
        beskrivning="Koppla agenten till era egna system och kanaler. Den kan slå upp ordrar och konton, skapa ärendet i ert ärendesystem när den lämnar över, och svara kunderna där de redan skriver."
      />
      <SystemSektion />
      <KanalSektion />
    </div>
  );
}
