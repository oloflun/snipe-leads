"use client";

import { ExternalLink, Link2, Loader2, Mail, Trash2 } from "lucide-react";
import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { useArbetsvag } from "@/components/AppShell";
import { useDashboard } from "@/components/dashboard/DashboardContext";
import { KONTAKT_MEJL, mejlaOss } from "@/components/marketing/copy";
import { Rad, Radlista, btnLiten, btnPrimary, btnSecondary } from "@/components/ui";
import { readJsonBody } from "@/lib/http/json";
import { cn } from "@/lib/utils";
import { useLocale, type Localized } from "@/lib/i18n";

/**
 * Inställningar → Inkorgar. Självbetjäning sedan 2026-09-21.
 *
 * ## Vad som ändrades och varför
 *
 * Sidan sa förut "vi kopplar er inkorg åt er": raden lades in för hand och
 * app-lösenordet som miljövariabel (IMAP_PASSWORD_<SLUG>). Det skalar inte
 * till kunder som skapar konto själva — beslutet 2026-09-21 är att kunden
 * kopplar sin egen Gmail/Outlook/iCloud här, med kontots adress förifylld.
 *
 * ## Lösenordet
 *
 * Ett APP-lösenord (inte kontolösenordet — Gmail och iCloud vägrar vanliga
 * lösenord över IMAP). Det provas mot mejlservern innan något sparas, och
 * lagras sedan Fernet-krypterat i backenden (migration 077) — aldrig i
 * klartext och aldrig i den här klientens state längre än inskickningen.
 * Miljövariabelvägen finns kvar för kopplingar vi förvaltar åt kunder.
 *
 * ## Guiden i tre steg (2026-09-29)
 *
 * Adress → app-lösenord → koppla. Leverantören upptäcks av backenden
 * (`/inbox/mailboxes/upptack`: fri domän ur tabellen, egen domän ur
 * MX-posten), så steg 2 visar exakt var lösenordet skapas. Efter kopplingen
 * körs en första synk direkt; därefter hämtar pollern nya mail själv.
 */

type Inkorg = {
  id: string | null;
  address: string | null;
  provider: string | null;
  status: string | null;
  host: string | null;
  last_sync_at: string | null;
  last_error: string | null;
  kan_synka: boolean;
};

type Svar = {
  mailboxes: Inkorg[];
  kan_synka: boolean;
};

type Guide = "google" | "microsoft" | "apple" | "annan";

type Upptackt = {
  provider: string | null;
  host: string | null;
  leverantor: string | null;
  guide: Guide;
};

const EPOST = /^[^@\s]+@[^@\s]+\.[^@\s]+$/;

/** Var app-lösenordet skapas, per leverantör — sidan kunden faktiskt behöver. */
const LOSENORDSGUIDE: Record<Guide, { lank?: { href: string; text: Localized }; steg: Localized[]; not?: Localized }> = {
  google: {
    lank: { href: "https://myaccount.google.com/apppasswords", text: { sv: "Google-kontot", en: "Google Account" } },
    steg: [
      {
        sv: "Logga in med kontot som tar emot kundmailen.",
        en: "Sign in with the account that receives customer email."
      },
      { sv: "Skriv Snajp som namn och tryck Skapa.", en: "Enter Snajp as the name and press Create." },
      { sv: "Kopiera koden på 16 tecken.", en: "Copy the 16-character code." }
    ],
    not: {
      sv: "Syns inte sidan måste tvåstegsverifiering slås på i Google-kontot först.",
      en: "If the page does not show, turn on 2-Step Verification in the Google Account first."
    }
  },
  apple: {
    lank: { href: "https://account.apple.com/account/manage", text: { sv: "Apple-kontot", en: "Apple Account" } },
    steg: [
      {
        sv: "Välj Inloggning och säkerhet → Appspecifika lösenord.",
        en: "Choose Sign-In and Security → App-Specific Passwords."
      },
      { sv: "Skapa ett lösenord med namnet Snajp.", en: "Create a password named Snajp." },
      { sv: "Kopiera lösenordet.", en: "Copy the password." }
    ]
  },
  microsoft: {
    lank: { href: "https://account.microsoft.com/security", text: { sv: "Microsoft-kontot", en: "Microsoft account" } },
    steg: [
      {
        sv: "Välj Avancerade säkerhetsalternativ → Applösenord (kräver tvåstegsverifiering).",
        en: "Choose Advanced security options → App passwords (requires two-step verification)."
      },
      { sv: "Skapa ett applösenord och kopiera det.", en: "Create an app password and copy it." }
    ],
    not: {
      sv: "Microsoft har stängt lösenordsinloggning för många konton, och företagskonton i Microsoft 365 tillåter den oftast inte. Nekas inloggningen i steg 3 hjälper vi er koppla på annat sätt.",
      en: "Microsoft has turned off password sign-in for many accounts, and Microsoft 365 work accounts usually do not allow it. If sign-in is refused in step 3, we will help you connect another way."
    }
  },
  annan: {
    steg: [
      { sv: "Logga in hos er mejlleverantör.", en: "Sign in to your email provider." },
      {
        sv: "Skapa ett app-lösenord för IMAP (heter ibland applösenord eller e-postlösenord), eller använd kontots vanliga lösenord om leverantören tillåter det.",
        en: "Create an app password for IMAP (sometimes called application password or email password), or use the account's regular password if the provider allows it."
      }
    ]
  }
};

