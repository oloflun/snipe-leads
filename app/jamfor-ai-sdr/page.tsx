import type { Metadata } from "next";
import { LandningsRutt } from "@/components/marketing/LandningsRutt";
import { sidmeta } from "@/lib/seo";

export const metadata: Metadata = {
  ...sidmeta({
    vag: "/jamfor-ai-sdr",
    titel: "Jämför AI-SDR och leadsagenter i Sverige | Snajp",
    beskrivning:
      "AI-SDR och leadsagenter för svenska företag jämförda: språk, godkännande, var datan bor och pris, kontrollerat mot leverantörernas egna sidor."
  })
};

export default function Page() {
  return <LandningsRutt vag="/jamfor-ai-sdr" />;
}
