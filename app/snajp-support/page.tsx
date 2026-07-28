import { PageShell } from "@/components/AppShell";
import { SnajpSupportDemo } from "@/components/snajp/SnajpSupportDemo";

export const metadata = {
  title: "Snajp-Support — AI-kundtjänst som sorterar och svarar"
};

export default function Page() {
  return (
    <PageShell
      kicker="Snajp-Support"
      title="Förstahandssupporten som aldrig gissar."
      description="En AI-agent som läser inkommande kundmail, sorterar dem i rätt fack och skriver färdiga svar grundade i er egen kunskapsbas. Ni granskar och godkänner — agenten skickar aldrig något på egen hand. Demon nedan visar ett bolag som säljer hjärtstartare; ladda ett scenario och se hela flödet."
    >
      <SnajpSupportDemo />
    </PageShell>
  );
}
