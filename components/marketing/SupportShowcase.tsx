"use client";

import { useLocale } from "@/lib/i18n";
import type { Localized } from "@/lib/i18n";
import { InboxTriage } from "@/components/snajp/InboxTriage";
import { SupportChat } from "@/components/snajp/SupportChat";

const copy = {
  chat: { sv: "Chatt", en: "Chat" },
  inbox: { sv: "Inkorg", en: "Inbox" },
  wake: {
    sv: "Backendet vilar efter en stunds tystnad. Första svaret kan dröja en minut.",
    en: "The backend sleeps after a quiet spell. The first reply can take a minute."
  }
} satisfies Record<string, Localized>;

/**
 * `tenant` väljs av servern (ProductPage): "snajp" när vår egen supportnyckel
 * finns i miljön, annars ingen — då svarar demot ur Nordlys-butikens KB som
 * förut. Med snajp-tenanten svarar chatten i stället ur Snajps egen
 * kunskapsbas (priser, dataskydd, uppstart), vilket är vad en besökare på
 * produktsidan faktiskt frågar om.
 */
export function SupportShowcase({ tenant }: Readonly<{ tenant?: string }> = {}) {
  const { text } = useLocale();

  return (
    <div className="space-y-12">
      <div>
        <h3 className="text-[1.125rem] font-semibold tracking-[-0.01em]">{text(copy.chat)}</h3>
        <div className="mt-4">
          <SupportChat tenant={tenant} />
        </div>
        <p className="mt-3 text-[0.8125rem] text-ink/45">{text(copy.wake)}</p>
      </div>

      <div>
        <h3 className="text-[1.125rem] font-semibold tracking-[-0.01em]">{text(copy.inbox)}</h3>
        <div className="mt-4">
          <InboxTriage />
        </div>
      </div>
    </div>
  );
}
