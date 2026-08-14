import { PageShell } from "@/components/AppShell";
import { PilotWorkspace } from "@/components/snajp/PilotWorkspace";
import { getWorkspaceContext } from "@/lib/workspace";
import { isPilotWorkspace } from "@/lib/snajp/pilot";

export const metadata = {
  title: "Kundtjänst — Snajp-Support"
};

// Skyddad pilot-arbetsyta: riktig kundinkorg, riktiga utskick. Skild från den
// publika demon på /demo/snajp både på sid- och datanivå (egen tenant).
//
// Tre lager: middleware.ts kräver inloggning, den här sidan kräver rätt
// ORGANISATION, och proxyn i app/api/kundtjanst gör om samma kontroll (så den
// håller även om någon anropar API:t direkt).
export default async function Page() {
  const context = await getWorkspaceContext();
  const allowed = context ? isPilotWorkspace(context.workspace.id) : false;

  if (!allowed) {
    return (
      <PageShell
        kicker="Kundtjänst"
        title="Ingen åtkomst till den här arbetsytan."
        description="Pilot-arbetsytan innehåller ett annat bolags riktiga kundärenden, och är därför begränsad till den organisation som äger inkorgen. Er egen AI-kundtjänst finns under Snajp-Support."
      >
        <div />
      </PageShell>
    );
  }

  return (
    <PageShell
      kicker="Kundtjänst"
      title="Dagens ärenden."
      description="Inkommande kundmail sorterade i fack med färdiga svarsförslag. Granska, redigera och skicka — inget går ut utan att du godkänt det."
    >
      <PilotWorkspace />
    </PageShell>
  );
}
