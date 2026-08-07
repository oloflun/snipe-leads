import type { Metadata } from "next";
import { ProductPage } from "@/components/marketing/ProductPage";
import { notFoundOnTenant } from "@/lib/tenants/server";

export const metadata: Metadata = {
  title: "Snajp Leads, säljmejl som låter som du",
  description:
    "Snajp Leads läser publika signaler om svenska bolag och skriver utkastet till säljmejlet. Inget skickas utan att du godkänt det.",
  alternates: { canonical: "/leads" }
};

export default async function Page() {
  await notFoundOnTenant();
  return <ProductPage initial="leads" />;
}
