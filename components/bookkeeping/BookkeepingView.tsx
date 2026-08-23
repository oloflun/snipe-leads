import { PageShell } from "@/components/AppShell";
import { BokforingPanel } from "@/components/bookkeeping/BokforingPanel";

/**
 * Bokföringsvyn. Serverskal, klientpanel — samma delning som resten av
 * arbetsytan.
 *
 * Grinden sitter INTE här utan i `WorkspaceSection`, som avgör på servern om
 * den som frågar är plattformsadmin. En kontroll i den här komponenten hade
 * körts efter att routen redan bestämt sig, alltså för sent för att svara 404.
 *
 * App-familjen enligt DESIGN.md: dense rows, fast typskala, ingen hero, inga
 * reveals, ingen bildyta.
 */
export function BookkeepingView() {
  return (
    <PageShell
      kicker="Bokföring"
      title="Kvitton, kontering och period"
      description="Ladda upp ett kvitto eller en faktura. Agenten läser av det och föreslår kontering — den bokför ingenting själv."
    >
      <BokforingPanel />
    </PageShell>
  );
}
