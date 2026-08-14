// Vilka organisationer som får se pilot-arbetsytan (/kundtjanst).
//
// Pilotens inkorg innehåller ETT annat bolags riktiga kundärenden. Tidigare
// räckte det att vara inloggad för att komma åt den, vilket blev en läcka i
// samma stund som vem som helst kunde registrera sig.
//
// Fail-closed: saknas SNAJP_PILOT_WORKSPACE_IDS släpps ingen in. Att öppna för
// alla när konfigurationen saknas var precis den bugg som fanns.

const IDS = (process.env.SNAJP_PILOT_WORKSPACE_IDS ?? "")
  .split(",")
  .map((id) => id.trim())
  .filter(Boolean);

export function isPilotWorkspace(workspaceId: string | null | undefined): boolean {
  return Boolean(workspaceId) && IDS.includes(workspaceId as string);
}

/** För felmeddelanden och admin-diagnostik — aldrig för åtkomstbeslut. */
export function pilotWorkspaceCount(): number {
  return IDS.length;
}
