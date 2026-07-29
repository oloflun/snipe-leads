import type { Metadata } from "next";
import { ProductPage } from "@/components/marketing/ProductPage";

export const metadata: Metadata = {
  title: "Snajp Leads, säljmejl som låter som du",
  description:
    "Snajp Leads läser publika signaler om svenska bolag och skriver utkastet till säljmejlet. Inget skickas utan att du godkänt det.",
  alternates: { canonical: "/leads" }
};

export default function Page() {
  return <ProductPage initial="leads" />;
}
