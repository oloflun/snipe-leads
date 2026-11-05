import type { Metadata } from "next";
import { LandningsRutt } from "@/components/marketing/LandningsRutt";
import { prisrad, sidmeta } from "@/lib/seo";

export const metadata: Metadata = {
  ...sidmeta({
    vag: "/ai-agenter",
    titel: "AI-agenter för svenska företag: sälj och kundtjänst | Snajp",
    beskrivning: `Snajps två AI-agenter: Iris hittar och skriver till nya B2B-kunder, supportagenten svarar dem ni har. Båda med Snajp Duo. ${prisrad("duo")}`
  })
};

export default function Page() {
  return <LandningsRutt vag="/ai-agenter" />;
}
