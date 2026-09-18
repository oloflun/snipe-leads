"use client";

import { Loader2 } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { Rad, Radlista, btnLiten, btnSecondary } from "@/components/ui";
import { Vaxel } from "@/components/settings/Vaxel";
import { readJsonBody } from "@/lib/http/json";
import { cn } from "@/lib/utils";

/**
 * Kundtjänstagentens ton, faktakontroll och eskaleringsgränser — per kund.
 *
 * Värdena bor i agent_configs.settings (snajp-support/app/agent/
 * support_regler.py) och verkställs i kod av agenten. Standardvärdena är
 * beteendet innan reglerna blev inställbara, så en kund som aldrig öppnar
 * den här panelen märker ingen skillnad. Samma sparmönster som
 * autosvarsreglerna ovanför: en ändrad väljare sparas direkt, fritexten när
 * du trycker Spara.
 */

type Installningar = {
  eskalering: {
    max_misslyckade: number;
    sentimentgrans: number;
    utanfor_amnet: "erbjud" | "eskalera";
    frustration_raknas: boolean;
  };
  tonlage: "standard" | "formell" | "personlig" | "kortfattad";
  faktakontroll: "tillatande" | "forsiktig" | "strikt";
  amnesomrade: string;
  options?: { amnesomrade_tak?: number };
};

const TONLAGEN: { varde: Installningar["tonlage"]; etikett: string }[] = [
  { varde: "standard", etikett: "Standard" },
  { varde: "formell", etikett: "Formell" },
  { varde: "personlig", etikett: "Personlig" },
  { varde: "kortfattad", etikett: "Kortfattad" }
];

const FAKTAKONTROLL: { varde: Installningar["faktakontroll"]; etikett: string; forklaring: string }[] = [
  {
    varde: "tillatande",
    etikett: "Tillåtande",
    forklaring: "Telefonnummer, mejladresser och länkar måste finnas i kunskapsbasen."
  },
  {
    varde: "forsiktig",
    etikett: "Försiktig",
    forklaring: "Dessutom siffror: priser, frister, leveranstider."
  },
  {
    varde: "strikt",
    etikett: "Strikt",
    forklaring: "Dessutom löften som gratis, återbetalning eller garanti."
  }
];

const SENTIMENTGRANSER = [0, 10, 20, 30, 40, 50, 60];

const valjarKlass = cn(
  "focus-ring min-h-11 rounded-input border border-ink/15 bg-paper px-3 text-[16px]",
  "disabled:cursor-not-allowed disabled:opacity-40"
);

