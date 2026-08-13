import { PageShell } from "@/components/AppShell";
import { SnajpSupportDemo } from "@/components/snajp/SnajpSupportDemo";

// Kundens egen arbetsyta — samma gränssnitt som demon, men mot den inloggade
// organisationens tenant. Åtkomst gated i middleware.ts (utloggade skickas till
// den publika demon på /demo/snajp) och i app/api/snajp-support-proxyn, som
// kräver session och kör mot organisationens egen API-nyckel.

export const metadata = {
  title: "Snajp-Support — er AI-kundtjänst"
};

export default function Page() {
  return (
    <PageShell
      kicker="Snajp-Support"
      title="Förstahandssupporten som aldrig gissar."
      description="En AI-agent som läser inkommande kundmail, sorterar dem i rätt fack och skriver färdiga svar grundade i er egen kunskapsbas. Ni granskar och godkänner — agenten skickar aldrig något på egen hand."
    >
      <SnajpSupportDemo apiBase="/api/snajp-support" />
    </PageShell>
  );
}
