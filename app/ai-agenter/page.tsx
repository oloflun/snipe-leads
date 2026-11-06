import type { Metadata } from "next";
import { LandningsRutt } from "@/components/marketing/LandningsRutt";
import { prisrad, sidmeta } from "@/lib/seo";

export const metadata: Metadata = {
  ...sidmeta({
    vag: "/ai-agenter",
    titel: "Svenska AI-agenter för företag | Snajp",
    beskrivning: `Snajps två svenska AI-agenter: Iris hittar och skriver till nya B2B-kunder, supportagenten svarar dem ni har. Båda med Snajp Duo. ${prisrad("duo")}`
  })
};

export default function Page() {
  return <LandningsRutt vag="/ai-agenter" />;
}
