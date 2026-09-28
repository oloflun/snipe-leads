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
      <PageHeader rubrik="Integrationer" />
      <SystemSektion />
      <KanalSektion />
    </div>
  );
}
