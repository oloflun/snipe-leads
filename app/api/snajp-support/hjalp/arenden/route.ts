import { NextRequest } from "next/server";
import { ejInloggadSvar, hjalpIdentitet, ogiltigtSvar, rapportkropp, tillHjalpen, tolka } from "@/lib/snajp/hjalp";
import { getWorkspaceContext } from "@/lib/workspace";

export const runtime = "nodejs";
export const maxDuration = 60;

/**
 * Felrapporterna (planen del 5): den inloggades egna ärenden, och en ny rapport.
 *
 * Läsningen frågar alltid efter den inloggades egna rapporter; ingen parameter
 * ur klienten avgör vems. Rapporten byggs i lib/snajp/hjalp.ts:rapportkropp:
 * rapportör, arbetsyta, kund, vy, roll och adminbesök kommer ur sessionen, ur
 * klienten bara sidans sökväg, de tre fälten och en bild.
 *
 * Läsrollen får rapportera: en felrapport är ingen skrivning i kundens data,
 * och den som bara får läsa ska ändå kunna säga att något är fel.
 */
export async function GET() {
  const context = await getWorkspaceContext();
  if (!context) return ejInloggadSvar();
  const identitet = await hjalpIdentitet(context);
  return tillHjalpen(
    process.env.SNAJP_KEY_SNAJP_HJALP,
    `/api/plattformsarenden?rapportor=${encodeURIComponent(identitet.userId)}`,
    { method: "GET" },
    identitet.userId
  );
}

export async function POST(request: NextRequest) {
  const context = await getWorkspaceContext();
  if (!context) return ejInloggadSvar();
  const identitet = await hjalpIdentitet(context);
  const kropp = rapportkropp(tolka(await request.text()), identitet);
  if (!kropp) return ogiltigtSvar();
  return tillHjalpen(
    process.env.SNAJP_KEY_SNAJP_HJALP,
    "/api/plattformsarenden",
    { method: "POST", body: JSON.stringify(kropp) },
    identitet.userId
  );
}
