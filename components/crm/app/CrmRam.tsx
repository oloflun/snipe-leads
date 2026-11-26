"use client";

// Astryx egen CSS laddas bara här, alltså bara av CRM:et. Lagerordningen står
// överst i app/globals.css, som rotlayouten laddar före den här filen.
import "@astryxdesign/core/reset.css";
import "@astryxdesign/core/astryx.css";
import "@/lib/crm/astryx/snajp.css";
import "@/components/crm/app/crm.css";

import { useEffect, useState } from "react";
import NextLink from "next/link";
import { usePathname } from "next/navigation";
import { ArrowLeft, Search, Settings } from "lucide-react";
import { AppShell } from "@astryxdesign/core/AppShell";
import { Avatar } from "@astryxdesign/core/Avatar";
import { Icon } from "@astryxdesign/core/Icon";
import { InternationalizationProvider } from "@astryxdesign/core/i18n";
import { Kbd } from "@astryxdesign/core/Kbd";
import { LinkProvider } from "@astryxdesign/core/Link";
import svSE from "@astryxdesign/core/locales/sv-SE.generated.js";
import { NavHeadingMenu, NavHeadingMenuItem } from "@astryxdesign/core/NavMenu";
import { ProgressBar } from "@astryxdesign/core/ProgressBar";
import { IconButton } from "@astryxdesign/core/IconButton";
import { SideNav, SideNavHeading, SideNavItem, SideNavSection, useSideNavRenderMode } from "@astryxdesign/core/SideNav";
import { Text } from "@astryxdesign/core/Text";
import { Timestamp } from "@astryxdesign/core/Timestamp";
import { Theme } from "@astryxdesign/core/theme";
import { Logo } from "@/components/Logo";
import { Kommandopalett } from "@/components/crm/app/Kommandopalett";
import { OBJEKT, Objektikon, Prick, type Objekt } from "@/components/crm/app/kit";
import { snajpTheme } from "@/lib/crm/astryx/snajp";
import { ASTRYX_SVENSKA } from "@/lib/crm/astryx/svenska";
import { SynklageKalla, avslutar, klara, pagar, useSynklage } from "@/components/crm/app/synklage";
import { TillaggSaknas, TillgangKalla, useTillgang } from "@/components/crm/app/Tillagg";
import { SYSTEMNAMN } from "@/lib/crm/api";
import { attRatta } from "@/lib/crm/felkoder";
import { useLocale } from "@/lib/i18n";
import { colorScheme, dataTheme, type Tema } from "@/lib/tema";

export type CrmVy = "oversikt" | "bolag" | "personer" | "synk" | "utvecklare";

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
 * Senaste synkens läge, längst ned i navigeringen. Läser det delade synkläget
 * (synklage.tsx), så att kortet visar samma tal som Synk och Översikten.
 */
