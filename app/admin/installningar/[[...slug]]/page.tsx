import { SettingsSection } from "@/components/settings/SettingsSection";

export const dynamic = "force-dynamic";

/**
 * Samma inställningssidor, inuti adminytan.
 *
 * Statisk mapp och inte `app/admin/[...slug]`: den senare skickar allt den
 * fångar till `WorkspaceSection`, som inte känner till några inställningar och
 * hade svarat 404. Ett statiskt segment vinner över en catch-all, så den här
 * filen tar `/admin/installningar/*` och arbetsytans dispatcher tar resten.
 *
 * Grinden är `app/admin/layout.tsx` (notFound för den som inte är
 * plattformsadmin). Entitlement per produkt kontrolleras dessutom inuti
 * SettingsSection, precis som på kundens yta.
 */
export default async function Page({
  params
}: Readonly<{ params: Promise<{ slug?: string[] }> }>) {
  const { slug = [] } = await params;
  return <SettingsSection slug={slug} />;
}
