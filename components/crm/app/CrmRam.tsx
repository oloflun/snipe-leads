"use client";

// Astryx egen CSS laddas bara här, alltså bara av CRM:et. Lagerordningen står
// överst i app/globals.css, som rotlayouten laddar före den här filen.
import "@astryxdesign/core/reset.css";
import "@astryxdesign/core/astryx.css";
import "@/lib/crm/astryx/snajp.css";

import { useEffect } from "react";
import NextLink from "next/link";
import { usePathname } from "next/navigation";
import { ArrowLeft, Building2, KeyRound, RefreshCw, Users } from "lucide-react";
import { AppShell } from "@astryxdesign/core/AppShell";
import { Icon } from "@astryxdesign/core/Icon";
import { InternationalizationProvider } from "@astryxdesign/core/i18n";
import { LinkProvider } from "@astryxdesign/core/Link";
import svSE from "@astryxdesign/core/locales/sv-SE.generated.js";
import { SideNav, SideNavHeading, SideNavItem, SideNavSection } from "@astryxdesign/core/SideNav";
import { MediaTheme, Theme } from "@astryxdesign/core/theme";
import { snajpTheme } from "@/lib/crm/astryx/snajp";
import { ASTRYX_SVENSKA } from "@/lib/crm/astryx/svenska";
import { useLocale } from "@/lib/i18n";
import { colorScheme, dataTheme, type Tema } from "@/lib/tema";

export type CrmVy = "bolag" | "personer" | "synk" | "utvecklare";

/**
 * Astryx rot-tema skriver `data-theme` på <html> och TAR BORT det när temat
 * avmonteras (Theme.js: useRootThemeSync). Snajps mörka läge bor i just det
 * attributet, stämplat av servern i app/layout.tsx. Utan vakten hade den som
 * valt mörkt fått en ljus arbetsyta när hon gick tillbaka från CRM:et, tills
 * nästa omladdning. Vakten ligger UTANFÖR temat och sätter tillbaka serverns
 * värde efter att temat har städat.
 */
function TemaVakt({ tema, children }: Readonly<{ tema: Tema; children: React.ReactNode }>) {
  useEffect(
    () => () => {
      window.setTimeout(() => {
        const rot = document.documentElement;
        const varde = dataTheme(tema);
        if (varde) rot.setAttribute("data-theme", varde);
        else rot.removeAttribute("data-theme");
        rot.style.colorScheme = colorScheme(tema);
      }, 0);
    },
    [tema]
  );
  return children;
}

/**
 * Skalet runt varje CRM-sida: tema, språk, länkar och sidnavigeringen.
 *
 * `bas` är roten vyerna ligger under. Appen använder `/crm`, förhandsvisningen
 * `/forhandsvisning/crm`, och ramen är densamma i båda.
 */
export function CrmRam({
  tema,
  bas = "/crm",
  arbetsyta,
  children
}: Readonly<{ tema: Tema; bas?: string; arbetsyta?: string; children: React.ReactNode }>) {
  const { locale, text } = useLocale();
  const vag = usePathname() ?? "";
  const aktiv = (vag.startsWith(bas) ? vag.slice(bas.length).split("/")[1] : "") || "bolag";
  const morkt = tema === "morkt";

  return (
    <TemaVakt tema={tema}>
      {/* Aldrig mode="system": då tar Astryx bort <html data-theme>, som Snajps mörka läge läser. */}
      <Theme theme={snajpTheme} mode={morkt ? "dark" : "light"}>
        <InternationalizationProvider
          locale={locale === "sv" ? "sv-SE" : "en"}
          messages={{ "sv-SE": svSE }}
          overrides={{ "sv-SE": ASTRYX_SVENSKA }}
        >
          <LinkProvider component={NextLink}>
            <AppShell
              variant="section"
              sideNav={
                // Railen är bläck, arbetsytans enda tonala vändning. Temats
                // roller för railen pekar på Snajps egna variabler (--ink som
                // yta, --paper som text), och de byter själva plats i mörkt
                // läge: där är railen ljus med mörk text, som i resten av appen.
                // Temat har därför samma roller för båda ytorna (onDark, onLight).
                <MediaTheme mode={morkt ? "light" : "dark"}>
                  <SideNav
                    collapsible
                    header={
                      <SideNavHeading
                        heading={text({ sv: "Snajp CRM", en: "Snajp CRM" })}
                        subheading={arbetsyta}
                        headingHref={`${bas}/bolag`}
                      />
                    }
                    footer={
                      <SideNavItem
                        label={text({ sv: "Till arbetsytan", en: "Back to workspace" })}
                        href="/dashboard"
                        icon={<Icon icon={ArrowLeft} />}
                      />
                    }
                  >
                    <SideNavSection title={text({ sv: "Register", en: "Records" })}>
                      <SideNavItem
                        label={text({ sv: "Bolag", en: "Companies" })}
                        href={`${bas}/bolag`}
                        isSelected={aktiv === "bolag"}
                        icon={<Icon icon={Building2} />}
                      />
                      <SideNavItem
                        label={text({ sv: "Personer", en: "People" })}
                        href={`${bas}/personer`}
                        isSelected={aktiv === "personer"}
                        icon={<Icon icon={Users} />}
                      />
                    </SideNavSection>
                    <SideNavSection title={text({ sv: "Data", en: "Data" })}>
                      <SideNavItem
                        label={text({ sv: "Synk", en: "Sync" })}
                        href={`${bas}/synk`}
                        isSelected={aktiv === "synk"}
                        icon={<Icon icon={RefreshCw} />}
                      />
                      <SideNavItem
                        label={text({ sv: "Utvecklare", en: "Developers" })}
                        href={`${bas}/utvecklare`}
                        isSelected={aktiv === "utvecklare"}
                        icon={<Icon icon={KeyRound} />}
                      />
                    </SideNavSection>
                  </SideNav>
                </MediaTheme>
              }
            >
              {children}
            </AppShell>
          </LinkProvider>
        </InternationalizationProvider>
      </Theme>
    </TemaVakt>
  );
}
