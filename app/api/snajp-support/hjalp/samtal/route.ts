import { ejInloggadSvar, hjalpIdentitet, hjalpSamtalskropp, tillHjalpen } from "@/lib/snajp/hjalp";
import { getWorkspaceContext } from "@/lib/workspace";

export const runtime = "nodejs";
export const maxDuration = 60;

/**
 * Hjälpsamtalet läst tillbaka från servern, så att det finns kvar efter en
 * omladdning och i en ny flik (planen del 1). Klientens kropp används inte:
 * samtalet är alltid den inloggades eget, under hennes adress på kunddomänen.
 * Backenden (POST /api/hjalp/samtal) godtar bara den domänen.
 */
export async function POST() {
  const context = await getWorkspaceContext();
  if (!context) return ejInloggadSvar();
  const identitet = await hjalpIdentitet(context);
  return tillHjalpen(
    process.env.SNAJP_KEY_SNAJP_HJALP,
    "/api/hjalp/samtal",
    { method: "POST", body: JSON.stringify(hjalpSamtalskropp(identitet)) },
    identitet.userId
  );
}
