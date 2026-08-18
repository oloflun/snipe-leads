import { WorkspaceSection } from "@/components/dashboard/WorkspaceSection";

/**
 * Kundens arbetsyta. Tunn med flit — dispatchern bor i WorkspaceSection, som
 * adminytan använder likadant. Se den filen för varför de delar kod.
 */
export default async function Page({
  params
}: Readonly<{ params: Promise<{ slug?: string[] }> }>) {
  const { slug = [] } = await params;
  return <WorkspaceSection slug={slug} />;
}
