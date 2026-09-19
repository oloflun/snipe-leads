import { notFound } from "next/navigation";
import type { Metadata } from "next";
import { EmbedYta } from "@/components/snajp/EmbedYta";
import { getTenantByPublicKey, paletteToCss } from "@/lib/tenants";

/**
 * Widgetens iframe-sida: /embed/<publik nyckel>.
 *
 * Adresseras med den PUBLIKA nyckeln, aldrig sluggen — nyckeln står redan i
 * kundens HTML och är slumpad så att /embed inte blir en katalog av gissade
 * kundnamn. Vilka domäner som får rama in sidan bestäms av CSP
 * frame-ancestors, som proxy.ts sätter per nyckel (lib/tenants/index.ts,
 * frameAncestors). Innehållet är detsamma som kundens publika /chat-sida —
 * ingen inloggning, ingen kunddata, bara chatten.
 */

type Props = { params: Promise<{ nyckel: string }> };

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { nyckel } = await params;
  const tenant = getTenantByPublicKey(nyckel);
  return {
    title: tenant ? `Chatt — ${tenant.name}` : "Chatt",
    robots: { index: false, follow: false }
  };
}

export default async function EmbedPage({ params }: Props) {
  const { nyckel } = await params;
  const tenant = getTenantByPublicKey(nyckel);

  if (!tenant) {
    notFound();
  }

  return (
    <>
      {/* Kundens palett, samma mekanism som kundsajterna: komponenterna
          läser tokens, style-taggen byter deras värden. */}
      <style dangerouslySetInnerHTML={{ __html: paletteToCss(tenant.palette) }} />
      <EmbedYta
        slug={tenant.slug}
        namn={tenant.name}
        logo={tenant.logo}
        farg={`oklch(${tenant.palette.ochre})`}
      />
    </>
  );
}