const ord = (s: string): Localized => ({ sv: s, en: s });

function nar(varde: string | null): Localized {
  if (!varde) return { sv: "aldrig", en: "never" };
  const stund = new Date(varde);
  if (Number.isNaN(stund.getTime())) return { sv: "okänt", en: "unknown" };
  const minuter = Math.round((Date.now() - stund.getTime()) / 60000);
  if (minuter < 1) return { sv: "nyss", en: "just now" };
  if (minuter < 60) return { sv: `${minuter} min sedan`, en: `${minuter} min ago` };
  const timmar = Math.round(minuter / 60);
  if (timmar < 24) return { sv: `${timmar} h sedan`, en: `${timmar} h ago` };
  const dagar = Math.round(timmar / 24);
  return { sv: `${dagar} dagar sedan`, en: `${dagar} days ago` };
}

export function Inkorgar() {
  const { userEmail, arLasare } = useDashboard();
  const vag = useArbetsvag();
  const { text } = useLocale();
  const [svar, setSvar] = useState<Svar | null>(null);
  const [laddar, setLaddar] = useState(true);
  const [fel, setFel] = useState<Localized | null>(null);

  // Formuläret. Adressen förifylls med kontots e-post — det vanligaste
  // fallet är att supportmejlen går till samma adress kunden loggar in med.
  const [adress, setAdress] = useState("");
  const [losenord, setLosenord] = useState("");
  const [imapVard, setImapVard] = useState("");
  const [skickar, setSkickar] = useState(false);
  const [formFel, setFormFel] = useState<Localized | null>(null);
  const [klart, setKlart] = useState<Localized | null>(null);
  const [kopplarUr, setKopplarUr] = useState<string | null>(null);
  const [upptackt, setUpptackt] = useState<Upptackt | null>(null);
  const [soker, setSoker] = useState(false);

  const hamta = useCallback(async () => {
    setLaddar(true);
    setFel(null);
    try {
      const response = await fetch("/api/snajp-support/inbox/mailboxes", {
        headers: { "Content-Type": "application/json" },
        cache: "no-store"
      });
      const kropp = await readJsonBody<Svar & { error?: string; detail?: string; offline?: boolean }>(
        response
      );
      if (!response.ok || kropp?.offline) {
        throw new Error(
          kropp?.detail ??
            kropp?.error ??
            text({
              sv: `Kunde inte läsa inkorgarna (${response.status}).`,
              en: `Could not read the mailboxes (${response.status}).`
            })
        );
      }
      setSvar({
        mailboxes: kropp?.mailboxes ?? [],
        kan_synka: Boolean(kropp?.kan_synka)
      });
    } catch (caught) {
      setFel(
        caught instanceof Error
          ? ord(caught.message)
          : { sv: "Kunde inte läsa inkorgarna.", en: "Could not read the mailboxes." }
      );
    } finally {
      setLaddar(false);
    }
  }, [text]);

  useEffect(() => {
    void hamta();
  }, [hamta]);

  useEffect(() => {
    // Inte en adress som redan är kopplad — då är förifyllningen en fälla.
    const redanKopplad = svar?.mailboxes.some((m) => m.address === userEmail?.toLowerCase());
    if (userEmail && !adress && svar && !redanKopplad) setAdress(userEmail);
    // Bara förifyllning: kundens egen inmatning ska aldrig skrivas över.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [userEmail, svar]);

  // Vem driver adressens mejl? Frågas efter en kort paus i skrivandet, så
  // att steg 2 kan visa rätt leverantörs lösenordssida. Egen domän slås upp
  // via MX-posten i backenden — kunden ska aldrig behöva veta vad IMAP är.
  useEffect(() => {
    const ren = adress.trim().toLowerCase();
    if (!EPOST.test(ren)) {
      setUpptackt(null);
      setSoker(false);
      return;
    }
    let avbruten = false;
    setSoker(true);
    const timer = setTimeout(async () => {
      try {
        const response = await fetch(
          `/api/snajp-support/inbox/mailboxes/upptack?adress=${encodeURIComponent(ren)}`,
          { cache: "no-store" }
        );
        const kropp = await readJsonBody<Upptackt>(response);
        if (!avbruten) setUpptackt(response.ok && kropp ? kropp : { provider: null, host: null, leverantor: null, guide: "annan" });
      } catch {
        if (!avbruten) setUpptackt({ provider: null, host: null, leverantor: null, guide: "annan" });
      } finally {
        if (!avbruten) setSoker(false);
      }
    }, 450);
    return () => {
      avbruten = true;
      clearTimeout(timer);
    };
  }, [adress]);

  const behoverVard = upptackt !== null && !upptackt.host;
  const guide = upptackt ? LOSENORDSGUIDE[upptackt.guide] : null;

  async function koppla(event: React.FormEvent) {
    event.preventDefault();
    setSkickar(true);
    setFormFel(null);
    setKlart(null);
    try {
      const response = await fetch("/api/snajp-support/inbox/mailboxes", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          address: adress.trim(),
          app_losenord: losenord,
          ...(behoverVard && imapVard.trim() ? { imap_host: imapVard.trim() } : {})
        })
      });
      const kropp = await readJsonBody<{ error?: string; detail?: string; connected?: boolean }>(response);
      if (!response.ok || !kropp?.connected) {
        throw new Error(
          kropp?.detail ??
            kropp?.error ??
            text({ sv: "Kopplingen misslyckades. Försök igen.", en: "Connecting failed. Try again." })
        );
      }
      // Lösenordet har gjort sitt och ska inte ligga kvar i minnet.
      setLosenord("");
      await hamta();
      // Första synken körs direkt — kunden ska inte behöva leta upp en knapp
      // till. Därefter hämtar backendens poller nya mail av sig själv.
      setKlart({ sv: "Inkorgen är kopplad. Hämtar era olästa mail …", en: "The mailbox is connected. Fetching your unread email …" });
      try {
        const synk = await fetch("/api/snajp-support/inbox/sync", {
          method: "POST",
          headers: { "Content-Type": "application/json" }
        });
        const resultat = await readJsonBody<{ fetched?: number; error?: string | null }>(synk);
        setKlart(
          !synk.ok || resultat?.error
            ? {
                sv: "Inkorgen är kopplad. Första hämtningen gick inte igenom just nu, men nya mail hämtas automatiskt.",
                en: "The mailbox is connected. The first fetch did not go through right now, but new email is fetched automatically."
              }
            : resultat?.fetched
              ? {
                  sv: `Inkorgen är kopplad och ${resultat.fetched} olästa mail är hämtade. Agenten sorterar dem nu, och nya mail hämtas automatiskt.`,
                  en: `The mailbox is connected and ${resultat.fetched} unread emails are fetched. The agent is sorting them now, and new email is fetched automatically.`
                }
              : {
                  sv: "Inkorgen är kopplad. Inga olästa mail just nu. Nya mail hämtas automatiskt.",
                  en: "The mailbox is connected. No unread email right now. New email is fetched automatically."
                }
        );
      } catch {
        setKlart({
          sv: "Inkorgen är kopplad. Nya mail hämtas automatiskt.",
          en: "The mailbox is connected. New email is fetched automatically."
        });
      }
      await hamta();
    } catch (caught) {
      setFormFel(
        caught instanceof Error ? ord(caught.message) : { sv: "Kopplingen misslyckades.", en: "Connecting failed." }
      );
    } finally {
      setSkickar(false);
    }
  }

  async function kopplaUr(inkorg: Inkorg) {
    if (!inkorg.id) return;
    setKopplarUr(inkorg.id);
    setFormFel(null);
    setKlart(null);
    try {
      const response = await fetch(`/api/snajp-support/inbox/mailboxes/${inkorg.id}`, {
        method: "DELETE",
        headers: { "Content-Type": "application/json" }
      });
      const kropp = await readJsonBody<{ error?: string; detail?: string }>(response);
      if (!response.ok) {
        throw new Error(
          kropp?.detail ??
            kropp?.error ??
            text({ sv: "Kunde inte koppla ur inkorgen.", en: "Could not disconnect the mailbox." })
        );
      }
      setKlart({
        sv: `${inkorg.address} är urkopplad. Redan hämtade mail ligger kvar som ärenden.`,
        en: `${inkorg.address} is disconnected. Email already fetched stays as tickets.`
      });
      await hamta();
    } catch (caught) {
      setFormFel(
        caught instanceof Error
          ? ord(caught.message)
          : { sv: "Kunde inte koppla ur inkorgen.", en: "Could not disconnect the mailbox." }
      );
    } finally {
      setKopplarUr(null);
    }
  }

  if (laddar && !svar) {
    return <div className="h-28 animate-pulse rounded-card bg-ink/[0.055]" aria-busy="true" />;
  }

  if (fel && !svar) {
    return (
      <p role="alert" className="max-w-[62ch] text-[0.9375rem] leading-6 text-danger">
        {text(fel)}
      </p>
    );
  }

  const inkorgar = svar?.mailboxes ?? [];

  return (
    <div className="grid gap-8">
      {inkorgar.length === 0 ? (
        <div className="rounded-card border border-dashed border-ink/15 bg-paper/45 p-6 text-center">
          <Mail className="mx-auto h-6 w-6 text-mineral" aria-hidden />
          <h2 className="mt-3 text-[1.0625rem] font-semibold">
            {text({ sv: "Ingen inkorg är kopplad ännu", en: "No mailbox is connected yet" })}
          </h2>
          <p className="mx-auto mt-2 max-w-[52ch] text-[0.9375rem] leading-6 text-ink-muted">
            {text({
              sv: "Koppla er Gmail, Outlook eller iCloud här nedanför, så hämtar agenten era olästa kundmail automatiskt.",
              en: "Connect your Gmail, Outlook or iCloud below and the agent fetches your unread customer email automatically."
            })}
          </p>
        </div>
      ) : (
        <Radlista ariaLabel={text({ sv: "Kopplade inkorgar", en: "Connected mailboxes" })}>
          {/* Fast schema per rad: adress i vänsterspalten, status alltid längst
              till höger på samma plats. Metaraden och ett eventuellt fel spänner
              över båda spalterna. */}
          {inkorgar.map((inkorg) => (
            <Rad
              key={inkorg.id ?? inkorg.address ?? "-"}
              className="grid grid-cols-[minmax(0,1fr)_auto] items-baseline gap-x-4 gap-y-1"
            >
              <span className="min-w-0 break-words text-[0.9375rem] font-semibold">
                {inkorg.address ?? "—"}
              </span>
              <span
                className={cn(
                  "kicker justify-self-end",
                  inkorg.kan_synka ? "text-moss" : "text-mineral"
                )}
              >
                {inkorg.kan_synka ? text({ sv: "kopplad", en: "connected" }) : text({ sv: "väntar på koppling", en: "waiting for connection" })}
              </span>
              <p className="col-span-2 text-[0.875rem] leading-6 text-ink-muted">
                {[inkorg.provider, inkorg.host, text({ sv: `senaste synk ${nar(inkorg.last_sync_at).sv}`, en: `last sync ${nar(inkorg.last_sync_at).en}` })]
                  .filter(Boolean)
                  .join(" · ")}
              </p>
              {inkorg.last_error ? (
                <p className="col-span-2 text-[0.875rem] leading-6 text-danger">
                  {inkorg.last_error}
                </p>
              ) : null}
              {inkorg.id && !arLasare ? (
                <button
                  type="button"
                  onClick={() => void kopplaUr(inkorg)}
                  disabled={kopplarUr !== null}
                  className={cn(btnSecondary, btnLiten, "col-span-2 mt-1 w-fit border border-ink/15 hover:border-ink/30")}
                >
                  {kopplarUr === inkorg.id ? (
                    <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden />
                  ) : (
                    <Trash2 className="h-3.5 w-3.5" aria-hidden />
                  )}
                  {text({ sv: "Koppla ur", en: "Disconnect" })}
                </button>
              ) : null}
            </Rad>
          ))}
        </Radlista>
      )}

      {klart ? (
        <div role="status" className="grid max-w-[62ch] gap-2">
          <p className="text-[0.9375rem] leading-6 text-moss">{text(klart)}</p>
          <Link
            href={vag("/dashboard/support")}
            className="focus-ring w-fit rounded-input text-[0.9375rem] font-medium underline underline-offset-4 hover:text-ochre"
          >
            {text({ sv: "Gå till Kundtjänst", en: "Go to Support" })}
          </Link>
        </div>
      ) : null}

      {arLasare ? null : (
        /* Guide i tre steg, NOT ett fritt formulär: kunden ska aldrig undra
           vad nästa sak att göra är. Steg 2 byter innehåll efter leverantören
           som steg 1 upptäckte. */
        <form onSubmit={(event) => void koppla(event)} className="border-t border-ink/15 pt-6">
          <h2 className="kicker text-mineral">
            {inkorgar.length === 0
              ? text({ sv: "Koppla er inkorg i tre steg", en: "Connect your mailbox in three steps" })
              : text({ sv: "Koppla en inkorg till", en: "Connect another mailbox" })}
          </h2>

          <ol className="mt-4 grid max-w-[560px] divide-y divide-ink/10">
            <Steg nummer={1} rubrik={text({ sv: "Adressen dit kundmailen kommer", en: "The address customer email goes to" })}>
              <input
                type="email"
                aria-label={text({ sv: "E-postadress", en: "Email address" })}
                value={adress}
                onChange={(event) => setAdress(event.target.value)}
                required
                autoComplete="email"
                placeholder={text({ sv: "info@erforetag.se", en: "info@yourcompany.com" })}
                className="focus-ring min-h-11 w-full rounded-input border border-ink/15 bg-paper px-3 text-[16px]"
              />
              <p className="text-[0.875rem] leading-6 text-ink-muted" aria-live="polite">
                {soker ? (
                  text({ sv: "Letar upp er mejlleverantör …", en: "Looking up your email provider …" })
                ) : upptackt?.host ? (
                  <>
                    <strong className="font-semibold text-ink">{upptackt.leverantor}</strong>
                    {text({ sv: ", servern hittades automatiskt.", en: ", the server was found automatically." })}
                  </>
                ) : upptackt ? (
                  text({
                    sv: "Vi känner inte igen leverantören. Ange mejlservern nedan.",
                    en: "We do not recognise the provider. Enter the mail server below."
                  })
                ) : null}
              </p>
              {behoverVard ? (
                <label className="grid gap-1.5">
                  <span className="text-[0.875rem] font-medium">{text({ sv: "IMAP-server", en: "IMAP server" })}</span>
                  <input
                    type="text"
                    value={imapVard}
                    onChange={(event) => setImapVard(event.target.value)}
                    required
                    placeholder={`mail.${adress.split("@")[1] ?? text({ sv: "erforetag.se", en: "yourcompany.com" })}`}
                    className="focus-ring min-h-11 rounded-input border border-ink/15 bg-paper px-3 text-[16px]"
                  />
                  <span className="text-[0.8125rem] leading-5 text-ink-subtle">
                    {text({
                      sv: "Står i er mejlleverantörs inställningar för IMAP, eller",
                      en: "It is in your email provider's IMAP settings, or"
                    })}{" "}
                    <a
                      href={mejlaOss(text({ sv: "Koppla vår inkorg", en: "Connect our mailbox" }))}
                      className="focus-ring rounded-input underline underline-offset-4 hover:text-ochre"
                    >
                      {text({ sv: "skriv till", en: "write to" })} {KONTAKT_MEJL}
                    </a>{" "}
                    {text({ sv: "så hjälper vi till.", en: "and we will help." })}
                  </span>
                </label>
              ) : null}
            </Steg>

            <Steg nummer={2} rubrik={text({ sv: "Skapa ett app-lösenord", en: "Create an app password" })}>
              {guide ? (
                <>
                  {guide.lank ? (
                    <a
                      href={guide.lank.href}
                      target="_blank"
                      rel="noopener noreferrer"
                      className={cn(btnSecondary, btnLiten, "w-fit whitespace-nowrap border border-ink/15 hover:border-ink/30")}
                    >
                      <ExternalLink className="h-3.5 w-3.5" aria-hidden />
                      <span className="sr-only">{text({ sv: "Öppna ", en: "Open " })}</span>
                      {text(guide.lank.text)}
                      <span className="sr-only">{text({ sv: " (ny flik)", en: " (new tab)" })}</span>
                    </a>
                  ) : null}
                  <ol className="grid list-decimal gap-1 pl-5 text-[0.9375rem] leading-6 text-ink-muted">
                    {guide.steg.map((rad) => (
                      <li key={rad.sv}>{text(rad)}</li>
                    ))}
                  </ol>
                  {guide.not ? (
                    <p className="text-[0.8125rem] leading-5 text-ink-subtle">{text(guide.not)}</p>
                  ) : null}
                </>
              ) : (
                <p className="text-[0.9375rem] leading-6 text-ink-muted">
                  {text({
                    sv: "Fyll i adressen först, så visar vi exakt var lösenordet skapas.",
                    en: "Fill in the address first and we show exactly where the password is created."
                  })}
                </p>
              )}
              <p className="text-[0.8125rem] leading-5 text-ink-subtle">
                {text({
                  sv: "App-lösenordet gäller bara för Snajp och kan återkallas när som helst, utan att ert vanliga lösenord ändras.",
                  en: "The app password only works for Snajp and can be revoked at any time, without changing your regular password."
                })}
              </p>
            </Steg>

            <Steg nummer={3} rubrik={text({ sv: "Klistra in och koppla", en: "Paste and connect" })}>
              <input
                type="password"
                aria-label={text({ sv: "App-lösenord", en: "App password" })}
                value={losenord}
                onChange={(event) => setLosenord(event.target.value)}
                required
                minLength={6}
                autoComplete="off"
                placeholder="abcd efgh ijkl mnop"
                className="focus-ring min-h-11 w-full rounded-input border border-ink/15 bg-paper px-3 text-[16px]"
              />
              <p className="text-[0.8125rem] leading-5 text-ink-subtle">
                {text({
                  sv: "Vi provar inloggningen direkt och sparar lösenordet krypterat. Det visas aldrig igen. Olästa mail hämtas direkt och sedan automatiskt, och markeras som lästa i er inkorg när Snajp har tagit emot dem.",
                  en: "We test the sign-in right away and store the password encrypted. It is never shown again. Unread email is fetched right away and then automatically, and marked as read in your mailbox once Snajp has received it."
                })}
              </p>
              {formFel ? (
                <p role="alert" className="text-[0.875rem] leading-6 text-danger">
                  {text(formFel)}
                </p>
              ) : null}
              <button type="submit" disabled={skickar || soker} className={cn(btnPrimary, "w-fit")}>
                {skickar ? (
                  <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
                ) : (
                  <Link2 className="h-4 w-4" aria-hidden />
                )}
                {skickar ? text({ sv: "Provar inloggningen …", en: "Testing the sign-in …" }) : text({ sv: "Koppla inkorgen", en: "Connect mailbox" })}
              </button>
            </Steg>
          </ol>
        </form>
      )}

      <button
        type="button"
        onClick={() => void hamta()}
        className="focus-ring inline-flex min-h-11 w-fit items-center gap-2 rounded-input border border-ink/20 px-4 text-[0.9375rem] font-medium transition-colors hover:border-ink"
      >
        {laddar ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden /> : null}
        {text({ sv: "Uppdatera", en: "Refresh" })}
      </button>
    </div>
  );
}

function Steg({
  nummer,
  rubrik,
  children
}: Readonly<{ nummer: number; rubrik: string; children: React.ReactNode }>) {
  const { text } = useLocale();
  return (
    <li className="grid grid-cols-[1.25rem_minmax(0,1fr)] gap-x-2 py-5 first:pt-0 sm:grid-cols-[2rem_minmax(0,1fr)] sm:gap-x-3">
      <span className="text-[1.25rem] font-semibold leading-7 text-mineral tabular-nums" aria-hidden>
        {nummer}
      </span>
      <div className="grid min-w-0 gap-3">
        <h3 className="text-[1rem] font-semibold leading-7">
          <span className="sr-only">{text({ sv: `Steg ${nummer}: `, en: `Step ${nummer}: ` })}</span>
          {rubrik}
        </h3>
        {children}
      </div>
    </li>
  );
}
