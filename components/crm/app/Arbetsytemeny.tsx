"use client";

import { useEffect, useMemo, useState } from "react";
import { ArrowLeft, Eye, Flag, Languages, LogOut, Mail, Moon, Repeat, Settings, ShieldCheck, Sun, Lock } from "lucide-react";
import { Button } from "@astryxdesign/core/Button";
import { Dialog, DialogHeader } from "@astryxdesign/core/Dialog";
import { Divider } from "@astryxdesign/core/Divider";
import { Layout, LayoutContent, LayoutFooter } from "@astryxdesign/core/Layout";
import { List, ListItem } from "@astryxdesign/core/List";
import { NavHeadingMenu, NavHeadingMenuItem } from "@astryxdesign/core/NavMenu";
import { Skeleton } from "@astryxdesign/core/Skeleton";
import { Spinner } from "@astryxdesign/core/Spinner";
import { HStack } from "@astryxdesign/core/Stack";
import { TextInput } from "@astryxdesign/core/TextInput";
import { useSkaletsAtgarder } from "@/components/crm/app/Skalet";
import { useDashboard } from "@/components/dashboard/DashboardContext";
import { SNAJP_SUPPORT_EPOST } from "@/components/snajp/AgentMenu";
import { readJsonBody } from "@/lib/http/json";
import { useLocale, type Localized } from "@/lib/i18n";
import type { Tema } from "@/lib/tema";

/**
 * Arbetsyteväxlarens meny (SK-065 till SK-069, SK-074, SK-075, AD-008, AD-010):
 * allt dagens railfot och Meny bär, i växlarens popover överst i sidofältet.
 * Samma meny står i mobilens toppfält (SK-066), så den som har en telefon når
 * språk, tema, kontakt och utloggning där.
 *
 * Plattformsadmin får också Byt kund och vyväxeln Admin och Demo. Att de syns
 * är hövlighet; grinden är `getPlatformAdmin()` i server actionen (Sekretess 5).
 *
 * Dialogerna (Byt kund, Kontakt, Dataskydd) ritas utanför menyn, i
 * `Skaldialoger`: menyn stänger sig själv vid ett val.
 */

export type Skaldialog = "bytkund" | "kontakt" | "dataskydd" | null;

/** "Anmäl felaktigt svar" utan hjälprutan: e-postklienten med ämne, mall och tekniska uppgifter (AgentMenu.tsx). */
function anmalLank(text: (v: Localized) => string): string {
  const tekniskt = [
    "Yta: crm",
    `Tidpunkt: ${new Date().toISOString()}`,
    typeof window !== "undefined" ? `Sida: ${window.location.href}` : null
  ]
    .filter(Boolean)
    .join("\n");
  const amne = encodeURIComponent(text({ sv: "Felaktigt svar från Snajp-agenten", en: "Incorrect answer from the Snajp agent" }));
  const mall = text({
    sv: "Beskriv kort vad som blev fel:\n\n\n---\nTekniska uppgifter (låt stå, de hjälper oss hitta samtalet):",
    en: "Briefly describe what went wrong:\n\n\n---\nTechnical details (please keep, they help us find the conversation):"
  });
  return `mailto:${SNAJP_SUPPORT_EPOST}?subject=${amne}&body=${encodeURIComponent(`${mall}\n${tekniskt}\n`)}`;
}

