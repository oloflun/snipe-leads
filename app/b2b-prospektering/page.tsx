import type { Metadata } from "next";
import { LandningsRutt } from "@/components/marketing/LandningsRutt";
import { sidmeta } from "@/lib/seo";

export const metadata: Metadata = {
  ...sidmeta({
    vag: "/b2b-prospektering",
    titel: "B2B-prospektering för svenska företag | Snajp",
    beskrivning:
      "Så prospekterar ni B2B i Sverige utan att skriva varje mejl själva: urval, research, första mejl och uppföljning, och reglerna för kall kontakt."
  })
};

export default function Page() {
  return <LandningsRutt vag="/b2b-prospektering" />;
}
