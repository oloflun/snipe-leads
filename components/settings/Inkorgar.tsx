"use client";

import { Loader2 } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { KONTAKT_MEJL, mejlaOss } from "@/components/marketing/copy";
import { Badge, Rad, Radlista, Tomt, btnSecondary, meta } from "@/components/ui";
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
    // Felet får en väg vidare. Uppdatera-knappen nedan renderas inte i det här
    // läget, så utan den här var sidan en återvändsgränd tills man laddade om.
    return (
      <div>
        <p role="alert" className="max-w-[62ch] text-[0.9375rem] leading-6 text-danger">
          {fel}
        </p>
        <button type="button" onClick={() => void hamta()} className={cn(btnSecondary, "mt-3")}>
          Försök igen
        </button>
      </div>
    );
  }

  const inkorgar = svar?.mailboxes ?? [];

  return (
    <div className="grid gap-7">
      {inkorgar.length === 0 ? (
        // Tomt läge i husets form: en mening och handlingen. Ikonen och den
        // streckade ramen gjorde det till ett eget litet kort.
        <Tomt
          action={
            <a href={mejlaOss("Koppla vår inkorg")} className={btnSecondary}>
              Skriv till {KONTAKT_MEJL}
            </a>
          }
        >
          Ingen inkorg är kopplad. Vi kopplar er Gmail eller Outlook åt er, eftersom kopplingen
          kräver ett app-lösenord som aldrig ska skrivas in i ett webbformulär.
        </Tomt>
      ) : (
        <Radlista ariaLabel="Kopplade inkorgar">
          {/* Radens anatomi: adress, metaraden under, status till höger. Ett
              eventuellt fel spänner över båda spalterna. */}
          {inkorgar.map((inkorg) => (
            <Rad
              key={inkorg.address ?? Math.random()}
              className="grid grid-cols-[minmax(0,1fr)_auto] items-baseline gap-x-4 gap-y-1"
            >
              <span className="min-w-0 break-words text-[0.9375rem] font-semibold">
                {inkorg.address ?? "–"}
              </span>
              <span className="justify-self-end">
                <Badge tone={inkorg.kan_synka ? "good" : "neutral"}>
                  {inkorg.kan_synka ? "Kopplad" : "Väntar på koppling"}
                </Badge>
              </span>
              <p className={cn(meta, "col-span-2")}>
                {[inkorg.provider, inkorg.host, `senaste synk ${nar(inkorg.last_sync_at)}`]
                  .filter(Boolean)
                  .join(" · ")}
              </p>
              {inkorg.last_error ? (
                <p className="col-span-2 text-[0.9375rem] leading-6 text-danger">
                  {inkorg.last_error}
                </p>
              ) : null}
            </Rad>
          ))}
        </Radlista>
      )}

      <button
        type="button"
        onClick={() => void hamta()}
        className={cn(btnSecondary, "w-fit")}
      >
        {laddar ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden /> : null}
        Uppdatera
      </button>
    </div>
  );
}