export function SupportEskalering() {
  const [data, setData] = useState<Installningar | null>(null);
  const [amne, setAmne] = useState("");
  const [sparar, setSparar] = useState<string | null>(null);
  const [fel, setFel] = useState<string | null>(null);

  const anropa = useCallback(async (init?: RequestInit): Promise<Installningar> => {
    const response = await fetch("/api/snajp-support/support/config", {
      headers: { "Content-Type": "application/json" },
      cache: "no-store",
      ...init
    });
    const kropp = await readJsonBody<Installningar & { error?: string; detail?: string }>(response);
    if (!response.ok || !kropp) {
      throw new Error(
        typeof kropp?.detail === "string"
          ? kropp.detail
          : (kropp?.error ?? `Kunde inte nå inställningarna (${response.status}).`)
      );
    }
    return kropp;
  }, []);

  useEffect(() => {
    void (async () => {
      try {
        const svar = await anropa();
        setData(svar);
        setAmne(svar.amnesomrade ?? "");
      } catch (orsak) {
        setFel(orsak instanceof Error ? orsak.message : "Kunde inte hämta inställningarna.");
      }
    })();
  }, [anropa]);

  async function spara(falt: string, kropp: Record<string, unknown>) {
    setSparar(falt);
    setFel(null);
    try {
      const svar = await anropa({ method: "PUT", body: JSON.stringify(kropp) });
      setData(svar);
      if (falt === "amnesomrade") setAmne(svar.amnesomrade ?? "");
    } catch (orsak) {
      setFel(orsak instanceof Error ? orsak.message : "Kunde inte spara.");
    } finally {
      setSparar(null);
    }
  }

  if (data === null) {
    return fel ? (
      <p role="alert" className="mt-10 max-w-[62ch] text-[0.875rem] text-danger">
        {fel}
      </p>
    ) : (
      <div className="mt-10 grid gap-3" aria-busy="true">
        {Array.from({ length: 4 }).map((_, index) => (
          <div key={index} className="h-14 animate-pulse rounded-card bg-ink/[0.055]" />
        ))}
      </div>
    );
  }

  const tak = data.options?.amnesomrade_tak ?? 600;
  const esk = data.eskalering;
  const upptagen = sparar !== null;
  const spinner = (falt: string) =>
    sparar === falt ? <Loader2 className="h-4 w-4 animate-spin text-ink/40" aria-hidden /> : null;

  return (
    <div className="mt-12 grid gap-7">
      <div>
        <h2 className="font-display text-[1.25rem]">Ton, faktakontroll och överlämning</h2>
        <p className="mt-1 max-w-[62ch] text-[0.9375rem] leading-6 text-ink/60">
          Hur agenten låter, hur strängt svaren kontrolleras mot kunskapsbasen, och när en
          människa tar över. Överlämningen sker i kundens eget chattfönster, och hela
          samtalet följer med.
        </p>
      </div>

      <Radlista ariaLabel="Ton och faktakontroll">
        <Rad className="grid grid-cols-[minmax(0,1fr)_auto] items-center gap-x-6">
          <span className="min-w-0 text-[0.9375rem]">Tonläge</span>
          <span className="flex items-center gap-2 justify-self-end">
            {spinner("tonlage")}
            <select
              value={data.tonlage}
              disabled={upptagen}
              aria-label="Tonläge"
              onChange={(e) => void spara("tonlage", { tonlage: e.target.value })}
              className={valjarKlass}
            >
              {TONLAGEN.map((t) => (
                <option key={t.varde} value={t.varde}>
                  {t.etikett}
                </option>
              ))}
            </select>
          </span>
        </Rad>
        <Rad className="grid grid-cols-[minmax(0,1fr)_auto] items-center gap-x-6">
          <span className="min-w-0 text-[0.9375rem]">
            Faktakontroll
            <span className="mt-0.5 block text-[0.8125rem] leading-5 text-ink/55">
              {FAKTAKONTROLL.find((f) => f.varde === data.faktakontroll)?.forklaring}
            </span>
          </span>
          <span className="flex items-center gap-2 justify-self-end">
            {spinner("faktakontroll")}
            <select
              value={data.faktakontroll}
              disabled={upptagen}
              aria-label="Faktakontroll"
              onChange={(e) => void spara("faktakontroll", { faktakontroll: e.target.value })}
              className={valjarKlass}
            >
              {FAKTAKONTROLL.map((f) => (
                <option key={f.varde} value={f.varde}>
                  {f.etikett}
                </option>
              ))}
            </select>
          </span>
        </Rad>
      </Radlista>

      <Radlista ariaLabel="När en människa tar över">
        <Rad className="grid grid-cols-[minmax(0,1fr)_auto] items-center gap-x-6">
          <span className="min-w-0 text-[0.9375rem]">
            Misslyckade försök innan överlämning
            <span className="mt-0.5 block text-[0.8125rem] leading-5 text-ink/55">
              Motfrågor i följd, eller gånger kunden säger att svaret missade.
            </span>
          </span>
          <span className="flex items-center gap-2 justify-self-end">
            {spinner("max_misslyckade")}
            <select
              value={esk.max_misslyckade}
              disabled={upptagen}
              aria-label="Misslyckade försök innan överlämning"
              onChange={(e) =>
                void spara("max_misslyckade", {
                  eskalering: { max_misslyckade: Number(e.target.value) }
                })
              }
              className={valjarKlass}
            >
              {[0, 1, 2, 3, 4, 5].map((n) => (
                <option key={n} value={n}>
                  {n}
                </option>
              ))}
            </select>
          </span>
        </Rad>
        <Rad className="grid grid-cols-[minmax(0,1fr)_auto] items-center gap-x-6">
          <span className="min-w-0 text-[0.9375rem]">
            Lämna över vid missnöje under
            <span className="mt-0.5 block text-[0.8125rem] leading-5 text-ink/55">
              Hur negativ tonen i kundens meddelande får vara innan en människa tar över.
            </span>
          </span>
          <span className="flex items-center gap-2 justify-self-end">
            {spinner("sentimentgrans")}
            <select
              value={esk.sentimentgrans}
              disabled={upptagen}
              aria-label="Gräns för missnöje"
              onChange={(e) =>
                void spara("sentimentgrans", {
                  eskalering: { sentimentgrans: Number(e.target.value) }
                })
              }
              className={valjarKlass}
            >
              {Array.from(new Set([...SENTIMENTGRANSER, esk.sentimentgrans]))
                .sort((a, b) => a - b)
                .map((n) => (
                  <option key={n} value={n}>
                    {n} %
                  </option>
                ))}
            </select>
          </span>
        </Rad>
        <Rad className="grid grid-cols-[minmax(0,1fr)_auto] items-center gap-x-6">
          <span className="min-w-0 text-[0.9375rem]">Frågor utanför ämnesområdet</span>
          <span className="flex items-center gap-2 justify-self-end">
            {spinner("utanfor_amnet")}
            <select
              value={esk.utanfor_amnet}
              disabled={upptagen}
              aria-label="Frågor utanför ämnesområdet"
              onChange={(e) =>
                void spara("utanfor_amnet", { eskalering: { utanfor_amnet: e.target.value } })
              }
              className={valjarKlass}
            >
              <option value="erbjud">Erbjud en människa</option>
              <option value="eskalera">Lämna över direkt</option>
            </select>
          </span>
        </Rad>
      </Radlista>

      <Vaxel
        etikett="Räkna frustration som ett misslyckat försök"
        beskrivning="Säger kunden att agenten inte förstår, räknas det mot gränsen ovan i stället för att agenten svarar samma sak igen."
        pa={esk.frustration_raknas}
        disabled={upptagen}
        onChange={(nytt) => void spara("frustration_raknas", { eskalering: { frustration_raknas: nytt } })}
      />

      <div>
        <label htmlFor="amnesomrade" className="text-[0.9375rem] font-semibold">
          Vad agenten ska hjälpa till med
        </label>
        <p className="mt-1 max-w-[62ch] text-[0.875rem] leading-6 text-ink/60">
          Några meningar om ert område. Frågor som uppenbart ligger utanför besvaras inte —
          agenten säger det och erbjuder en människa. Lämna tomt för att agenten ska utgå
          från kunskapsbasen.
        </p>
        <textarea
          id="amnesomrade"
          value={amne}
          onChange={(e) => setAmne(e.target.value.slice(0, tak))}
          rows={3}
          maxLength={tak}
          className="focus-ring mt-2 w-full rounded-input border border-ink/15 bg-paper px-3 py-2.5 text-[16px] leading-6"
        />
        <div className="mt-2 flex items-center gap-3">
          <button
            type="button"
            disabled={upptagen || amne === (data.amnesomrade ?? "")}
            onClick={() => void spara("amnesomrade", { amnesomrade: amne })}
            className={cn(btnSecondary, btnLiten)}
          >
            {spinner("amnesomrade")}
            Spara
          </button>
          <span className="text-[0.8125rem] num text-ink/45">
            {amne.length} / {tak}
          </span>
        </div>
      </div>

      {fel ? (
        <p role="alert" className="max-w-[62ch] break-words text-[0.875rem] text-danger">
          {fel}
        </p>
      ) : null}
    </div>
  );
}
