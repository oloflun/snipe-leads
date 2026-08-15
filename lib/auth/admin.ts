import "server-only";

import { createClient } from "@/lib/supabase/server";
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

export async function isPlatformAdmin(userId: string): Promise<boolean> {
  const supabase = await createClient();
  const { data, error } = await supabase
    .from("platform_admins")
    .select("user_id")
    .eq("user_id", userId)
    .maybeSingle();

  if (error) {
    // Fail-closed. Ett uppslag som inte gick att göra betyder INTE admin —
    // motsatt val hade gjort ett databasavbrott till en behörighetshöjning.
    console.error("isPlatformAdmin:", error.message);
    return false;
  }

  return Boolean(data);
}

export type PlatformAdmin = {
  userId: string;
  email: string | undefined;
};

/**
 * Returnerar admin-identiteten, eller null. Anroparen avgör vad ett null
 * betyder — `/admin/layout.tsx` svarar 404, inte 403, eftersom ett 403 bekräftar
 * att ytan finns.
 */
export async function getPlatformAdmin(): Promise<PlatformAdmin | null> {
  const context = await getWorkspaceContext();
  if (!context) {
    return null;
  }
  if (!(await isPlatformAdmin(context.user.id))) {
    return null;
  }
  return { userId: context.user.id, email: context.user.email };
}
