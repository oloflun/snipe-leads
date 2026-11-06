import type { Metadata } from "next";
import { LandningsRutt } from "@/components/marketing/LandningsRutt";
import { prisrad, sidmeta } from "@/lib/seo";

export const metadata: Metadata = {
  ...sidmeta({
    vag: "/svensk-ai-sdr",
    titel: "Svensk AI-SDR | Iris från Snajp",
    beskrivning: `Iris är en svensk AI-SDR för B2B-företag i Sverige. Hon väljer ut rätt bolag, läser på om dem och skriver säljmejlet på svenska. ${prisrad("leads")}`
  })
};

export default function Page() {
  return <LandningsRutt vag="/svensk-ai-sdr" />;
}
