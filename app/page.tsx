import type { Metadata } from "next";
import { redirect } from "next/navigation";
import { JsonLd } from "@/components/JsonLd";
import { ProductPage } from "@/components/marketing/ProductPage";
import { KONTAKT_MEJL } from "@/components/marketing/copy";
import { hemFragor } from "@/components/marketing/copy-sections";
import { faqSida, graf, organisation, produkt, sidmeta, webbplats } from "@/lib/seo";
import { getCurrentTenant } from "@/lib/tenants/server";

// Kanonisk adress och delningskort bara här, inte i layouten: en canonical i
// layouten ärvs av varje sida som saknar en egen, och /login hade pekat på
// startsidan som sin kanoniska version.
export const metadata: Metadata = {
  ...sidmeta({
    vag: "/",
    titel: "Snajp | Svensk AI-SDR och AI-kundtjänst för B2B",
    beskrivning:
      "Snajp är två svenska AI-agenter. Iris skriver säljmejlen till nya B2B-kunder och supportagenten svarar kundmejlen ur er kunskapsbas. Testa båda direkt."
  })
};

// Organisationen och webbplatsen bor på startsidan, som Google läser dem;
// produktsidorna och sökordssidorna pekar hit med @id.
const SCHEMA = graf(
  organisation(KONTAKT_MEJL),
  webbplats(),
  produkt("leads"),
  produkt("support"),
  produkt("duo"),
  // Frågorna står synliga på startsidan, så de får stå i schemat.
  faqSida(hemFragor.map((o) => ({ fraga: o.q.sv, svar: o.a.sv })))
);

export default async function Page() {
  const tenant = await getCurrentTenant();

  // På en kunds domän får roten aldrig visa Snajps marknadsföringssajt. Utan
  // detta landade Livrustnings besökare på "Säljmejl som låter som du" med
  // Snajps logotyp — leverantörens säljpitch på kundens egen adress.
  //
  // Det enda vi levererar på kundens domän är chatten. Kundens egen hemsida
  // ligger kvar där den ligger och byggs inte om.
  if (tenant) {
    redirect(`/chat/${tenant.slug}`);
  }

  return (
    <>
      <JsonLd data={SCHEMA} />
      {/* En egen sida, inte /leads (Anton 2026-11-07): egen H1 och kropp, och ingen omskrivning till /leads. */}
      <ProductPage initial="leads" hem />
    </>
  );
}
