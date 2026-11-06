import type { Metadata } from "next";
import { LandningsRutt } from "@/components/marketing/LandningsRutt";
import { prisrad, sidmeta } from "@/lib/seo";

export const metadata: Metadata = {
  ...sidmeta({
    vag: "/ai-supportagent",
    titel: "AI-supportagent för företagssupport på svenska | Snajp",
    beskrivning: `En AI-supportagent som sorterar kundmejlen, skriver svaren ur er kunskapsbas och lämnar över det som kräver en människa. ${prisrad("support")}`
  })
};

export default function Page() {
  return <LandningsRutt vag="/ai-supportagent" />;
}
