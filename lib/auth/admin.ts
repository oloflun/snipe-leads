import "server-only";

import { cache } from "react";
import { sqlAsUser } from "@/lib/db";
import { harAktivTvafaktor } from "@/lib/auth/tvafaktor";
import { TVAFAKTOR_KRAVS_FOR_PLATTFORMSADMIN } from "@/lib/auth/tvafaktor-krypto";
import { sessionenUppfyllerTvafaktor } from "@/lib/auth/tvafaktor-session";
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
 * betyder. `/admin/layout.tsx` frågar först `auth()` (ingen session →
 * /login?next=/admin) och skickar sedan ett null vidare: en admin som stoppas
 * av tvåfaktorn till /settings/tvafaktor, en inloggad icke-admin till
 * /dashboard (ändrat från 404 2026-11-24, INV-AUTH-002). `/api/admin` svarar
 * fortfarande 404, eftersom ett API inte omdirigeras.
 */
export const getPlatformAdmin = cache(async function getPlatformAdmin(): Promise<PlatformAdmin | null> {
  const admin = await getPlatformAdminUtanTvafaktorkrav();
  if (!admin) {
    return null;
  }
  // Tvånget (av som standard, Antons beslut): en admin utan aktiv tvåfaktor
  // har ingen adminrätt alls, i layouten, API-proxyn och varje action, eftersom
  // alla frågar den här funktionen. Inrullningen nås ändå, se nedan.
  if (await saknarKravdTvafaktor(admin.userId)) {
    return null;
  }
  // Oberoende av tvånget: har kontot tvåfaktor på ska SESSIONEN ha gått
  // igenom den. Annars behåller en session från före aktiveringen (eller en
  // stulen sådan) adminrätten utan kod (Codex-granskningen 2026-11-19).
  if (!(await sessionenUppfyllerTvafaktor(admin.userId, admin.tvafaktorISessionen, harAktivTvafaktor))) {
    return null;
  }
  return { userId: admin.userId, email: admin.email };
});

/**
 * Plattformsadmin enligt `platform_admins`, oavsett tvåfaktorkravet. Bara för
 * inrullningssidan (`/settings/tvafaktor`), som måste nås av en admin som
 * ännu inte har tvåfaktor när tvånget är påslaget. Ger ingen annan adminrätt.
 */
export const getPlatformAdminUtanTvafaktorkrav = cache(
  async function getPlatformAdminUtanTvafaktorkrav(): Promise<(PlatformAdmin & { tvafaktorISessionen: boolean }) | null> {
    const context = await getWorkspaceContext();
    if (!context) {
      return null;
    }
    // Samma uppslag som isPlatformAdmin, läst i arbetsytans fråga (samma
    // användare, samma RLS) i stället för i en egen transaktion.
    if (!context.isPlatformAdmin) {
      return null;
    }
    return {
      userId: context.user.id,
      email: context.user.email,
      tvafaktorISessionen: context.user.tvafaktor === true
    };
  }
);

/**
 * Sant bara när tvånget är påslaget OCH kontot saknar aktiv tvåfaktor. Med
 * tvånget av (standard) ställs ingen fråga alls. Ett uppslagsfel räknas som
 * "saknas" (fail closed), som isPlatformAdmin.
 */
export async function saknarKravdTvafaktor(userId: string): Promise<boolean> {
  if (!TVAFAKTOR_KRAVS_FOR_PLATTFORMSADMIN) {
    return false;
  }
  try {
    return !(await harAktivTvafaktor(userId));
  } catch (error) {
    console.error("saknarKravdTvafaktor:", (error as Error).message);
    return true;
  }
}
