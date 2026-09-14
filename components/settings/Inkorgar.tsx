"use client";

import { Loader2, Mail } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { KONTAKT_MEJL, mejlaOss } from "@/components/marketing/copy";
import { readJsonBody } from "@/lib/http/json";
import { cn } from "@/lib/utils";

/**
 * Inställningar → Inkorgar.
 *
 * ## Vad som stod här förut
 *
 * Två påhittade rader: "sales@snajp-demo.se · healthy · 96 skick per dag" och
 * "elin@kundbolag.se · warming · 34 skick per dag". En betalande kund som
 * öppnade sin egen inställningssida möttes alltså av två adresser som varken
 * var deras eller ens fanns — och sidan gav inget sätt att ta reda på om deras
 * riktiga inkorg var kopplad.
 *
 * Det hänger ihop med felrapporten om knappen "Synka inkorg", som svarade
 * "IMAP är inte konfigurerat (IMAP_HOST/USER/PASSWORD)": produkten hade två
 * ytor om inkorgar, en som ljög och en som talade i miljövariabler, och ingen
 * som svarade på frågan "är min mail kopplad".
 *
 * ## Vad den gör nu
 *
 * Frågar backenden (`GET /api/inbox/mailboxes`) och visar exakt vad den
 * svarar: adress, leverantör, status, senaste synk och senaste fel. Finns
 * ingen inkorg står det, med vägen till att koppla en.
 *
 * ## Varför lösenordet inte går att fylla i här
 *
 * Ett app-lösenord till kundens Gmail eller Outlook är en nyckel till hela
 * deras korrespondens. Det bor i miljön under `IMAP_PASSWORD_<SLUG>` och
 * aldrig i databasen — just för att en läsbehörighet på `ss_mailboxes` inte
 * ska räcka för att läsa kundens mail (se poller.py). Ett formulär här hade
 * betytt att lösenordet passerar webben, servern och en logg på vägen. Därför
 * kopplas inkorgen av oss, och sidan säger det rakt ut i stället för att låtsas
 * att det är självbetjäning.
 */

type Inkorg = {
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
  const [svar, setSvar] = useState<Svar | null>(null);
  const [laddar, setLaddar] = useState(true);
  const [fel, setFel] = useState<string | null>(null);

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

  if (laddar) {
    return <div className="h-28 animate-pulse rounded-card bg-ink/[0.055]" aria-busy="true" />;
  }

  if (fel) {
    return (
      <p role="alert" className="max-w-[62ch] text-[0.9375rem] leading-6 text-danger">
        {fel}
      </p>
    );
  }

  const inkorgar = svar?.mailboxes ?? [];

  return (
    <div className="grid gap-7">
      {inkorgar.length === 0 ? (
        <div className="rounded-card border border-dashed border-ink/15 bg-paper/45 p-8 text-center">
          <Mail className="mx-auto h-6 w-6 text-mineral" aria-hidden />
          <h2 className="mt-4 text-[1.0625rem] font-semibold">Ingen inkorg är kopplad ännu</h2>
          <p className="mx-auto mt-2 max-w-[52ch] text-[0.9375rem] leading-6 text-ink/60">
            Kundtjänstagenterna svarar i chatten redan nu. Ska de läsa och besvara mejl behöver vi
            koppla er Gmail eller Outlook — det gör vi åt er, eftersom kopplingen kräver ett
            app-lösenord som aldrig ska passera ett webbformulär.
          </p>
          <a
            href={mejlaOss("Koppla vår inkorg")}
            className="focus-ring mt-5 inline-flex min-h-11 items-center rounded-input border border-ink/20 px-5 text-[0.9375rem] font-semibold transition-colors hover:border-ink"
          >
            Skriv till {KONTAKT_MEJL}
          </a>
        </div>
      ) : (
        <div className="divide-y divide-ink/10 border-y border-ink/15">
          {inkorgar.map((inkorg) => (
            <div key={inkorg.address ?? Math.random()} className="grid gap-1 py-4">
              <div className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
                <span className="text-[0.9375rem] font-semibold">{inkorg.address ?? "—"}</span>
                <span
                  className={cn(
                    "kicker",
                    inkorg.kan_synka ? "text-moss" : "text-mineral"
                  )}
                >
                  {inkorg.kan_synka ? "kopplad" : "väntar på koppling"}
                </span>
              </div>
              <p className="text-[0.875rem] leading-6 text-ink/60">
                {[inkorg.provider, inkorg.host, `senaste synk ${nar(inkorg.last_sync_at)}`]
                  .filter(Boolean)
                  .join(" · ")}
              </p>
              {inkorg.last_error ? (
                <p className="text-[0.875rem] leading-6 text-danger">{inkorg.last_error}</p>
              ) : null}
            </div>
          ))}
        </div>
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
