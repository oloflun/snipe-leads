import { DraftPortal } from "@/components/DesignDrafts";

export default async function Page({
  params,
}: Readonly<{ params: Promise<{ slug?: string[] }> }>) {
  const { slug = [] } = await params;
  return <DraftPortal variant="editorial-clean" slug={slug} asMain />;
}