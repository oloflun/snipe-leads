import type { Metadata } from "next";
import { JsonLd } from "@/components/JsonLd";
import { FaqDragspel } from "@/components/marketing/FaqDragspel";
import { InnehallsSida, SidAvslut, SidRubrik } from "@/components/marketing/InnehallsSida";
import { KONTAKT_MEJL } from "@/components/marketing/copy";
import { FAQ } from "@/lib/faq";
import { faqSida, graf, sidmeta } from "@/lib/seo";
import { notFoundOnTenant } from "@/lib/tenants/server";

export const metadata: Metadata = {
  ...sidmeta({
    vag: "/faq",
    titel: "Frågor och svar om Snajp: AI-SDR, leads och kundtjänst",
    beskrivning:
      "Vad Snajps AI-agenter gör, var datan kommer ifrån, vad det kostar, hur GDPR hanteras och hur ni kommer igång med leads och kundtjänst på svenska."
  })
};

// Samma frågor som dragspelet, vars svar står i HTML:en även när de är
// hopfällda (FaqDragspel).
const SCHEMA = graf(faqSida(FAQ.map((p) => ({ fraga: p.fraga.sv, svar: p.svar.map((s) => s.sv).join(" ") }))));

/**
 * `notFoundOnTenant` av samma skäl som integritetspolicyn: sidan svarar på
 * frågor om SNAJP som leverantör. På en kunds egen domän hade den beskrivit
 * fel bolag för fel besökare.
 */
export default async function Page() {
  await notFoundOnTenant();

  return (
    <InnehallsSida>
      <JsonLd data={SCHEMA} />
      <SidRubrik
        rubrik="Frågor och svar"
        ingress="Det vi oftast får frågor om, besvarat kort. Hittar du inte svaret tar vi det på en demo i stället."
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
