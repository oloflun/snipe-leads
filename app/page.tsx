import { redirect } from "next/navigation";
import { ProductPage } from "@/components/marketing/ProductPage";
import { getCurrentTenant } from "@/lib/tenants/server";

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

  return <ProductPage initial="leads" />;
}
