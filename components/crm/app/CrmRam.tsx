"use client";

// Astryx egen CSS laddas bara här, alltså bara av CRM:et. Lagerordningen står
// överst i app/globals.css, som rotlayouten laddar före den här filen.
import "@astryxdesign/core/reset.css";
import "@astryxdesign/core/astryx.css";
import "@/lib/crm/astryx/snajp.css";
import "@/components/crm/app/crm.css";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import NextLink from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { ArrowLeft, LifeBuoy, Search } from "lucide-react";
import { AppShell } from "@astryxdesign/core/AppShell";
import { Avatar } from "@astryxdesign/core/Avatar";
import { Icon } from "@astryxdesign/core/Icon";
import { InternationalizationProvider } from "@astryxdesign/core/i18n";
import { Kbd } from "@astryxdesign/core/Kbd";
import { LinkProvider } from "@astryxdesign/core/Link";
import svSE from "@astryxdesign/core/locales/sv-SE.generated.js";
import { ProgressBar } from "@astryxdesign/core/ProgressBar";
import { IconButton } from "@astryxdesign/core/IconButton";
import { SideNav, SideNavHeading, SideNavItem, SideNavSection, useSideNavRenderMode } from "@astryxdesign/core/SideNav";
import { Text } from "@astryxdesign/core/Text";
import { Timestamp } from "@astryxdesign/core/Timestamp";
import { Theme } from "@astryxdesign/core/theme";
import { Logo } from "@/components/Logo";
import { HjalpRuta, useHjalpArenden } from "@/components/snajp/HjalpRuta";
import { Arbetsytemeny, Skaldialoger, type Skaldialog } from "@/components/crm/app/Arbetsytemeny";
import { Banderoll } from "@/components/crm/app/Banderoll";
import { Kommandopalett } from "@/components/crm/app/Kommandopalett";
import { NotisKalla, notistal, useNotiser } from "@/components/crm/app/Notiser";
import { SkaletsAtgarder, type Skalatgarder } from "@/components/crm/app/Skalet";
import { Objektikon, Prick } from "@/components/crm/app/kit";
import { ArbetsytanAktiveras, Sida } from "@/components/crm/app/Sida";
import { useDashboard } from "@/components/dashboard/DashboardContext";
import { snajpTheme } from "@/lib/crm/astryx/snajp";
import { ASTRYX_SVENSKA } from "@/lib/crm/astryx/svenska";
import { SynklageKalla, avslutar, klara, pagar, useSynklage } from "@/components/crm/app/synklage";
import { TillaggSaknas, TillgangKalla, useTillgang } from "@/components/crm/app/Tillagg";
import { SYSTEMNAMN } from "@/lib/crm/api";
import { attRatta } from "@/lib/crm/felkoder";
import { narbar, postForVag, synligaGrupper, synligaPoster, type Navpost } from "@/lib/crm/navigering";
import { useLocale } from "@/lib/i18n";
import { TEMA_COOKIE, colorScheme, dataTheme, type Tema } from "@/lib/tema";

/**
 * De vyer som fanns före navigeringsregistret. Nya vyer står bara i registret
 * (lib/crm/navigering.ts), med vägar i flera led (`iris/leads`).
 */
export type CrmVy = "oversikt" | "bolag" | "personer" | "affarer" | "uppgifter" | "synk" | "sparrar" | "utvecklare";

/**
 * Astryx rot-tema skriver `data-theme` på <html> och TAR BORT det när temat
 * avmonteras (Theme.js: useRootThemeSync). Snajps mörka läge bor i just det
 * attributet, stämplat av servern i app/layout.tsx. Utan vakten hade den som
 * valt mörkt fått en ljus arbetsyta när hon gick tillbaka från CRM:et, tills
 * nästa omladdning. Vakten ligger UTANFÖR temat och sätter tillbaka det senast
 * valda temat efter att temat har städat.
 *
 * Bara vid avmontering: temat ligger i en ref och effekten har tom
 * beroendelista. Körde avstädningen vid varje byte i menyn skrev den tillbaka
 * det GAMLA temat efter att Astryx redan satt det nya.
 */
