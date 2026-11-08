import { EmailStudioEditor } from "@/components/email/EmailStudioEditor";
import { LandingPhoto } from "@/components/marketing/LandingPhoto";
import { SupportShowcase } from "@/components/marketing/SupportShowcase";
import { loadPublicEmailStudioData } from "@/lib/data/emails";
import type { ProductKey } from "@/lib/routes";

/**
 * One shell for /, /leads and /support. Only the initially selected
 * product differs, so all three URLs are linkable and crawlable while the
 * in-page switch moves between them without a navigation. /kvitton leder till
 * /support sedan 2026-10-17 (Kvittohanteraren är ett vilande tillägg).
 *
 * Example data only: a public page must never reach for a session or a database,
 * and the fine print under the demo says as much.
 */
/** `hem`: startsidan `/`, en egen sida med båda agenterna (LandingPhoto, Startsida.tsx). */
export function ProductPage({ initial, hem = false }: Readonly<{ initial: ProductKey; hem?: boolean }>) {
  const emailData = loadPublicEmailStudioData();

  // Publika chatten svarar ur Snajps EGEN kunskapsbas (priser, dataskydd,
  // uppstart) när vår supportnyckel finns — det är de frågorna en besökare
  // ställer. Saknas nyckeln faller demot tillbaka på Nordlys-butiken som
  // förut, i stället för att brytas av en miljö som inte hunnit få nyckeln.
  const supportTenant = process.env.SNAJP_KEY_SNAJP ? "snajp" : undefined;

  return (
    <LandingPhoto
      initial={initial}
      hem={hem}
      leadsDemo={<EmailStudioEditor data={emailData} compact />}
      supportDemo={<SupportShowcase tenant={supportTenant} />}
    />
  );
}
