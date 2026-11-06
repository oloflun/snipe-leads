import type { Metadata } from "next";
import { LandningsRutt } from "@/components/marketing/LandningsRutt";
import { prisrad, sidmeta } from "@/lib/seo";

export const metadata: Metadata = {
  ...sidmeta({
    vag: "/ai-supportagent",
    titel: "Svensk AI-supportagent för företag | Snajp",
    beskrivning: `Svensk AI-supportagent för företagssupport: sorterar kundmejlen, skriver svaren ur er kunskapsbas och lämnar över resten. ${prisrad("support")}`
  })
};

export default function Page() {
  return <LandningsRutt vag="/ai-supportagent" />;
}
