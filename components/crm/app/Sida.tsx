"use client";

import { Banner } from "@astryxdesign/core/Banner";
import { Heading } from "@astryxdesign/core/Heading";
import { Layout, LayoutContent, LayoutHeader } from "@astryxdesign/core/Layout";
import { HStack, VStack } from "@astryxdesign/core/Stack";
import { Text } from "@astryxdesign/core/Text";
import { CrmFel } from "@/lib/crm/api";
import { useLocale } from "@/lib/i18n";

/**
 * En CRM-sida: rubrik med antal till vänster, sidans åtgärder till höger, och
 * innehållet under en hårlinje. Samma huvud på varje vy, så att blicken hittar
 * rubrik, antal och åtgärd på samma ställe.
 */
export function Sida({
  rubrik,
  antal,
  atgarder,
  verktyg,
  children
}: Readonly<{
  rubrik: string;
  antal?: string;
  atgarder?: React.ReactNode;
  verktyg?: React.ReactNode;
  children: React.ReactNode;
}>) {
  return (
    <Layout
      defaultHasDividers
      header={
        <LayoutHeader padding={4} paddingBlockEnd={verktyg ? 0 : 4}>
          <VStack gap={3}>
            <HStack justify="between" align="center" gap={4} wrap="wrap">
              <HStack align="end" gap={3} wrap="wrap">
                <Heading level={1}>{rubrik}</Heading>
                {antal ? (
                  <Text color="secondary" hasTabularNumbers>
                    {antal}
                  </Text>
                ) : null}
              </HStack>
              {atgarder ? (
                <HStack gap={2} align="center">
                  {atgarder}
                </HStack>
              ) : null}
            </HStack>
            {verktyg}
          </VStack>
        </LayoutHeader>
      }
      content={
        <LayoutContent padding={0}>
          {/* Tabellens celler har 8 px inre marginal. Med 8 px till här står
              första kolumnens text i linje med sidans rubrik, på 16 px. */}
          <div className="px-2">{children}</div>
        </LayoutContent>
      }
    />
  );
}

/** Ett fel från API:t, på läsarens språk, med ett sätt att försöka igen. */
export function Felruta({ fel, igen }: Readonly<{ fel: unknown; igen?: React.ReactNode }>) {
  const { text } = useLocale();
  const beskrivning =
    fel instanceof CrmFel
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
