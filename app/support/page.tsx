import type { Metadata } from "next";
import { JsonLd } from "@/components/JsonLd";
import { ProductPage } from "@/components/marketing/ProductPage";
import { sectionCopy } from "@/components/marketing/copy-sections";
import { FAMILJ } from "@/lib/landningar";
import { brodsmulor, faqSida, graf, prisrad, produkt, sidmeta } from "@/lib/seo";
import { notFoundOnTenant } from "@/lib/tenants/server";

export const metadata: Metadata = {
  ...sidmeta({
    vag: "/support",
    titel: "Support som svarar på svenska | Snajp Support",
    beskrivning: `Snajps supportagent läser kundmejl och chattar och svarar era kunder på svenska ur er kunskapsbas. Det den inte vet går till en människa. ${prisrad("support")}`
  })
};

const SCHEMA = graf(
  produkt("support"),
  brodsmulor([{ namn: "Snajp", vag: "/" }, { namn: FAMILJ.support.namn.sv, vag: FAMILJ.support.vag }]),
  // Invändningarna står synliga på sidan, så de får stå i schemat.
  faqSida(sectionCopy.support.objections.map((o) => ({ fraga: o.q.sv, svar: o.a.sv })))
);

export default async function Page() {
  await notFoundOnTenant();
  return (
    <>
      <JsonLd data={SCHEMA} />
      <ProductPage initial="support" />
    </>
  );
}
