"use client";

import { Button } from "@astryxdesign/core/Button";
import { Dialog, DialogHeader } from "@astryxdesign/core/Dialog";
import { Layout, LayoutContent, LayoutFooter } from "@astryxdesign/core/Layout";
import { HStack } from "@astryxdesign/core/Stack";
import { Text } from "@astryxdesign/core/Text";
import { Postchip } from "@/components/crm/app/kit";
import { useLocale } from "@/lib/i18n";

/**
 * NYTT MÖNSTER (steg 4.2): bekräftelse av en massåtgärd med listan över vilka
 * poster den berör (LR-057). AlertDialog bär bara en mening; här behöver den som
 * trycker se varje bolag och vart mejlet går innan något skickas eller tas bort.
 *
 * En Dialog med Layout som BolagFormular: rubriken med antalet, en rullbar lista
 * med postchip och mottagare, ett valfritt tillägg (som kryssrutan för
 * provkörningens bolag), förklaringen, och Avbryt bredvid handlingen. Dialogen
 * stängs inte medan åtgärden pågår. Återanvänd den för varje "gör det här med N
 * poster" som behöver visa posterna först.
 */
export function Bekraftelse({
  oppen,
  titel,
  poster,
  overhoppade = 0,
  tillagg,
  forklaring,
  handling,
  farlig = false,
  upptagen,
  bekrafta,
  stang
}: Readonly<{
  oppen: boolean;
  titel: string;
  poster: { id: string; namn: string; under?: string | null }[];
  /** Markerade som inte berörs (saknar väntande utkast med mera). */
  overhoppade?: number;
  tillagg?: React.ReactNode;
  forklaring: string;
  handling: string;
  farlig?: boolean;
  upptagen: boolean;
  bekrafta: () => void;
  stang: () => void;
}>) {
  const { text } = useLocale();
  return (
    <Dialog isOpen={oppen} onOpenChange={(o) => !o && !upptagen && stang()} purpose="form" width={600}>
      <Layout
        header={<DialogHeader title={titel} onOpenChange={(o) => !o && !upptagen && stang()} />}
        content={
          <LayoutContent>
            <div className="flex flex-col gap-4">
              {poster.length > 0 ? (
                <ul className="crm-kallkort flex max-h-[18rem] flex-col overflow-y-auto rounded-[16px] px-3 py-1.5" aria-label={titel}>
                  {poster.map((p) => (
                    <li key={p.id} className="flex min-w-0 flex-wrap items-center justify-between gap-x-3 gap-y-0.5 border-b border-ink/[0.07] py-2 last:border-b-0">
                      <Postchip namn={p.namn} storlek="sm" vikt="lugn" />
                      {p.under ? <span className="min-w-0 truncate text-[0.8125rem] text-ink-muted">{p.under}</span> : null}
                    </li>
                  ))}
                </ul>
              ) : null}
              {overhoppade > 0 ? (
                <Text color="secondary" type="supporting">
                  {overhoppade === 1
                    ? text({ sv: "1 av de markerade berörs inte och hoppas över.", en: "1 of the selected is not affected and is skipped." })
                    : text({ sv: `${overhoppade} av de markerade berörs inte och hoppas över.`, en: `${overhoppade} of the selected are not affected and are skipped.` })}
                </Text>
              ) : null}
              {tillagg}
              <Text color="secondary">{forklaring}</Text>
            </div>
          </LayoutContent>
        }
        footer={
          <LayoutFooter>
            <HStack justify="end" gap={2}>
              <Button label={text({ sv: "Avbryt", en: "Cancel" })} variant="ghost" onClick={stang} isDisabled={upptagen} />
              <Button
                label={handling}
                variant={farlig ? "secondary" : "primary"}
                className={farlig ? "crm-farlig" : undefined}
                isLoading={upptagen}
                isDisabled={poster.length === 0}
                onClick={bekrafta}
              />
            </HStack>
          </LayoutFooter>
        }
      />
    </Dialog>
  );
}
