import { notFound } from "next/navigation";
import { DraftPortal } from "@/components/DesignDrafts";
import { isDraftVariant, showcaseStaticSlugs } from "@/lib/design-drafts";

export function generateStaticParams() {
  return ["editorial-clean", "modern-blend"].flatMap((variant) =>
    showcaseStaticSlugs.map((slug) => ({ variant, slug }))
  );
}

export default async function Page({
  params
}: Readonly<{ params: Promise<{ variant: string; slug?: string[] }> }>) {
  const { variant, slug = [] } = await params;

  if (!isDraftVariant(variant)) {
    notFound();
  }

  return <DraftPortal variant={variant} slug={slug} />;
}
