import type { Metadata } from "next";
import { LandningsRutt } from "@/components/marketing/LandningsRutt";
import { prisrad, sidmeta } from "@/lib/seo";

export const metadata: Metadata = {
  ...sidmeta({
    vag: "/b2b-leads",
    titel: "Svenska B2B-leads | Snajp",
    beskrivning: `Svenska B2B-leads utvalda efter bransch, ort och storlek, med kontaktväg, research och ett färdigt säljmejl att godkänna. ${prisrad("leads")}`
  })
};

export default function Page() {
  return <LandningsRutt vag="/b2b-leads" />;
}
