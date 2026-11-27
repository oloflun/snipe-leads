"use client";

import { Badge } from "@astryxdesign/core/Badge";
import { Banner } from "@astryxdesign/core/Banner";
import { Heading } from "@astryxdesign/core/Heading";
import { Layout, LayoutContent, LayoutHeader } from "@astryxdesign/core/Layout";
import { VStack } from "@astryxdesign/core/Stack";
import { Text } from "@astryxdesign/core/Text";
import { Clock } from "lucide-react";
import { Objektikon, type Objekt } from "@/components/crm/app/kit";
import { NotisKlocka } from "@/components/crm/app/Notiser";
import { CrmFel, EJ_AKTIVERAD, LASROLL } from "@/lib/crm/api";
import { useLocale } from "@/lib/i18n";

/**
 * Sidhuvudet (DESIGN-CRM.md § Sidhuvud och vyrad), 64 px: objektets ikonplatta,
 * rubriken i Fraunces och antalet som en neutral etikett. Till höger sidans
 * primära handling (bläck) och eventuella ikonknappar.
 */
export function Sidhuvud({
  objekt,
  rubrik,
  antal,
  atgarder
}: Readonly<{ objekt?: Objekt; rubrik: string; antal?: string | number; atgarder?: React.ReactNode }>) {
  return (
    <div className="flex min-h-16 flex-wrap items-center justify-between gap-x-4 gap-y-2 px-4 py-3 sm:px-6">
      <div className="flex min-w-0 items-center gap-3">
        {objekt ? <Objektikon objekt={objekt} storlek={32} /> : null}
        <Heading level={1} maxLines={1}>
          {rubrik}
        </Heading>
        {antal != null && antal !== "" ? <Badge variant="neutral" label={<span className="tabular-nums">{antal}</span>} /> : null}
      </div>
      <div className="flex items-center gap-2">
        {atgarder}
        {/* Skalets klocka (Notiser.tsx): syns bara när arbetsytan har Leads. */}
        <NotisKlocka />
      </div>
    </div>
  );
}

/**
 * Vyraden, 52 px under en hårlinje: vyerna till vänster (ett SegmentedControl),
 * sök och sortering till höger. Bara val som fungerar mot API:t.
 */
export function Vyrad({ children, hoger }: Readonly<{ children?: React.ReactNode; hoger?: React.ReactNode }>) {
  return (
    <div className="flex min-h-[52px] flex-wrap items-center justify-between gap-x-4 gap-y-2 border-t border-ink/[0.08] px-4 py-2 sm:px-6">
      <div className="flex min-w-0 items-center gap-2">{children}</div>
      {hoger ? <div className="flex w-full items-center gap-2 sm:w-auto">{hoger}</div> : null}
    </div>
  );
}

/**
 * En CRM-sida: sidhuvud, valfri vyrad och innehållet, som rullar under huvudet.
 *
 * `vyrad` (eller det äldre `verktyg`) hamnar i vyraden. `utfyllnad` styr
 * innehållets marginal: `tabell` ger tabellen kant i kant med bladet (cellerna
 * har egen marginal), `sida` ger 24 px runt, som översiktens rutnät, och `tavla`
 * låter innehållet fylla bladets höjd, så att tavlans rullningslist i sidled
 * ligger i bladets nederkant.
 */
