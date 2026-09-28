"use client";

import { Link2, Loader2, Mail, Trash2 } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
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
  global_konfigurerad: boolean;
  kan_synka: boolean;
};

//: Domäner formuläret själv känner igen — samma lista som backendens
//: DOMAN_TILL_IMAP (app/email_pipeline/poller.py). Övriga adresser får ett
//: extra fält för IMAP-värden i stället för ett bakslag efter inskick.
const KANDA_DOMANER = [
  "gmail.com", "googlemail.com",
  "outlook.com", "hotmail.com", "hotmail.se", "live.com", "live.se", "msn.com",
  "icloud.com", "me.com", "mac.com"
];

function domanFor(adress: string): string {
  return adress.split("@")[1]?.trim().toLowerCase() ?? "";
}

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

/** Var app-lösenordet skapas, per leverantör — länken kunden faktiskt behöver. */
function losenordshjalp(doman: string): string {
  if (["gmail.com", "googlemail.com"].includes(doman)) {
    return "Skapa app-lösenordet på myaccount.google.com → Säkerhet → Applösenord (kräver tvåstegsverifiering).";
  }
  if (["icloud.com", "me.com", "mac.com"].includes(doman)) {
    return "Skapa app-lösenordet på account.apple.com → Inloggning och säkerhet → Appspecifika lösenord.";
  }
  if (doman) {
    return "Outlook/Hotmail: använd ditt vanliga lösenord, eller ett app-lösenord om kontot har tvåstegsverifiering.";
  }
  return "";
}

export function Inkorgar() {
  const { userEmail, arLasare } = useDashboard();
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
        global_konfigurerad: Boolean(kropp?.global_konfigurerad),
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
    if (userEmail && !adress) setAdress(userEmail);
    // Bara förifyllning: kundens egen inmatning ska aldrig skrivas över.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [userEmail]);

  const doman = domanFor(adress);
  const behoverVard = Boolean(doman) && !KANDA_DOMANER.includes(doman);

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
      setKlart("Inkorgen är kopplad! Tryck på Synka inkorg i Kundtjänst så hämtas era olästa mail.");
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
            kundmail när ni trycker Synka inkorg.
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
        <p role="status" className="max-w-[62ch] text-[0.9375rem] leading-6 text-moss">
          {klart}
        </p>
      ) : null}

      {arLasare ? null : (
        <form onSubmit={(event) => void koppla(event)} className="border-t border-ink/15 pt-6">
          <h2 className="kicker text-mineral">
            {inkorgar.length === 0 ? "Koppla er inkorg" : "Koppla en inkorg till"}
          </h2>
          <p className="mt-3 max-w-[58ch] text-[0.9375rem] leading-6 text-ink-muted">
            Ange adressen dit kundmailen kommer och ett app-lösenord. Vi provar inloggningen
            direkt och sparar lösenordet krypterat — det visas aldrig igen.
          </p>

          <div className="mt-4 grid max-w-[420px] gap-4">
            <label className="grid gap-1.5">
              <span className="text-[0.875rem] font-medium">E-postadress</span>
              <input
                type="email"
                value={adress}
                onChange={(event) => setAdress(event.target.value)}
                required
                autoComplete="email"
                placeholder="er.adress@gmail.com"
                className="focus-ring min-h-11 rounded-input border border-ink/15 bg-paper px-3 text-[16px]"
              />
            </label>

            <label className="grid gap-1.5">
              <span className="text-[0.875rem] font-medium">App-lösenord</span>
              <input
                type="password"
                value={losenord}
                onChange={(event) => setLosenord(event.target.value)}
                required
                minLength={6}
                autoComplete="off"
                placeholder="abcd efgh ijkl mnop"
                className="focus-ring min-h-11 rounded-input border border-ink/15 bg-paper px-3 text-[16px]"
              />
              {losenordshjalp(doman) ? (
                <span className="text-[0.8125rem] leading-5 text-ink-subtle">
                  {losenordshjalp(doman)}
                </span>
              ) : null}
            </label>

            {behoverVard ? (
              <label className="grid gap-1.5">
                <span className="text-[0.875rem] font-medium">IMAP-server</span>
                <input
                  type="text"
                  value={imapVard}
                  onChange={(event) => setImapVard(event.target.value)}
                  required
                  placeholder={`mail.${doman}`}
                  className="focus-ring min-h-11 rounded-input border border-ink/15 bg-paper px-3 text-[16px]"
                />
                <span className="text-[0.8125rem] leading-5 text-ink-subtle">
                  Adressen har en egen domän — ange mejlservern (står hos er mejlleverantör),
                  eller{" "}
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

            {formFel ? (
              <p role="alert" className="text-[0.875rem] leading-6 text-danger">
                {formFel}
              </p>
            ) : null}

            <button type="submit" disabled={skickar} className={cn(btnPrimary, "w-fit")}>
              {skickar ? (
                <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
              ) : (
                <Link2 className="h-4 w-4" aria-hidden />
              )}
              {skickar ? "Provar inloggningen …" : "Koppla inkorgen"}
            </button>
          </div>
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
