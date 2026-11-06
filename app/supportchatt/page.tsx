import type { Metadata } from "next";
import { LandningsRutt } from "@/components/marketing/LandningsRutt";
import { prisrad, sidmeta } from "@/lib/seo";

export const metadata: Metadata = {
  ...sidmeta({
    vag: "/supportchatt",
    titel: "Svensk supportchatt och AI-chatbot till hemsidan | Snajp",
    beskrivning: `En svensk AI-chatt på er hemsida som svarar besökarna ur er kunskapsbas. En rad kod, era färger och obegränsade chattar. ${prisrad("support")}`
  })
};

export default function Page() {
  return <LandningsRutt vag="/supportchatt" />;
}
