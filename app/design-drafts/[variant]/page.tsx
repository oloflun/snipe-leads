import { notFound } from "next/navigation";
import { DraftLanding } from "@/components/DesignDrafts";
import { isDraftVariant } from "@/lib/design-drafts";

export function generateStaticParams() {
  return [{ variant: "editorial-clean" }, { variant: "modern-blend" }];
}

export default async function Page({ params }: Readonly<{ params: Promise<{ variant: string }> }>) {
  const { variant } = await params;

  if (!isDraftVariant(variant)) {
    notFound();
  }

  return <DraftLanding variant={variant} />;
}
