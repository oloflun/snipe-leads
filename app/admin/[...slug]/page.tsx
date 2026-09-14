import { WorkspaceSection } from "@/components/dashboard/WorkspaceSection";

export const dynamic = "force-dynamic";

/**
 * Arbetsytans flikar INUTI adminytan: /admin/leads, /admin/support, /admin/emails …
 *
 * Vanlig catch-all och inte optional: `[[...slug]]` matchar även /admin självt
 * och kan därför inte samexistera med de statiska syskonen (kunder, korningar,
 * handelser). Med `[...slug]` vinner de statiska routerna, och den här fångar
 * bara det som blir över.
 *
 * Grinden är app/admin/layout.tsx, som svarar notFound() för den som inte är
 * plattformsadmin. Entitlement per produkt kontrolleras dessutom inuti
 * WorkspaceSection, precis som på kundens yta.
 */
export default async function Page({
  params
}: Readonly<{ params: Promise<{ slug?: string[] }> }>) {
  const { slug = [] } = await params;
  return <WorkspaceSection slug={slug} />;
}
