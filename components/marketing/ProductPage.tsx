import { BokforingDemo } from "@/components/bookkeeping/BokforingDemo";
import { EmailStudioEditor } from "@/components/email/EmailStudioEditor";
import { LandingPhoto } from "@/components/marketing/LandingPhoto";
import { SupportShowcase } from "@/components/marketing/SupportShowcase";
import { loadPublicEmailStudioData } from "@/lib/data/emails";
import type { ProductKey } from "@/lib/routes";

/**
 * One shell for /, /leads, /support and /bokforing. Only the initially selected
 * product differs, so all four URLs are linkable and crawlable while the
 * in-page switch moves between them without a navigation.
 *
 * Example data only: a public page must never reach for a session or a database,
 * and the fine print under the demo says as much. Bokföringens demo är samma
 * `BokforingDemo` som /demo/bokforing visar — handräknade konstanter, ingen
 * modell, ingen backend.
 */
export function ProductPage({ initial }: Readonly<{ initial: ProductKey }>) {
  const emailData = loadPublicEmailStudioData();

  // Publika chatten svarar ur Snajps EGEN kunskapsbas (priser, dataskydd,
  // uppstart) när vår supportnyckel finns — det är de frågorna en besökare
  // ställer. Saknas nyckeln faller demot tillbaka på Nordlys-butiken som
  // förut, i stället för att brytas av en miljö som inte hunnit få nyckeln.
  const supportTenant = process.env.SNAJP_KEY_SNAJP ? "snajp" : undefined;

  return (
    <LandingPhoto
      initial={initial}
      leadsDemo={<EmailStudioEditor data={emailData} compact />}
      supportDemo={<SupportShowcase tenant={supportTenant} />}
      bookkeepingDemo={<BokforingDemo />}
    />
  );
}