function TemaVakt({ tema, children }: Readonly<{ tema: Tema; children: React.ReactNode }>) {
  const senaste = useRef(tema);
  useEffect(() => {
    senaste.current = tema;
  }, [tema]);
  useEffect(
    () => () => {
      window.setTimeout(() => {
        const nu = senaste.current;
        const rot = document.documentElement;
        const varde = dataTheme(nu);
        if (varde) rot.setAttribute("data-theme", varde);
        else rot.removeAttribute("data-theme");
        rot.style.colorScheme = colorScheme(nu);
      }, 0);
    },
    []
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

/**
 * Vyn, eller helsidan om arbetsytan saknar tillägget (Tillagg.tsx) eller inte är
 * kopplad till agenterna än (SK-157). Avgörs en gång, i skalet.
 */
function Innehall({ children }: Readonly<{ children: React.ReactNode }>) {
  const tillgang = useTillgang();
  if (tillgang === "saknas") return <TillaggSaknas />;
  if (tillgang === "aktiveras") {
    return (
      <Sida rubrik="Snajp CRM" utfyllnad="sida">
        <div className="pt-4">
          <ArbetsytanAktiveras yta="Snajp CRM" />
        </div>
      </Sida>
    );
  }
  return children;
}

/**
 * Bladet: banderollen (kundbesök, läsroll, demo) som en fast rad överst, och
 * vyn under den. Vyn fyller resten av höjden och rullar själv, så banderollen
 * står kvar när man rullar.
 */
function Blad({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <div className="flex h-full min-h-0 flex-col">
      <Banderoll />
      <div className="min-h-0 flex-1">
        <Innehall>{children}</Innehall>
      </div>
    </div>
  );
}

/** En post ur registret i sidofältet, med sitt tal (Leads: olästa notiser) när den har ett. */
function Menypost({ post, bas, vald }: Readonly<{ post: Navpost; bas: string; vald: boolean }>) {
  const { text } = useLocale();
  const { antal } = useNotiser();
  const tal = post.raknare === "leadsnotiser" ? antal : 0;
  return (
    <SideNavItem
      label={text(post.namn)}
      href={`${bas}/${post.nyckel}`}
      icon={<Objektikon ikon={post.ikon} ton={post.ton} storlek={24} />}
      isSelected={vald}
      endContent={
        tal > 0 ? (
          <span className="crm-railtal tabular-nums">
            {notistal(tal)}
            <span className="sr-only">{tal === 1 ? text({ sv: " oläst", en: " unread" }) : text({ sv: " olästa", en: " unread" })}</span>
          </span>
        ) : undefined
      }
    />
  );
}

const HOPFALLD_NYCKEL = "snajp.crm.nav-hopfalld";


/**
 * Skalet runt varje CRM-sida (DESIGN-CRM.md § Skalet): tema, språk, länkar,
 * den marinblå sidnavigeringen, banderollen, notiserna och kommandopaletten.
 * Innehållet ligger som ett upphöjt blad bredvid navigeringen (AppShell `elevated`).
 *
 * Navigeringen ritas ur registret (lib/crm/navigering.ts): grupper med de poster
 * den som tittar får se, och bara poster som gör något.
 *
 * `bas` är roten vyerna ligger under. Appen använder `/crm`, förhandsvisningen
 * `/forhandsvisning/crm`, och ramen är densamma i båda.
 */
export function CrmRam({
  tema,
  bas = "/crm",
  arbetsyta,
  hjalp = false,
  notiser = false,
  atgarder,
  children
}: Readonly<{
  tema: Tema;
  bas?: string;
  arbetsyta?: string;
  /**
   * Hjälprutan (components/snajp/HjalpRuta.tsx): samma ruta som i arbetsytan, så att en fråga,
   * kontext till kunskapsbasen och en felrapport går att lämna härifrån, med CRM-sidans adress i rapporten.
   * Av i demoläget och utan inloggning, som i arbetsytan.
   */
  hjalp?: boolean;
  /** Leadsnotiserna (Notiser.tsx). Av utan inloggning och i demoarbetsytor; skalet kräver dessutom produkten Leads. */
  notiser?: boolean;
  /** Förhandsvisningens egna åtgärder för vyväxeln och utloggningen (Skalet.tsx). */
  atgarder?: Partial<Skalatgarder>;
  children: React.ReactNode;
}>) {
  const { locale, text } = useLocale();
  const router = useRouter();
  const vag = usePathname() ?? "";
  const { products, addons, isPlatformAdmin } = useDashboard();
  const lage = useMemo(() => ({ products, addons, isPlatformAdmin }), [products, addons, isPlatformAdmin]);
  const grupper = useMemo(() => synligaGrupper(lage), [lage]);
  // Stabila värden till paletten: en ny källa medan den är öppen kör om sökningen.
  const palettposter = useMemo(() => synligaPoster(lage), [lage]);
  const oppnaBytKund = useCallback(() => setDialog("bytkund"), []);
  const aktiv = postForVag(vag, bas);
  // Temat kan bytas i menyn: samma cookie som Inställningar › Tema, och <html> byts direkt.
  const [temaNu, setTemaNu] = useState<Tema>(tema);
  const morkt = temaNu === "morkt";
  const [palett, setPalett] = useState(false);
  const [hopfalld, setHopfalld] = useState(false);
  const [hjalpOppen, setHjalpOppen] = useState(false);
  const [dialog, setDialog] = useState<Skaldialog>(null);
  // Ärenden som väntar på kunden (ett svar, eller att prova en rättning) syns som ett tal på raden.
  const { vantar } = useHjalpArenden(hjalp, false);
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

  const valjTema = (nytt: Tema) => {
    setTemaNu(nytt);
    const rot = document.documentElement;
    const varde = dataTheme(nytt);
    if (varde) rot.setAttribute("data-theme", varde);
    else rot.removeAttribute("data-theme");
    rot.style.colorScheme = colorScheme(nytt);
    document.cookie = `${TEMA_COOKIE}=${nytt}; path=/; max-age=31536000; samesite=lax`;
  };

  /**
   * Skydd mot att bli strandad (SK-071): står man på en vy som arbetsytan inte
   * når (produkten saknas, eller bara plattformsadmin ser den), går man till
   * översikten. En vy som inte är byggd än har ingen sida och svarar 404 som förut.
   */
  const strandad = aktiv != null && aktiv.byggd && !narbar(aktiv, lage);
  useEffect(() => {
    if (strandad) router.replace(`${bas}/oversikt`);
  }, [strandad, router, bas]);

  return (
    <TemaVakt tema={temaNu}>
      {/* Aldrig mode="system": då tar Astryx bort <html data-theme>, som Snajps mörka läge läser. */}
      <Theme theme={snajpTheme} mode={morkt ? "dark" : "light"}>
        <InternationalizationProvider
          locale={locale === "sv" ? "sv-SE" : "en"}
          messages={{ "sv-SE": svSE }}
          overrides={{ "sv-SE": ASTRYX_SVENSKA }}
        >
          <LinkProvider component={NextLink}>
            <SkaletsAtgarder atgarder={atgarder}>
            <TillgangKalla>
            <SynklageKalla>
            <NotisKalla pa={notiser && products.includes("leads")} bas={bas}>
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
                          <Arbetsytemeny
                            tema={temaNu}
                            valjTema={valjTema}
                            oppna={setDialog}
                            oppnaHjalp={hjalp ? () => setHjalpOppen(true) : undefined}
                          />
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
                      {hjalp ? (
                        <SideNavItem
                          label={text({ sv: "Hjälp och fel", en: "Help and issues" })}
                          icon={LifeBuoy}
                          onClick={() => setHjalpOppen(true)}
                          endContent={
                            vantar > 0 ? (
                              <span className="crm-railtal tabular-nums">
                                {vantar}
                                <span className="sr-only">
                                  {vantar === 1 ? text({ sv: " ärende väntar på dig", en: " case is waiting for you" }) : text({ sv: " ärenden väntar på dig", en: " cases are waiting for you" })}
                                </span>
                              </span>
                            ) : undefined
                          }
                        />
                      ) : null}
                      <SideNavItem label={text({ sv: "Till arbetsytan", en: "Back to workspace" })} href="/dashboard" icon={ArrowLeft} />
                    </div>
                  }
                  footerIcons={<MobilSok oppna={() => setPalett(true)} />}
                >
                  {grupper.map((g) => (
                    <SideNavSection key={g.nyckel} title={text(g.namn)}>
                      {g.poster.map((p) => (
                        <Menypost key={p.nyckel} post={p} bas={bas} vald={aktiv?.nyckel === p.nyckel} />
                      ))}
                    </SideNavSection>
                  ))}
                </SideNav>
              }
            >
              <Blad>{children}</Blad>
              <Kommandopalett
                oppen={palett}
                setOppen={setPalett}
                bas={bas}
                poster={palettposter}
                bytKund={isPlatformAdmin ? oppnaBytKund : undefined}
              />
              <Skaldialoger dialog={dialog} stang={() => setDialog(null)} />
              {hjalp && hjalpOppen ? <HjalpRuta onStang={() => setHjalpOppen(false)} /> : null}
            </AppShell>
            </NotisKalla>
            </SynklageKalla>
            </TillgangKalla>
            </SkaletsAtgarder>
          </LinkProvider>
        </InternationalizationProvider>
      </Theme>
    </TemaVakt>
  );
}
