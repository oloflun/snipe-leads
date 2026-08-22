import { SettingsSection } from "@/components/settings/SettingsSection";

export const dynamic = "force-dynamic";

/**
 * Kundens inställningar. Tunn med flit — dispatchern bor i SettingsSection,
 * som adminytan använder likadant. Se den filen för varför de delar kod.
 */
export default async function Page({
  params
}: Readonly<{ params: Promise<{ slug?: string[] }> }>) {
  const { slug = [] } = await params;
  return <SettingsSection slug={slug} />;
}
