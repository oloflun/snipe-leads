import "server-only";

import { SNAJP_SUPPORT_URL } from "@/app/api/snajp-support/_lib";

/**
 * Startar skanningen av kundens egen webbplats, åt kunden, när onboardingen
 * sparas (Antons beställning 2026-11-18).
 *
 * Backenden (POST /api/kb/skanna med `spara`) läser sajten och sparar
 * artikelutkast som FÖRSLAG. Kunskapsbasen rörs aldrig: ett förslag blir en ny
 * artikel först när kunden lägger till det, och en rubrik som redan finns hos
 * kunden föreslås inte (app/api/kb.py, `nya_forslag`). Förloppet och utfallet
 * sparas (migration 121) och visas i Översikt › Kom igång och Kunskapsbas.
 *
 * Svaret väntas in bara tills backenden tagit emot jobbet (202), aldrig tills
 * skanningen är klar. Det fäller aldrig onboardingen: en skanning som inte
 * kunde starta sparas ändå med skälet, så kunden ser varför.
 *
 * Bara här. Inloggningsvägen (fyllStandardinstallningarEnGang) startar aldrig
 * en skanning: en ny hämtning av sajten är tillägget Synkad kunskapsbas, inte
 * uppsättningen (docs/pilot_onboarding.md).
 */
export async function startaWebbplatsskanning(apiKey: string, webbplats: string): Promise<void> {
  if (!webbplats.trim()) return;
  try {
    const svar = await fetch(`${SNAJP_SUPPORT_URL}/api/kb/skanna`, {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-API-Key": apiKey },
      body: JSON.stringify({ webbplats, spara: true, startad_av: "onboarding" }),
      cache: "no-store",
      signal: AbortSignal.timeout(15_000)
    });
    if (!svar.ok && svar.status !== 422) {
      // 422 är en adress som inte går att skanna, och den har backenden redan
      // sparat med skälet. Allt annat loggas.
      console.error(`[onboarding] webbplatsskanningen startade inte: ${svar.status}`);
    }
  } catch (error) {
    console.error("[onboarding] webbplatsskanningen startade inte:", error);
  }
}