export function Arbetsytemeny({
  tema,
  valjTema,
  oppna,
  oppnaHjalp
}: Readonly<{
  tema: Tema;
  valjTema: (tema: Tema) => void;
  oppna: (dialog: Exclude<Skaldialog, null>) => void;
  /** Hjälprutan, där en felrapport blir ett ärende. Utan den öppnar Anmäl felaktigt svar e-postklienten. */
  oppnaHjalp?: () => void;
}>) {
  const { text, toggleLocale } = useLocale();
  const { isPlatformAdmin, impersonation, vy, signedIn, userEmail } = useDashboard();
  const { bytVy, loggaUt } = useSkaletsAtgarder();
  const morkt = tema === "morkt";

  return (
    <NavHeadingMenu>
      <NavHeadingMenuItem label={text({ sv: "Inställningar", en: "Settings" })} href="/settings" icon={Settings} />
      <NavHeadingMenuItem
        label={text({ sv: "English", en: "Svenska" })}
        description={text({ sv: "Byt språk till engelska", en: "Change the language to Swedish" })}
        icon={Languages}
        onClick={toggleLocale}
      />
      <NavHeadingMenuItem
        label={morkt ? text({ sv: "Ljust läge", en: "Light mode" }) : text({ sv: "Mörkt läge", en: "Dark mode" })}
        icon={morkt ? Sun : Moon}
        onClick={() => valjTema(morkt ? "ljust" : "morkt")}
      />
      <Divider />
      <NavHeadingMenuItem label={text({ sv: "Kontakt", en: "Contact" })} icon={Mail} onClick={() => oppna("kontakt")} />
      <NavHeadingMenuItem label={text({ sv: "Dataskydd", en: "Data protection" })} icon={Lock} onClick={() => oppna("dataskydd")} />
      {oppnaHjalp ? (
        <NavHeadingMenuItem
          label={text({ sv: "Anmäl felaktigt svar", en: "Report an incorrect answer" })}
          description={text({ sv: "Blir ett ärende hos Snajp", en: "Becomes a case at Snajp" })}
          icon={Flag}
          onClick={oppnaHjalp}
        />
      ) : (
        <NavHeadingMenuItem
          label={text({ sv: "Anmäl felaktigt svar", en: "Report an incorrect answer" })}
          description={text({ sv: "Öppnar din e-postklient", en: "Opens your email client" })}
          icon={Flag}
          href={anmalLank(text)}
        />
      )}
      {isPlatformAdmin ? (
        <>
          <Divider />
          <NavHeadingMenuItem
            label={text({ sv: "Byt kund", en: "Switch customer" })}
            description={impersonation ? text({ sv: `Tittar som ${impersonation.namn}`, en: `Viewing as ${impersonation.namn}` }) : undefined}
            icon={Repeat}
            onClick={() => oppna("bytkund")}
          />
          <NavHeadingMenuItem
            label={text({ sv: "Admin", en: "Admin" })}
            description={
              vy === "admin" && !impersonation
                ? text({ sv: "Visas nu", en: "Showing now" })
                : text({ sv: "Din egen arbetsyta", en: "Your own workspace" })
            }
            icon={ShieldCheck}
            isDisabled={vy === "admin" && !impersonation}
            onClick={() => void bytVy("admin")}
          />
          <NavHeadingMenuItem
            label={text({ sv: "Demo", en: "Demo" })}
            description={vy === "demo" ? text({ sv: "Visas nu", en: "Showing now" }) : text({ sv: "Demokontot, som en kund ser det", en: "The demo account, as a customer sees it" })}
            icon={Eye}
            isDisabled={vy === "demo"}
            onClick={() => void bytVy("demo")}
          />
        </>
      ) : null}
      <Divider />
      <NavHeadingMenuItem label={text({ sv: "Till arbetsytan", en: "Back to workspace" })} href="/dashboard" icon={ArrowLeft} />
      {signedIn ? (
        <NavHeadingMenuItem
          label={text({ sv: "Logga ut", en: "Sign out" })}
          description={userEmail ?? undefined}
          icon={LogOut}
          onClick={() => void loggaUt()}
        />
      ) : null}
    </NavHeadingMenu>
  );
}

// ---------------------------------------------------------------------------
// Dialogerna
// ---------------------------------------------------------------------------

export function Skaldialoger({ dialog, stang }: Readonly<{ dialog: Skaldialog; stang: () => void }>) {
  return (
    <>
      <BytKundDialog oppen={dialog === "bytkund"} stang={stang} />
      <OmSnajpDialog slag={dialog === "kontakt" || dialog === "dataskydd" ? dialog : null} stang={stang} />
    </>
  );
}

type Kund = { slug: string; name: string };

/**
 * Byt kund (SK-074, AD-010, AD-011): sökbar lista över de kunder som går att
 * öppna (`GET /api/admin/kunder`), hämtad först när dialogen öppnas. Ett val kör
 * samma kundbesök som dagens Byt kund och Öppna: cookien, loggen, och en hård
 * omladdning på samma vy. Dialogen stängs inte medan bytet pågår.
 */
