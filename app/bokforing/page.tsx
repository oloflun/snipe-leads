import { redirect } from "next/navigation";

/**
 * Gamla produktadressen. Bokföringsagenten blev Kvittohanteraren 2026-09-16,
 * och den är sedan 2026-10-17 ett vilande tillägg till Support utan egen
 * säljsida — länkar och bokmärken hit landar på Supports sida (se /kvitton).
 */
export default function Page() {
  redirect("/support");
}
