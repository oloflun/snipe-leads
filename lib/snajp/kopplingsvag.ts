/**
 * Vilken väg onboardingen tar för att ge arbetsytan sin backend-kund.
 *
 * En arbetsyta som redan har en kund behåller den, vad testrutan än säger:
 * `link_test_tenant` och `link_workspace_tenant` kopplar bara en arbetsyta utan
 * slug. Produktion 2026-11-23 (kund-ad046232): en redan kopplad testarbetsyta
 * gick testvägen, kopplingen nekades, och allt som hängde på den nya nyckeln
 * hoppades över, alltså webbplatsskanningen, målgruppen och erbjudandena.
 *
 * Egen fil utan `server-only`, så att valet går att testa med node --test.
 */
export type Kopplingsvag = "befintlig" | "testtenant" | "kundtenant";

export function kopplingsvag(slug: string | null | undefined, testkund: boolean): Kopplingsvag {
  if (slug) return "befintlig";
  return testkund ? "testtenant" : "kundtenant";
}