function Synkkort({ bas }: Readonly<{ bas: string }>) {
  const { text } = useLocale();
  const { korningar, anslutningar } = useSynklage();
  const senaste = korningar?.[0];

  if (!senaste) return null;
  const igang = pagar(senaste);
  const anslutning = senaste.connection_id ? anslutningar[senaste.connection_id] : undefined;
  const rubrik = anslutning ? (SYSTEMNAMN[anslutning.system] ?? anslutning.name) : text({ sv: "Synk", en: "Sync" });
  const lage =
    senaste.status === "failed"
      ? { ton: "fara" as const, text: text({ sv: "Misslyckades", en: "Failed" }) }
      : avslutar(senaste)
        ? { ton: "ockra" as const, text: text({ sv: "Avslutar", en: "Finishing" }) }
        : igang
          ? { ton: "ockra" as const, text: text({ sv: "Synkar nu", en: "Syncing now" }) }
          : attRatta(senaste) > 0
            ? { ton: "ockra" as const, text: text({ sv: "Klar, med poster att rätta", en: "Done, with records to fix" }) }
            : { ton: "mossa" as const, text: text({ sv: "Klar", en: "Done" }) };
  const tid = senaste.completed_at ?? senaste.created_at;

  return (
    <NextLink
      href={`${bas}/synk?korning=${encodeURIComponent(senaste.id)}`}
      className="crm-synkkort mx-1 mb-1 block rounded-[16px] p-3 no-underline"
    >
      <span className="flex items-center gap-2">
        <Prick ton={lage.ton} pulserar={igang} />
        <span className="min-w-0 flex-1 truncate text-[0.8125rem] font-semibold text-rail-text">{rubrik}</span>
        {tid ? <Timestamp value={tid} format="relative" isLive hasTooltip={false} /> : null}
      </span>
      <span className="mt-1 block text-[0.8125rem] text-rail-muted">{lage.text}</span>
      <span className="sr-only">{text({ sv: "Öppna körningen i Synk.", en: "Open the run in Sync." })}</span>
      {igang ? (
        <span className="mt-2 block">
          <ProgressBar
            label={text({ sv: "Synkens förlopp", en: "Sync progress" })}
            isLabelHidden
            isIndeterminate={senaste.status === "queued" || senaste.counts.total === 0 || avslutar(senaste)}
            value={klara(senaste)}
            max={Math.max(senaste.counts.total, 1)}
          />
          <span className="mt-1 block text-[0.75rem] tabular-nums text-rail-muted">
            {text({
              sv: `${klara(senaste).toLocaleString("sv-SE")} av ${senaste.counts.total.toLocaleString("sv-SE")} poster`,
              en: `${klara(senaste).toLocaleString("en-GB")} of ${senaste.counts.total.toLocaleString("en-GB")} records`
            })}
          </span>
        </span>
      ) : null}
    </NextLink>
  );
}

/**
 * Sökningen i mobilens toppfält. Toppfältet ritar bara rubriken och
 * `footerIcons`, så sökraden under rubriken når inte dit; utan knappen fanns
 * kommandopaletten bara i lådan. Knappen syns bara i toppfältet: på skrivbordet
 * finns sökraden, och i lådan står den överst.
 */
function MobilSok({ oppna }: Readonly<{ oppna: () => void }>) {
  const { text } = useLocale();
  if (useSideNavRenderMode() !== "topbar") return null;
  return (
    <IconButton
      label={text({ sv: "Sök eller hoppa till", en: "Search or jump to" })}
      icon={<Icon icon={Search} size="sm" />}
      variant="ghost"
      size="md"
      className="crm-mobilsok"
      onClick={oppna}
    />
  );
}

/** Vyn, eller helsidan om arbetsytan saknar tillägget (Tillagg.tsx). Avgörs en gång, i skalet. */
function Innehall({ children }: Readonly<{ children: React.ReactNode }>) {
  return useTillgang() === "saknas" ? <TillaggSaknas /> : children;
}

const HOPFALLD_NYCKEL = "snajp.crm.nav-hopfalld";

