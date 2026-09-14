import type { Metadata } from "next";
import { ProductPage } from "@/components/marketing/ProductPage";
import { notFoundOnTenant } from "@/lib/tenants/server";

/**
 * Bokföringens marknadssida. Samma skal som /leads och /support.
 *
 * Rubriken lovar avsiktligt mindre än de andra två: "underlag", inte
 * "bokföring". Produkten föreslår kontering och räknar perioden — den bokför
 * ingenting, och beskrivningen nedan är det första stället en besökare möter
 * den gränsen. Se `FORBEHALL` i snajp-support/app/api/bookkeeping.py, som är
 * samma sak sagd för ett JSON-svar.
 */
export const metadata: Metadata = {
  title: "Snajp Bokföring, från kvitto till bokfört på sekunder",
  description:
    "Bokföringsagenten läser av kvitton och fakturor, föreslår kontering ur BAS-kontoplanen och räknar perioden. Den bokför ingenting själv — du godkänner innan något förs in.",
  alternates: { canonical: "/bokforing" }
};

export default async function Page() {
  await notFoundOnTenant();
  return <ProductPage initial="bookkeeping" />;
}
