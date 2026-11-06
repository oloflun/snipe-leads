import type { Metadata } from "next";
import { LandningsRutt } from "@/components/marketing/LandningsRutt";
import { sidmeta } from "@/lib/seo";

export const metadata: Metadata = {
  ...sidmeta({
    vag: "/jamfor-supportagenter",
    titel: "Jämför supportagenter och supportbotar i Sverige | Snajp",
    beskrivning:
      "Supportagenter och chattbotar för svenska företag jämförda: svenska svar, överlämning, var datan bor och pris, kontrollerat mot leverantörernas sidor."
  })
};

export default function Page() {
  return <LandningsRutt vag="/jamfor-supportagenter" />;
}
