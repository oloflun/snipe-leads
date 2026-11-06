import type { Metadata } from "next";
import { LandningsRutt } from "@/components/marketing/LandningsRutt";
import { sidmeta } from "@/lib/seo";

export const metadata: Metadata = {
  ...sidmeta({
    vag: "/leads-i-inkorgen",
    titel: "Svenska leads i inkorgen, med mejlet skrivet | Snajp",
    beskrivning:
      "Nya svenska B2B-leads och färdiga säljmejl samlas i er granskningskö. Ni godkänner, svaren hamnar i samma tråd och uppföljningen stoppar av sig själv."
  })
};

export default function Page() {
  return <LandningsRutt vag="/leads-i-inkorgen" />;
}
