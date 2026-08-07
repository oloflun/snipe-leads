import { notFound } from "next/navigation";
import { DraftLanding } from "@/components/DesignDrafts";
import { isDraftVariant } from "@/lib/design-drafts";
import { notFoundOnTenant } from "@/lib/tenants/server";

export function generateStaticParams() {
  return [{ variant: "editorial-clean" }, { variant: "modern-blend" }];
}

export default async function Page({ params }: Readonly<{ params: Promise<{ variant: string }> }>) {
  const { variant } = await params;

  // Snajps interna designutkast finns inte på en kunds domän.
  await notFoundOnTenant();

  if (!isDraftVariant(variant)) {
    notFound();
  }

  return <DraftLanding variant={variant} />;
}
