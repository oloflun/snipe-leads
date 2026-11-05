import type { Metadata } from "next";
import { LandningsRutt } from "@/components/marketing/LandningsRutt";
import { prisrad, sidmeta } from "@/lib/seo";

export const metadata: Metadata = {
  ...sidmeta({
    vag: "/support-pa-svenska",
    titel: "Support på svenska med AI-agent för kundtjänst | Snajp",
    beskrivning: `Snajp Support läser kundmejl och chattar och svarar på svenska ur er egen kunskapsbas. Saknas underlag går ärendet till en människa. ${prisrad("support")}`
  })
};

export default function Page() {
  return <LandningsRutt vag="/support-pa-svenska" />;
}
