import type { Metadata } from "next";
import { LandningsRutt } from "@/components/marketing/LandningsRutt";
import { prisrad, sidmeta } from "@/lib/seo";

export const metadata: Metadata = {
  ...sidmeta({
    vag: "/support-pa-svenska",
    titel: "Support på svenska | Snajp",
    beskrivning: `En svensk supportagent som läser kundmejl och chattar och svarar på svenska ur er kunskapsbas. Saknas underlag tar en människa över. ${prisrad("support")}`
  })
};

export default function Page() {
  return <LandningsRutt vag="/support-pa-svenska" />;
}
