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
const LOSENORDSGUIDE: Record<Guide, { lank?: { href: string; text: string }; steg: string[]; not?: string }> = {
  google: {
    lank: { href: "https://myaccount.google.com/apppasswords", text: "Google-kontot" },
    steg: [
      "Logga in med kontot som tar emot kundmailen.",
      "Skriv Snajp som namn och tryck Skapa.",
      "Kopiera koden på 16 tecken."
    ],
    not: "Syns inte sidan måste tvåstegsverifiering slås på i Google-kontot först."
  },
  apple: {
    lank: { href: "https://account.apple.com/account/manage", text: "Apple-kontot" },
    steg: [
      "Välj Inloggning och säkerhet → Appspecifika lösenord.",
      "Skapa ett lösenord med namnet Snajp.",
      "Kopiera lösenordet."
    ]
  },
  microsoft: {
    lank: { href: "https://account.microsoft.com/security", text: "Microsoft-kontot" },
    steg: [
      "Välj Avancerade säkerhetsalternativ → Applösenord (kräver tvåstegsverifiering).",
      "Skapa ett applösenord och kopiera det."
    ],
    not: "Microsoft har stängt lösenordsinloggning för många konton, och företagskonton i Microsoft 365 tillåter den oftast inte. Nekas inloggningen i steg 3 hjälper vi er koppla på annat sätt."
  },
  annan: {
    steg: [
      "Logga in hos er mejlleverantör.",
      "Skapa ett app-lösenord för IMAP (heter ibland applösenord eller e-postlösenord), eller använd kontots vanliga lösenord om leverantören tillåter det."
    ]
  }
};

function nar(varde: string | null): string {
  if (!varde) return "aldrig";
  const stund = new Date(varde);
  if (Number.isNaN(stund.getTime())) return "okänt";
  const minuter = Math.round((Date.now() - stund.getTime()) / 60000);
  if (minuter < 1) return "nyss";
  if (minuter < 60) return `${minuter} min sedan`;
  const timmar = Math.round(minuter / 60);
  if (timmar < 24) return `${timmar} h sedan`;
  return `${Math.round(timmar / 24)} dagar sedan`;
}

