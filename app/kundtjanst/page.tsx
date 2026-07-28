import { PageShell } from "@/components/AppShell";
import { PilotWorkspace } from "@/components/snajp/PilotWorkspace";

export const metadata = {
  title: "Kundtjänst — Snajp-Support"
};

// Skyddad pilot-arbetsyta: riktig kundinkorg, riktiga utskick. Skild från den
// publika demon på /snajp-support både på sid- och datanivå (egen tenant).
// Åtkomst gated i middleware.ts + sessionskontroll i app/api/kundtjanst-proxyn.
export default function Page() {
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