/**
 * Skalet runt varje CRM-sida (DESIGN-CRM.md § Skalet): tema, språk, länkar,
 * den ljusa sidnavigeringen och kommandopaletten. Innehållet ligger som ett
 * upphöjt blad bredvid navigeringen (AppShell `elevated`).
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
  const aktiv = ((vag.startsWith(bas) ? vag.slice(bas.length).split("/")[1] : "") || "oversikt") as Objekt;
  const morkt = tema === "morkt";
  const [palett, setPalett] = useState(false);
  const [hopfalld, setHopfalld] = useState(false);
  const namn = arbetsyta || "Snajp";

  // Hopfällningen är ett utseendeval per läsare: det får bo i webbläsaren.
  useEffect(() => {
    try {
      setHopfalld(window.localStorage.getItem(HOPFALLD_NYCKEL) === "1");
    } catch {
      /* privat fönster: utfälld */
    }
  }, []);
  const fallIhop = (varde: boolean) => {
    setHopfalld(varde);
    try {
      window.localStorage.setItem(HOPFALLD_NYCKEL, varde ? "1" : "0");
    } catch {
      /* inget att spara i */
    }
  };

  const post = (vy: Objekt) => (
    <SideNavItem
      key={vy}
      label={text(OBJEKT[vy].namn)}
      href={`${bas}/${vy}`}
      icon={<Objektikon objekt={vy} storlek={24} />}
      isSelected={aktiv === vy}
    />
  );

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
            <TillgangKalla>
            <SynklageKalla>
            <AppShell
              variant="elevated"
              contentPadding={0}
              mobileNav={{ breakpoint: "md" }}
              sideNav={
                <SideNav
                  className={hopfalld ? "crm-rail" : "crm-rail crm-nav-bred"}
                  // Knappens text kommer ur Astryx egna språkfiler (sv-SE och en).
                  collapsible={{ isCollapsed: hopfalld, onCollapsedChange: fallIhop }}
                  header={
                    <div className="crm-rail-huvud">
                      <NextLink
                        href={`${bas}/oversikt`}
                        className={hopfalld ? "crm-logga crm-logga-mark" : "crm-logga"}
                        aria-label={text({ sv: "Snajp, till översikten", en: "Snajp, to the overview" })}
                      >
                        <Logo compact={hopfalld} tone="paper" />
                      </NextLink>
                      <SideNavHeading
                        heading={namn}
                        icon={<Avatar name={namn} size={24} shape="rounded" tooltip={false} className="crm-arbetsyta" />}
                        menu={
                          <NavHeadingMenu>
                            <NavHeadingMenuItem label={text({ sv: "Till arbetsytan", en: "Back to workspace" })} href="/dashboard" icon={ArrowLeft} />
                            <NavHeadingMenuItem label={text({ sv: "Inställningar", en: "Settings" })} href="/settings" icon={Settings} />
                          </NavHeadingMenu>
                        }
                      />
                    </div>
                  }
                  topContent={
                    hopfalld ? (
                      <SideNavItem label={text({ sv: "Sök eller hoppa till", en: "Search or jump to" })} icon="search" onClick={() => setPalett(true)} />
                    ) : (
                      <button
                        type="button"
                        onClick={() => setPalett(true)}
                        className="crm-sokrad mx-1 mt-1 flex h-9 w-[calc(100%-0.5rem)] items-center gap-2 rounded-[10px] px-2.5 text-left"
                      >
                        <Icon icon={Search} size="sm" color="secondary" />
                        <Text color="secondary" maxLines={1}>
                          {text({ sv: "Sök eller hoppa till", en: "Search or jump to" })}
                        </Text>
                        <span className="ml-auto">
                          <Kbd keys="mod+k" />
                        </span>
                      </button>
                    )
                  }
                  footer={
                    <div className="flex flex-col gap-1">
                      {hopfalld ? null : <Synkkort bas={bas} />}
                      <SideNavItem label={text({ sv: "Till arbetsytan", en: "Back to workspace" })} href="/dashboard" icon={ArrowLeft} />
                    </div>
                  }
                  footerIcons={<MobilSok oppna={() => setPalett(true)} />}
                >
                  <SideNavSection title={text({ sv: "Arbetsyta", en: "Workspace" })}>
                    {post("oversikt")}
                    {post("bolag")}
                    {post("personer")}
                  </SideNavSection>
                  <SideNavSection title={text({ sv: "Data", en: "Data" })}>
                    {post("synk")}
                    {post("utvecklare")}
                  </SideNavSection>
                </SideNav>
              }
            >
              <Innehall>{children}</Innehall>
              <Kommandopalett oppen={palett} setOppen={setPalett} bas={bas} />
            </AppShell>
            </SynklageKalla>
            </TillgangKalla>
          </LinkProvider>
        </InternationalizationProvider>
      </Theme>
    </TemaVakt>
  );
}
