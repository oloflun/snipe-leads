import { PageShell } from "@/components/AppShell";
import { Dashboard } from "@/components/snajp/Dashboard";

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
      <Dashboard mode="pilot" apiBase="/api/kundtjanst" />
    </PageShell>
  );
}
