import type { Metadata } from "next";
import { JsonLd } from "@/components/JsonLd";
import { ProductPage } from "@/components/marketing/ProductPage";
import { sectionCopy } from "@/components/marketing/copy-sections";
import { FAMILJ } from "@/lib/landningar";
import { brodsmulor, faqSida, graf, prisrad, produkt, sidmeta } from "@/lib/seo";
import { notFoundOnTenant } from "@/lib/tenants/server";

export const metadata: Metadata = {
  ...sidmeta({
    vag: "/leads",
    titel: "Leadsagent för B2B-leads på svenska | Iris från Snajp",
    beskrivning: `Iris är Snajps leadsagent och AI-SDR. Hon letar prospekt utifrån er produkt, gör en behovsanalys med källor och skriver mejlet på svenska. ${prisrad("leads")}`
  })
};

const SCHEMA = graf(
  produkt("leads"),
  brodsmulor([{ namn: "Snajp", vag: "/" }, { namn: FAMILJ.leads.namn.sv, vag: FAMILJ.leads.vag }]),
  // Invändningarna står synliga på sidan, så de får stå i schemat.
  faqSida(sectionCopy.leads.objections.map((o) => ({ fraga: o.q.sv, svar: o.a.sv })))
);

export default async function Page() {
  await notFoundOnTenant();
  return (
    <>
      <JsonLd data={SCHEMA} />
      <ProductPage initial="leads" />
    </>
  );
}
