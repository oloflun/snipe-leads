import type { Metadata } from "next";
import { ProductPage } from "@/components/marketing/ProductPage";
import { notFoundOnTenant } from "@/lib/tenants/server";

export const metadata: Metadata = {
  title: "Iris, Snajps leadsagent: din säljare som aldrig sover",
  description:
    "Iris letar prospekt utifrån er produkt, gör en behovsanalys med synliga källor och skriver det utgående mejlet. Inget skickas utan att du godkänt det.",
  alternates: { canonical: "/leads" }
};

export default async function Page() {
  await notFoundOnTenant();
  return <ProductPage initial="leads" />;
}
