import { CompanyDetailView } from "@/components/WorkspaceViews";
import { companies } from "@/lib/mock-data";

export function generateStaticParams() {
  return companies.map((company) => ({ id: company.id }));
}

export default async function Page({ params }: Readonly<{ params: Promise<{ id: string }> }>) {
  const { id } = await params;
  return <CompanyDetailView id={id} />;
}
