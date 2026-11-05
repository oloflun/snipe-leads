import { KONTAKT_MEJL } from "@/components/marketing/copy";
import { llmsText } from "@/lib/llms";
import { getCurrentTenant } from "@/lib/tenants/server";

/**
 * /llms.txt, se lib/llms.ts.
 *
 * Inte på kundens domän: där är vi kundens supportchatt, och en fil som
 * beskriver Snajp vore fel bolag på fel sajt (TENANTS.md).
 *
 * Inte grindad på produktion som sitemapen. Filen räknar inte upp miljöns
 * adresser, bara de kanoniska på www.snajp.se, och utanför produktion säger
 * robots.txt redan nej till varje crawler.
 */
const TEXT = llmsText(KONTAKT_MEJL);

export async function GET() {
  if (await getCurrentTenant()) return new Response("Not found", { status: 404 });
  return new Response(TEXT, {
    headers: { "Content-Type": "text/plain; charset=utf-8", "Cache-Control": "public, max-age=3600" }
  });
}
