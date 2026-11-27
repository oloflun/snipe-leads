import { KorningVy } from "@/components/crm/app/iris/KorningVy";

export default async function Page({ params }: Readonly<{ params: Promise<{ id: string }> }>) {
  const { id } = await params;
  return <KorningVy id={decodeURIComponent(id)} />;
}