function BytKundDialog({ oppen, stang }: Readonly<{ oppen: boolean; stang: () => void }>) {
  const { text } = useLocale();
  const { impersonation } = useDashboard();
  const { bytVy } = useSkaletsAtgarder();
  const [sok, setSok] = useState("");
  const [kunder, setKunder] = useState<Kund[] | null>(null);
  const [fel, setFel] = useState(false);
  const [byter, setByter] = useState<string | null>(null);
  const [bytFel, setBytFel] = useState(false);

  useEffect(() => {
    if (!oppen || kunder) return;
    let avbruten = false;
    void (async () => {
      try {
        const svar = await fetch("/api/admin/kunder", { cache: "no-store" });
        const kropp = await readJsonBody<{ tenants?: { slug?: string | null; name?: string | null }[] }>(svar);
        if (avbruten) return;
        if (!svar.ok || !kropp?.tenants) {
          setFel(true);
          return;
        }
        setKunder(kropp.tenants.filter((t): t is Kund => Boolean(t.slug && t.name)).map((t) => ({ slug: t.slug, name: t.name })));
      } catch {
        if (!avbruten) setFel(true);
      }
    })();
    return () => {
      avbruten = true;
    };
  }, [oppen, kunder]);

  const traffar = useMemo(() => {
    const q = sok.trim().toLocaleLowerCase("sv");
    const lista = kunder ?? [];
    return (q ? lista.filter((k) => k.name.toLocaleLowerCase("sv").includes(q) || k.slug.includes(q)) : lista).slice(0, 12);
  }, [kunder, sok]);

  const avbryt = () => {
    if (byter) return;
    setSok("");
    setBytFel(false);
    stang();
  };

  async function valj(kund: Kund) {
    setByter(kund.slug);
    setBytFel(false);
    const bytt = await bytVy(`kund:${kund.slug}`).catch(() => false);
    // Lyckat byte laddar om sidan. Annars står dialogen kvar med beskedet.
    if (!bytt) {
      setByter(null);
      setBytFel(true);
    }
  }

  const status = byter
    ? text({ sv: "Öppnar kundens arbetsyta.", en: "Opening the customer's workspace." })
    : bytFel
      ? text({ sv: "Kunden gick inte att öppna. Försök igen.", en: "The customer could not be opened. Try again." })
      : kunder && traffar.length === 0
        ? text({ sv: "Ingen kund matchade.", en: "No customer matched." })
        : kunder
          ? traffar.length === 1
            ? text({ sv: "1 kund visas.", en: "1 customer shown." })
            : text({ sv: `${traffar.length} kunder visas.`, en: `${traffar.length} customers shown.` })
          : "";

  return (
    <Dialog isOpen={oppen} onOpenChange={(o) => !o && avbryt()} width={480}>
      <Layout
        header={
          <DialogHeader
            title={text({ sv: "Byt kund", en: "Switch customer" })}
            subtitle={text({
              sv: "Öppna en kunds arbetsyta. Allt du kör där är test, och besöket loggas.",
              en: "Open a customer's workspace. Everything you run there is a test, and the visit is logged."
            })}
            onOpenChange={(o) => !o && avbryt()}
          />
        }
        content={
          <LayoutContent>
            <div className="flex flex-col gap-3">
              <TextInput
                type="search"
                label={text({ sv: "Sök kund eller slug", en: "Search customer or slug" })}
                isLabelHidden
                placeholder={text({ sv: "Sök kund eller slug", en: "Search customer or slug" })}
                startIcon="search"
                hasClear
                value={sok}
                onChange={(v) => setSok(v)}
                width="100%"
                controlClassName="crm-sokfalt"
                hasAutoFocus
                isDisabled={Boolean(byter)}
              />
              {fel ? (
                <p className="text-[0.875rem] text-danger">{text({ sv: "Kundlistan gick inte att hämta.", en: "The customer list could not be loaded." })}</p>
              ) : kunder === null ? (
                <div role="status" aria-label={text({ sv: "Hämtar kunderna", en: "Loading the customers" })} className="flex flex-col gap-3 py-2">
                  {[0, 1, 2, 3].map((i) => (
                    <Skeleton key={i} width={`${72 - i * 9}%`} height={12} radius="rounded" index={i} />
                  ))}
                </div>
              ) : traffar.length ? (
                <div className="-mx-2 max-h-[22rem] overflow-y-auto">
                  <List hasDividers density="balanced">
                    {traffar.map((k) => (
                      <ListItem
                        key={k.slug}
                        label={k.name}
                        description={k.slug}
                        isSelected={impersonation?.slug === k.slug}
                        isDisabled={Boolean(byter) && byter !== k.slug}
                        endContent={byter === k.slug ? <Spinner size="sm" label={text({ sv: "Öppnar", en: "Opening" })} /> : undefined}
                        onClick={() => void valj(k)}
                      />
                    ))}
                  </List>
                </div>
              ) : null}
              <p role="status" className={bytFel ? "text-[0.875rem] text-danger" : "text-[0.8125rem] text-ink-muted"}>
                {status}
              </p>
            </div>
          </LayoutContent>
        }
        footer={
          <LayoutFooter>
            <HStack justify="end" gap={2}>
              <Button label={text({ sv: "Stäng", en: "Close" })} variant="ghost" onClick={avbryt} isDisabled={Boolean(byter)} />
            </HStack>
          </LayoutFooter>
        }
      />
    </Dialog>
  );
}

