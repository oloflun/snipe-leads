import { PageShell } from "@/components/AppShell";
import { EmailStudioEditor } from "@/components/email/EmailStudioEditor";
import { loadEmailStudioData } from "@/lib/data/emails";

export default async function Page() {
  const data = await loadEmailStudioData();

  return (
    <PageShell
      kicker="Email studio"
      title="Personaliseringens manusbord."
      description="Ämnesrad, öppningsrad, cold email och uppföljningar visas tillsammans med signal, källa och CTA."
    >
      <EmailStudioEditor data={data} />
    </PageShell>
  );
}
