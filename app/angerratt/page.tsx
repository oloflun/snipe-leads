import type { Metadata } from "next";
import { notFoundOnTenant } from "@/lib/tenants/server";
import { AngerrattSida } from "./AngerrattSida";

export const metadata: Metadata = {
  title: "Distansavtal och ångerrätt — Snajp",
  description:
    "Vad distansavtalslagen innebär för avtal med Snajp: lagen skyddar konsumenter, Snajps tjänster tecknas av företag — och vad som gäller i stället.",
  alternates: { canonical: "/angerratt" }
};

/**
 * Informationen om distansavtalslagen som onboardingens villkorskryssruta
 * länkar till (OnboardingWizard, paketsteget — sista steget).
 *
 * ## Rättsläget som texten bygger på (kontrollerat 2026-09-29)
 *
 * Lag (2005:59) om distansavtal och avtal utanför affärslokaler ger KONSUMENTER
 * 14 dagars ångerrätt vid distansavtal. En konsument är en fysisk person som
 * handlar huvudsakligen för ändamål utanför näringsverksamhet — ett företag
 * som tecknar avtal om Snajps agenter omfattas alltså inte, och det gäller
 * även enskilda näringsidkare som tecknar för sin verksamhet.
 *
 * Texten säger det RAKT UT i stället för att gömma det: en sida som räknar
 * upp lagens rättigheter utan att säga att de inte gäller köparen vore
 * vilseledande åt andra hållet. Konsumentfallet beskrivs ändå, eftersom
 * gränsdragningen (huvudsakligen privat bruk) inte är vår att avgöra ensidigt.
 *
 * Sidan är tvåspråkig sedan 2026-10-02 (Antons beslut): texten bor i
 * AngerrattSida.tsx, och den engelska är en översättning av den svenska.
 */
export default async function Page() {
  await notFoundOnTenant();

  return <AngerrattSida />;
}
