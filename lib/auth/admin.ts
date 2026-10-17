import "server-only";

import { cache } from "react";
import { sqlAsUser } from "@/lib/db";
import { getWorkspaceContext } from "@/lib/workspace";

/**
 * Plattformsadmin — läsning över ALLA kunder.
 *
 * Skiljd från `profiles.role`, som är workspace-scopad och säger vad någon får
 * göra inuti sin egen arbetsyta. Att blanda dem hade betytt att den som blir
 * owner av sitt eget workspace också blir admin över alla andras.
 *
 * `import "server-only"` är inte kosmetik: den gör det till ett byggfel att
 * importera modulen i en klientkomponent. Ett adminvillkor som råkar hamna i
 * klientbundeln är samma sak som inget adminvillkor — det syns i devtools och
 * går att sätta till true.
 */

/**
 * Per request och användare (React `cache`): layoutens onboardinggrind,
 * `getPlatformAdmin` och vyväxeln ställer annars samma fråga var för sig vid
 * varje sidbyte.
 */
export const isPlatformAdmin = cache(async function isPlatformAdmin(userId: string): Promise<boolean> {
  try {
    const rows = await sqlAsUser<{ user_id: string }>(
      userId,
      "select user_id from public.platform_admins where user_id = $1",
      [userId]
    );
    return rows.length > 0;
  } catch (error) {
    // Fail-closed. Ett uppslag som inte gick att göra betyder INTE admin —
    // motsatt val hade gjort ett databasavbrott till en behörighetshöjning.
    console.error("isPlatformAdmin:", (error as Error).message);
    return false;
  }
});

export type PlatformAdmin = {
  userId: string;
  email: string | null;
};

/**
 * Returnerar admin-identiteten, eller null. Anroparen avgör vad ett null
 * betyder — `/admin/layout.tsx` svarar 404, inte 403, eftersom ett 403 bekräftar
 * att ytan finns.
 */
export const getPlatformAdmin = cache(async function getPlatformAdmin(): Promise<PlatformAdmin | null> {
  const context = await getWorkspaceContext();
  if (!context) {
    return null;
  }
  // Samma uppslag som isPlatformAdmin, läst i arbetsytans fråga (samma
  // användare, samma RLS) i stället för i en egen transaktion.
  if (!context.isPlatformAdmin) {
    return null;
  }
  return { userId: context.user.id, email: context.user.email };
});
