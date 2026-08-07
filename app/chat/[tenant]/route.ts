import { redirect } from "next/navigation";
import { getTenant } from "@/lib/tenants";
import { notFound } from "next/navigation";

/**
 * Den publika supportlänken. Kunden lägger EN statisk adress på sin hemsida —
 * /chat/livrustning — och varje besökare får en egen session med egen URL.
 *
 * Länken kan lika gärna klistras in i ett mejl vid direktkontakt; den fungerar
 * likadant och kräver ingen inloggning.
 */
export async function GET(_request: Request, { params }: { params: Promise<{ tenant: string }> }) {
  const { tenant } = await params;

  if (!getTenant(tenant)) {
    notFound();
  }

  redirect(`/chat/${tenant}/${crypto.randomUUID()}`);
}
