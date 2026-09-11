"use server";

import { revalidatePath } from "next/cache";

import { isAddonKey, type AddonKey } from "@/lib/addons";
import { getPlatformAdmin } from "@/lib/auth/admin";
import { sqlAsUser } from "@/lib/db";

/**
 * Tilläggen per kund — plattformsadminens skrivyta.
 *
 * ## Varför inte kunden själv
 *
 * Ett tillägg är inte ett paketval, det är ett uppsättningsarbete hos oss:
 * en IMAP-koppling, en verifierad domän, en egen kvot. En kryssruta i
 * kundens egen vy hade tänt en yta som inte kan leverera. Se migration 063
 * och lib/addons.ts.
 *
 * ## Grinden står i VARJE funktion
 *
 * Samma regel som agentinstruktioner.ts: en server action är en
 * POST-endpoint med ett genererat id, och att den bara anropas från en
 * skyddad sida är ett antagande om klienten — och klienten är inte vår.
 * Databasfunktionerna kontrollerar dessutom `platform_admins` själva, så
 * grinden finns i två lager som inte litar på varandra.
 *
 * ## Varför RPC och inte en UPDATE
 *
 * `workspaces` är läsbar men inte skrivbar under RLS, och adminen läser
 * dessutom en ANNAN arbetsyta än sin egen. Båda korsningarna sker i
 * security definer-funktioner som grindar själva — se migration 063.
 */

export type Tillaggslage = { addons?: AddonKey[]; error?: string };
export type Tillaggsbyte = { success: boolean; addons?: AddonKey[]; error?: string };

/** Svenskt besked för ett fel som annars är en rå Postgres-mening. */
function felText(error: unknown): string {
  const text = (error as Error)?.message ?? "";
  if (text.includes("arbetsytan finns inte")) {
    // Samma svar som funktionen ger på nekad behörighet, med flit: ett
    // särskilt behörighetsfel bekräftar att arbetsytan finns.
    return "Kunden har ingen arbetsyta kopplad till sig, eller så saknas behörighet.";
  }
  if (text.includes("okänt tillägg")) {
    return "Ett av tilläggen finns inte i databasens lista. Katalogen och check-villkoret har glidit isär — se lib/addons.ts.";
  }
  return text || "Tilläggen kunde inte sparas.";
}

export async function hamtaTillagg(tenantId: string): Promise<Tillaggslage> {
  const admin = await getPlatformAdmin();
  if (!admin) {
    return { error: "Bara plattformsadmin kan se tillägg." };
  }

  try {
    const rader = await sqlAsUser<{ admin_workspace_addons: string[] }>(
      admin.userId,
      "select public.admin_workspace_addons($1::uuid)",
      [tenantId]
    );
    // `filter(isAddonKey)` och inte en rak cast: ett värde som finns i
    // databasen men inte i katalogen ska försvinna ur vyn, inte krascha
    // renderingen av de sex som är giltiga.
    return { addons: (rader[0]?.admin_workspace_addons ?? []).filter(isAddonKey) };
  } catch (error) {
    return { error: felText(error) };
  }
}

export async function sattTillagg(
  tenantId: string,
  addons: string[]
): Promise<Tillaggsbyte> {
  const admin = await getPlatformAdmin();
  if (!admin) {
    return { success: false, error: "Bara plattformsadmin kan ändra tillägg." };
  }

  // Filtreras HÄR också, inte bara i databasen. Check-villkoret är domaren,
  // men ett okänt värde som aldrig lämnar Next-appen ger ett begripligt fel
  // i stället för ett check-brott — och listan som skickas är då alltid en
  // delmängd av katalogen användaren faktiskt såg.
  const giltiga = addons.filter(isAddonKey);
  const okanda = addons.filter((nyckel) => !isAddonKey(nyckel));
  if (okanda.length) {
    return { success: false, error: `Okänt tillägg: ${okanda.join(", ")}.` };
  }

  let rader: { set_workspace_addons: string[] }[];
  try {
    rader = await sqlAsUser<{ set_workspace_addons: string[] }>(
      admin.userId,
      "select public.set_workspace_addons($1::uuid, $2::text[])",
      [tenantId, giltiga]
    );
  } catch (error) {
    return { success: false, error: felText(error) };
  }

  // Läses tillbaka ur SVARET, inte ur `giltiga`. Funktionen returnerar det
  // som faktiskt står i kolumnen — samma regel som bytPlan: en vy som ritar
  // det den skickade in kan visa ett tillägg kunden inte har.
  const skrivna = (rader[0]?.set_workspace_addons ?? []).filter(isAddonKey);

  // Menyn och vyerna grindas på samma kolumn, renderade på servern
  // (WorkspaceSection). Utan det här dyker Leadslistor upp först när någon
  // råkar ladda om sidan.
  revalidatePath("/", "layout");

  return { success: true, addons: skrivna };
}