export function Sida({
  objekt,
  rubrik,
  antal,
  atgarder,
  vyrad,
  vyradHoger,
  verktyg,
  utfyllnad = "tabell",
  children
}: Readonly<{
  objekt?: Objekt;
  rubrik: string;
  antal?: string | number;
  atgarder?: React.ReactNode;
  vyrad?: React.ReactNode;
  vyradHoger?: React.ReactNode;
  /** Äldre namn på vyradens innehåll. Ritas i vyraden över hela bredden. */
  verktyg?: React.ReactNode;
  utfyllnad?: "tabell" | "sida" | "tavla";
  children: React.ReactNode;
}>) {
  const harVyrad = vyrad != null || vyradHoger != null || verktyg != null;
  return (
    <Layout
      height="fill"
      header={
        <LayoutHeader padding={0}>
          <Sidhuvud objekt={objekt} rubrik={rubrik} antal={antal} atgarder={atgarder} />
          {harVyrad ? (
            verktyg != null && vyrad == null && vyradHoger == null ? (
              <div className="border-t border-ink/[0.08] px-4 pt-2 sm:px-6">{verktyg}</div>
            ) : (
              <Vyrad hoger={vyradHoger}>{vyrad}</Vyrad>
            )
          ) : null}
        </LayoutHeader>
      }
      content={
        <LayoutContent padding={0}>
          <div
            className={
              utfyllnad === "sida"
                ? "px-4 pb-8 pt-2 sm:px-6"
                : utfyllnad === "tavla"
                  ? "flex min-h-full flex-col border-t border-ink/[0.08]"
                  : "border-t border-ink/[0.08]"
            }
          >
            {children}
          </div>
        </LayoutContent>
      }
    />
  );
}

/** Svarade proxyn att arbetsytan inte är kopplad till agenterna än (409 `ej_aktiverad`, SK-157). */
export const arEjAktiverad = (fel: unknown) => fel instanceof CrmFel && fel.status === 409 && fel.kod === EJ_AKTIVERAD;

/**
 * "Din arbetsyta aktiveras" (SK-157): det en ny kund möter i stället för ett
 * tekniskt 409, i varje vy som får svaret `ej_aktiverad`. Neutral, inte
 * larmande: inget är trasigt och kunden behöver inte göra något. `Felruta` visar
 * den av sig själv; en vy som inte använder `Felruta` visar den när `arEjAktiverad(fel)`.
 * Ett 409 utan koden (kopplad kund utan nyckel) är ett driftfel och visas som fel.
 */
export function ArbetsytanAktiveras({ yta }: Readonly<{ yta?: string }>) {
  const { text } = useLocale();
  return (
    <div role="status" className="crm-kallkort flex items-start gap-3 rounded-[16px] p-5">
      <Objektikon ikon={Clock} ton="mineral" storlek={32} />
      <div className="min-w-0">
        <p className="text-[0.9375rem] font-semibold text-ink">{text({ sv: "Din arbetsyta aktiveras", en: "Your workspace is being activated" })}</p>
        <p className="mt-1 max-w-[62ch] text-[0.875rem] leading-relaxed text-ink2">
          {yta
            ? text({ sv: `${yta} är redo när vi kopplat er till agenterna.`, en: `${yta} is ready once we have connected you to the agents.` })
            : text({ sv: "Vyn är redo när vi kopplat er till agenterna.", en: "The view is ready once we have connected you to the agents." })}
        </p>
      </div>
    </div>
  );
}

/** Ett fel från API:t, på läsarens språk, med ett sätt att försöka igen. */
export function Felruta({ fel, igen }: Readonly<{ fel: unknown; igen?: React.ReactNode }>) {
  const { text } = useLocale();
  if (arEjAktiverad(fel)) return <ArbetsytanAktiveras />;
  const beskrivning =
    fel instanceof CrmFel && fel.kod === LASROLL
      ? text({ sv: "Du har läsbehörighet. Du kan följa allt, men inte ändra något.", en: "You have read access. You can follow everything, but not change anything." })
      : fel instanceof CrmFel
        ? text(fel.text)
        : text({ sv: "Något gick fel när sidan hämtade data.", en: "Something went wrong while the page loaded its data." });
  return (
    <Banner
      status="error"
      container="section"
      title={text({ sv: "Det gick inte att hämta", en: "Could not load" })}
      description={beskrivning}
      endContent={igen}
    />
  );
}

/** En etikett med sitt värde, för postens detaljer. Tomt värde visas som streck. */
export function Uppgift({ etikett, children }: Readonly<{ etikett: string; children?: React.ReactNode }>) {
  const tom = children == null || children === "" || children === false;
  return (
    <VStack gap={0.5}>
      <Text type="label" color="secondary">
        {etikett}
      </Text>
      {tom ? <Text color="disabled">-</Text> : <Text wordBreak="break-word">{children}</Text>}
    </VStack>
  );
}
