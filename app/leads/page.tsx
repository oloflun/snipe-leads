import type { Metadata } from "next";
import { ProductPage } from "@/components/marketing/ProductPage";
import { notFoundOnTenant } from "@/lib/tenants/server";

export const metadata: Metadata = {
  title: "Snajp Leads, din säljare som aldrig sover",
  description:
    "Leads-agenten letar prospekt utifrån er produkt, gör en behovsanalys och skriver det utgående mejlet. Inget skickas utan att du godkänt det.",
  alternates: { canonical: "/leads" }
};

export default async function Page() {
  await notFoundOnTenant();
  return <ProductPage initial="leads" />;
}
