import { CampaignDetailView } from "@/components/WorkspaceViews";
import { campaigns } from "@/lib/mock-data";

export function generateStaticParams() {
  return campaigns.map((campaign) => ({ id: campaign.id }));
}

export default async function Page({ params }: Readonly<{ params: Promise<{ id: string }> }>) {
  const { id } = await params;
  return <CampaignDetailView id={id} />;
}