const KONTAKT: Localized = {
  sv: "Vi bygger och driftar agenterna. Gäller din fråga en beställning eller ett ärende hos företaget du chattar med, skriv det i chatten i stället. De svarar snabbare på sitt eget.",
  en: "We build and operate the agent. If your question concerns an order or a case with the company you are chatting with, write it in the chat instead. They answer faster on their own matters."
};

/** Samma fem punkter som dagens meny (components/snajp/AgentMenu.tsx). */
const DATASKYDD: { sv: string[]; en: string[] } = {
  sv: [
    "Det du skriver i chatten behandlas för att kunna besvara ditt ärende, och för inget annat.",
    "Personuppgiftsansvarig är företaget du chattar med. Snajp är personuppgiftsbiträde och behandlar uppgifterna på deras uppdrag.",
    "Skriv inte personnummer, kortuppgifter eller uppgifter om hälsa i chatten. Behövs sådant för ditt ärende ber vi om det på ett säkrare sätt.",
    "Du har rätt att begära utdrag, rättelse eller radering av dina uppgifter, och att invända mot behandlingen.",
    "Vill du utöva någon av de rättigheterna, kontakta i första hand företaget du chattar med."
  ],
  en: [
    "What you write in the chat is processed in order to answer your case, and for nothing else.",
    "The company you are chatting with is the data controller. Snajp is a data processor acting on their instructions.",
    "Do not write national ID numbers, card details or health information in the chat. If your case needs any of that, we will ask for it in a safer way.",
    "You have the right to request access, rectification or erasure of your data, and to object to the processing.",
    "To exercise any of those rights, contact the company you are chatting with in the first instance."
  ]
};

/** Kontakt och Dataskydd (SK-067): samma innehåll som dagens meny, i en dialog. */
function OmSnajpDialog({ slag, stang }: Readonly<{ slag: "kontakt" | "dataskydd" | null; stang: () => void }>) {
  const { text, locale } = useLocale();
  const titel = slag === "dataskydd" ? text({ sv: "Så hanterar vi dina uppgifter", en: "How we handle your data" }) : text({ sv: "Kontakt", en: "Contact" });
  const epost = (
    <a href={`mailto:${SNAJP_SUPPORT_EPOST}`} className="font-medium text-warning underline underline-offset-4">
      {SNAJP_SUPPORT_EPOST}
    </a>
  );
  return (
    <Dialog isOpen={slag !== null} onOpenChange={(o) => !o && stang()} width={520}>
      <Layout
        header={<DialogHeader title={titel} onOpenChange={(o) => !o && stang()} />}
        content={
          <LayoutContent>
            {slag === "dataskydd" ? (
              <div className="flex flex-col gap-3 text-[0.9375rem] leading-relaxed text-ink2">
                <ul className="flex list-disc flex-col gap-2 pl-5 marker:text-ink-muted">
                  {DATASKYDD[locale].map((punkt) => (
                    <li key={punkt}>{punkt}</li>
                  ))}
                </ul>
                <p>
                  {text({ sv: "Frågor om hur Snajp behandlar uppgifter besvaras på ", en: "Questions about how Snajp processes data are answered at " })}
                  {epost}.
                </p>
              </div>
            ) : (
              <div className="flex flex-col gap-3 text-[0.9375rem] leading-relaxed text-ink2">
                <p>{text(KONTAKT)}</p>
                <p>{epost}</p>
              </div>
            )}
          </LayoutContent>
        }
        footer={
          <LayoutFooter>
            <HStack justify="end" gap={2}>
              <Button label={text({ sv: "Stäng", en: "Close" })} variant="ghost" onClick={stang} />
            </HStack>
          </LayoutFooter>
        }
      />
    </Dialog>
  );
}
