import type { Metadata } from "next";
import { ProductPage } from "@/components/marketing/ProductPage";
import { notFoundOnTenant } from "@/lib/tenants/server";

export const metadata: Metadata = {
  title: "Snajp Support, svar hämtade ur era egna texter",
  description:
    "Snajp Support läser inkommande kundmejl, sorterar dem i rätt fack och svarar utifrån er kunskapsbas. Saknas underlag går ärendet till en människa.",
  alternates: { canonical: "/support" }
};

export default async function Page() {
  await notFoundOnTenant();
  return <ProductPage initial="support" />;
}