export function Inkorgar() {
  const { userEmail, arLasare } = useDashboard();
  const vag = useArbetsvag();
  const [svar, setSvar] = useState<Svar | null>(null);
  const [laddar, setLaddar] = useState(true);
  const [fel, setFel] = useState<string | null>(null);

  // Formuläret. Adressen förifylls med kontots e-post — det vanligaste
  // fallet är att supportmejlen går till samma adress kunden loggar in med.
  const [adress, setAdress] = useState("");
  const [losenord, setLosenord] = useState("");
  const [imapVard, setImapVard] = useState("");
  const [skickar, setSkickar] = useState(false);
  const [formFel, setFormFel] = useState<string | null>(null);
  const [klart, setKlart] = useState<string | null>(null);
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
        throw new Error(kropp?.detail ?? kropp?.error ?? `Kunde inte läsa inkorgarna (${response.status}).`);
      }
      setSvar({
        mailboxes: kropp?.mailboxes ?? [],
        kan_synka: Boolean(kropp?.kan_synka)
      });
    } catch (caught) {
      setFel(caught instanceof Error ? caught.message : "Kunde inte läsa inkorgarna.");
    } finally {
      setLaddar(false);
    }
  }, []);

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
        throw new Error(kropp?.detail ?? kropp?.error ?? "Kopplingen misslyckades. Försök igen.");
      }
      // Lösenordet har gjort sitt och ska inte ligga kvar i minnet.
      setLosenord("");
      await hamta();
      // Första synken körs direkt — kunden ska inte behöva leta upp en knapp
      // till. Därefter hämtar backendens poller nya mail av sig själv.
      setKlart("Inkorgen är kopplad. Hämtar era olästa mail …");
      try {
        const synk = await fetch("/api/snajp-support/inbox/sync", {
          method: "POST",
          headers: { "Content-Type": "application/json" }
        });
        const resultat = await readJsonBody<{ fetched?: number; error?: string | null }>(synk);
        setKlart(
          !synk.ok || resultat?.error
            ? "Inkorgen är kopplad. Första hämtningen gick inte igenom just nu, men nya mail hämtas automatiskt."
            : resultat?.fetched
              ? `Inkorgen är kopplad och ${resultat.fetched} olästa mail är hämtade. Agenten sorterar dem nu, och nya mail hämtas automatiskt.`
              : "Inkorgen är kopplad. Inga olästa mail just nu. Nya mail hämtas automatiskt."
        );
      } catch {
        setKlart("Inkorgen är kopplad. Nya mail hämtas automatiskt.");
      }
      await hamta();
    } catch (caught) {
      setFormFel(caught instanceof Error ? caught.message : "Kopplingen misslyckades.");
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
        throw new Error(kropp?.detail ?? kropp?.error ?? "Kunde inte koppla ur inkorgen.");
      }
      setKlart(`${inkorg.address} är urkopplad. Redan hämtade mail ligger kvar som ärenden.`);
      await hamta();
    } catch (caught) {
      setFormFel(caught instanceof Error ? caught.message : "Kunde inte koppla ur inkorgen.");
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
        {fel}
      </p>
    );
  }

  const inkorgar = svar?.mailboxes ?? [];

  return (
    <div className="grid gap-8">
      {inkorgar.length === 0 ? (
        <div className="rounded-card border border-dashed border-ink/15 bg-paper/45 p-6 text-center">
          <Mail className="mx-auto h-6 w-6 text-mineral" aria-hidden />
          <h2 className="mt-3 text-[1.0625rem] font-semibold">Ingen inkorg är kopplad ännu</h2>
          <p className="mx-auto mt-2 max-w-[52ch] text-[0.9375rem] leading-6 text-ink-muted">
            Koppla er Gmail, Outlook eller iCloud här nedanför, så hämtar agenten era olästa
            kundmail automatiskt.
          </p>
        </div>
      ) : (
        <Radlista ariaLabel="Kopplade inkorgar">
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
                {inkorg.kan_synka ? "kopplad" : "väntar på koppling"}
              </span>
              <p className="col-span-2 text-[0.875rem] leading-6 text-ink-muted">
                {[inkorg.provider, inkorg.host, `senaste synk ${nar(inkorg.last_sync_at)}`]
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
                  Koppla ur
                </button>
              ) : null}
            </Rad>
          ))}
        </Radlista>
      )}

      {klart ? (
        <div role="status" className="grid max-w-[62ch] gap-2">
          <p className="text-[0.9375rem] leading-6 text-moss">{klart}</p>
          <Link
            href={vag("/dashboard/support")}
            className="focus-ring w-fit rounded-input text-[0.9375rem] font-medium underline underline-offset-4 hover:text-ochre"
          >
            Gå till Kundtjänst
          </Link>
        </div>
      ) : null}

      {arLasare ? null : (
        /* Guide i tre steg, NOT ett fritt formulär: kunden ska aldrig undra
           vad nästa sak att göra är. Steg 2 byter innehåll efter leverantören
           som steg 1 upptäckte. */
        <form onSubmit={(event) => void koppla(event)} className="border-t border-ink/15 pt-6">
          <h2 className="kicker text-mineral">
            {inkorgar.length === 0 ? "Koppla er inkorg i tre steg" : "Koppla en inkorg till"}
          </h2>

          <ol className="mt-4 grid max-w-[560px] divide-y divide-ink/10">
            <Steg nummer={1} rubrik="Adressen dit kundmailen kommer">
              <input
                type="email"
                aria-label="E-postadress"
                value={adress}
                onChange={(event) => setAdress(event.target.value)}
                required
                autoComplete="email"
                placeholder="info@erforetag.se"
                className="focus-ring min-h-11 w-full rounded-input border border-ink/15 bg-paper px-3 text-[16px]"
              />
              <p className="text-[0.875rem] leading-6 text-ink-muted" aria-live="polite">
                {soker ? (
                  "Letar upp er mejlleverantör …"
                ) : upptackt?.host ? (
                  <>
                    <strong className="font-semibold text-ink">{upptackt.leverantor}</strong>, servern
                    hittades automatiskt.
                  </>
                ) : upptackt ? (
                  "Vi känner inte igen leverantören. Ange mejlservern nedan."
                ) : null}
              </p>
              {behoverVard ? (
                <label className="grid gap-1.5">
                  <span className="text-[0.875rem] font-medium">IMAP-server</span>
                  <input
                    type="text"
                    value={imapVard}
                    onChange={(event) => setImapVard(event.target.value)}
                    required
                    placeholder={`mail.${adress.split("@")[1] ?? "erforetag.se"}`}
                    className="focus-ring min-h-11 rounded-input border border-ink/15 bg-paper px-3 text-[16px]"
                  />
                  <span className="text-[0.8125rem] leading-5 text-ink-subtle">
                    Står i er mejlleverantörs inställningar för IMAP, eller{" "}
                    <a
                      href={mejlaOss("Koppla vår inkorg")}
                      className="focus-ring rounded-input underline underline-offset-4 hover:text-ochre"
                    >
                      skriv till {KONTAKT_MEJL}
                    </a>{" "}
                    så hjälper vi till.
                  </span>
                </label>
              ) : null}
            </Steg>

            <Steg nummer={2} rubrik="Skapa ett app-lösenord">
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
                      <span className="sr-only">Öppna </span>
                      {guide.lank.text}
                      <span className="sr-only"> (ny flik)</span>
                    </a>
                  ) : null}
                  <ol className="grid list-decimal gap-1 pl-5 text-[0.9375rem] leading-6 text-ink-muted">
                    {guide.steg.map((rad) => (
                      <li key={rad}>{rad}</li>
                    ))}
                  </ol>
                  {guide.not ? (
                    <p className="text-[0.8125rem] leading-5 text-ink-subtle">{guide.not}</p>
                  ) : null}
                </>
              ) : (
                <p className="text-[0.9375rem] leading-6 text-ink-muted">
                  Fyll i adressen först, så visar vi exakt var lösenordet skapas.
                </p>
              )}
              <p className="text-[0.8125rem] leading-5 text-ink-subtle">
                App-lösenordet gäller bara för Snajp och kan återkallas när som helst, utan att
                ert vanliga lösenord ändras.
              </p>
            </Steg>

            <Steg nummer={3} rubrik="Klistra in och koppla">
              <input
                type="password"
                aria-label="App-lösenord"
                value={losenord}
                onChange={(event) => setLosenord(event.target.value)}
                required
                minLength={6}
                autoComplete="off"
                placeholder="abcd efgh ijkl mnop"
                className="focus-ring min-h-11 w-full rounded-input border border-ink/15 bg-paper px-3 text-[16px]"
              />
              <p className="text-[0.8125rem] leading-5 text-ink-subtle">
                Vi provar inloggningen direkt och sparar lösenordet krypterat. Det visas aldrig
                igen. Olästa mail hämtas direkt och sedan automatiskt, och markeras som lästa i
                er inkorg när Snajp har tagit emot dem.
              </p>
              {formFel ? (
                <p role="alert" className="text-[0.875rem] leading-6 text-danger">
                  {formFel}
                </p>
              ) : null}
              <button type="submit" disabled={skickar || soker} className={cn(btnPrimary, "w-fit")}>
                {skickar ? (
                  <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
                ) : (
                  <Link2 className="h-4 w-4" aria-hidden />
                )}
                {skickar ? "Provar inloggningen …" : "Koppla inkorgen"}
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
        Uppdatera
      </button>
    </div>
  );
}

function Steg({
  nummer,
  rubrik,
  children
}: Readonly<{ nummer: number; rubrik: string; children: React.ReactNode }>) {
  return (
    <li className="grid grid-cols-[1.25rem_minmax(0,1fr)] gap-x-2 py-5 first:pt-0 sm:grid-cols-[2rem_minmax(0,1fr)] sm:gap-x-3">
      <span className="text-[1.25rem] font-semibold leading-7 text-mineral tabular-nums" aria-hidden>
        {nummer}
      </span>
      <div className="grid min-w-0 gap-3">
        <h3 className="text-[1rem] font-semibold leading-7">
          <span className="sr-only">Steg {nummer}: </span>
          {rubrik}
        </h3>
        {children}
      </div>
    </li>
  );
}
