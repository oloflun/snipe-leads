import type { Metadata } from "next";
import { LandningsRutt } from "@/components/marketing/LandningsRutt";
import { prisrad, sidmeta } from "@/lib/seo";

export const metadata: Metadata = {
  ...sidmeta({
    vag: "/supportchatt",
    titel: "Svensk supportchatt till er hemsida | Snajp",
    beskrivning: `Svensk supportagent för hemsidan: en supportbot som svarar besökarna ur er kunskapsbas. En rad kod och obegränsade chattar. ${prisrad("support")}`
  })
};

export default function Page() {
  return <LandningsRutt vag="/supportchatt" />;
}
