import type { Metadata } from "next";
import { FaqDragspel } from "@/components/marketing/FaqDragspel";
import { InnehallsSida, SidAvslut, SidRubrik } from "@/components/marketing/InnehallsSida";
import { KONTAKT_MEJL } from "@/components/marketing/copy";
import { notFoundOnTenant } from "@/lib/tenants/server";

export const metadata: Metadata = {
  title: "FAQ — Snajp",
  description:
    "Vad Snajp är, var datan kommer ifrån, vad som händer med kunduppgifter och hur ni kommer igång.",
  alternates: { canonical: "/faq" }
};

/**
 * `notFoundOnTenant` av samma skäl som integritetspolicyn: sidan svarar på
 * frågor om SNAJP som leverantör. På en kunds egen domän hade den beskrivit
 * fel bolag för fel besökare.
 */
export default async function Page() {
  await notFoundOnTenant();

  return (
    <InnehallsSida>
      <SidRubrik
        rubrik="Frågor och svar"
        ingress="Det vi får frågan om oftast, besvarat kort. Hittar du inte svaret tar vi det på en demo i stället."
      />

      <FaqDragspel />

      <SidAvslut
        rubrik="Kvar med en fråga?"
        text="Femton minuter räcker för att se plattformen köra mot era egna ärenden. Vi säger rakt ut om vi tror att det passar er."
        primar={{ etikett: "Boka demo", href: "/boka-demo" }}
        sekundar={{ etikett: "Skriv till oss", href: `mailto:${KONTAKT_MEJL}` }}
      />
    </InnehallsSida>
  );
}
