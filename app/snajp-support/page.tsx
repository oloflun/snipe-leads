import { PageShell } from "@/components/AppShell";
import { SnajpSupportDemo } from "@/components/snajp/SnajpSupportDemo";

export const metadata = {
  title: "Snajp-Support — AI-kundtjänst som sorterar och svarar"
};

export default function Page() {
  return (
    <PageShell
      kicker="Snajp-Support"
      title="Kundtjänst som svarar sig själv."
      description="En AI-agent som läser inkommande kundmail, sorterar dem i rätt fack, svarar utifrån er kunskapsbas — och lämnar över till en människa exakt när det behövs. Testa demon nedan, sedan lyfter vi in den i ert affärssystem eller via API."
    >
      <SnajpSupportDemo />
    </PageShell>
  );
}
