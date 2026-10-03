"use client";

import { Dashboard } from "@/components/snajp/Dashboard";

/**
 * Iris › Inkorg — leads-inkorgen (plan del D, migration 084).
 *
 * Samma vy som kundtjänstinkorgen, filtrerad på klass='lead': svar från
 * prospekt och nya inkommande leads, sorterade dit av reglerna eller Jev i
 * app/email_pipeline/klassning.py. En kund med bara leads-paketet kopplar sin
 * brevlåda med syfte "leads" (Inställningar › Inkorgar) och får allt hit.
 * Ett supportutkast skrivs aldrig för en rad här.
 */
export function IrisInkorg() {
  return <Dashboard lager="leads" />;
}
