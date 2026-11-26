"use client";

import { Layout, LayoutContent, LayoutHeader } from "@astryxdesign/core/Layout";
import { Skeleton } from "@astryxdesign/core/Skeleton";
import { Tabellskelett } from "@/components/crm/app/kit";
import { useLocale } from "@/lib/i18n";

/**
 * Medan en CRM-vy laddas: sidhuvudets och tabellens form i skelett, inuti
 * skalet, så att navigeringen står still och bladet inte blinkar tomt.
 */
export default function CrmLaddar() {
  const { text } = useLocale();
  return (
    <Layout
      height="fill"
      header={
        <LayoutHeader padding={0}>
          <div className="flex min-h-16 items-center gap-3 px-4 py-3 sm:px-6" aria-hidden>
            <Skeleton width={32} height={32} radius={3} />
            <Skeleton width={160} height={22} radius="rounded" />
          </div>
          <div className="flex min-h-[52px] items-center gap-2 border-t border-ink/[0.08] px-4 py-2 sm:px-6" aria-hidden>
            <Skeleton width={240} height={28} radius="rounded" />
          </div>
        </LayoutHeader>
      }
      content={
        <LayoutContent padding={0}>
          <div className="border-t border-ink/[0.08]">
            <Tabellskelett rader={8} kolumner={5} markering={false} label={text({ sv: "Hämtar vyn", en: "Loading the view" })} />
          </div>
        </LayoutContent>
      }
    />
  );
}
