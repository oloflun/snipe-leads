import { ContactDetailView } from "@/components/WorkspaceViews";
import { contacts } from "@/lib/mock-data";

export function generateStaticParams() {
  return contacts.map((contact) => ({ id: contact.id }));
}

export default async function Page({ params }: Readonly<{ params: Promise<{ id: string }> }>) {
  const { id } = await params;
  return <ContactDetailView id={id} />;
}
