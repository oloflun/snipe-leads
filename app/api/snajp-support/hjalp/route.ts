import { NextRequest } from "next/server";
import {
  ejInloggadSvar,
  hjalpAvSvar,
  hjalpChattkropp,
  hjalpIdentitet,
  medSigneratJobb,
  ogiltigtSvar,
  tillHjalpen,
  tolka
} from "@/lib/snajp/hjalp";
import { getWorkspaceContext } from "@/lib/workspace";

export const runtime = "nodejs";
// Samma budget som de andra chattvägarna: backenden kan behöva vakna.
export const maxDuration = 60;

/**
 * Hjälprutans fråga till Snajps egen supportagent
 * (docs/PLAN-HJALPRUTAN-2026-11-25.md, del 2).
 *
 * Inloggad (getWorkspaceContext), men INTE under kundens nyckel: frågan går
 * till hjälpens egen kund i systemet (`SNAJP_KEY_SNAJP_HJALP`), som svarar ur
 * Snajps kunskapsbas om produkten. Kroppen skrivs om på servern
 * (lib/snajp/hjalp.ts:hjalpChattkropp): ur klienten tas bara texten och en
 * bild; avsändaren blir den inloggades id på kunddomänen och is_test är
 * falskt. Svaret är ett jobb som rutan pollar på ./jobb/[jobId].
 *
 * Jobb-id:t går aldrig naket till klienten: alla kunders frågor ligger under
 * samma hjälpkund, så backendens tenantkontroll skiljer dem inte åt. Id:t
 * signeras med den inloggades användare och arbetsyta
 * (lib/snajp/hjalp.ts:medSigneratJobb), och pollningen godtar bara en
 * signatur som hör till den som frågar. Utan AUTH_SECRET skickas ingen fråga
 * alls: ett jobb som inte går att signera skulle inte gå att läsa.
 */
export async function POST(request: NextRequest) {
  const context = await getWorkspaceContext();
  if (!context) return ejInloggadSvar();
  const hemlighet = process.env.AUTH_SECRET;
  if (!hemlighet) return hjalpAvSvar();
  const identitet = await hjalpIdentitet(context);
  const kropp = hjalpChattkropp(tolka(await request.text()), identitet);
  if (!kropp) return ogiltigtSvar();
  const svar = await tillHjalpen(
    process.env.SNAJP_KEY_SNAJP_HJALP,
    "/api/chat",
    { method: "POST", body: JSON.stringify(kropp) },
    identitet.userId
  );
  return medSigneratJobb(svar, identitet, hemlighet);
}
