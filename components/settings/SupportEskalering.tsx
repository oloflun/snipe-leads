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
  sprak: "kundens" | "svenska";
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

  const ladda = useCallback(async () => {
    setFel(null);
    try {
      const svar = await anropa();
      setData(svar);
      setAmne(svar.amnesomrade ?? "");
    } catch (orsak) {
      setFel(orsak instanceof Error ? orsak.message : "Kunde inte hämta inställningarna.");
    }
  }, [anropa]);

  useEffect(() => {
    void ladda();
  }, [ladda]);

  /**
   * Optimistiskt: väljaren visar det nya värdet direkt i stället för att hoppa
   * tillbaka tills servern svarat, och backar till det sparade om sparningen
   * fallerar — en växel som står kvar på ett värde som aldrig sparades vore
   * värre än en som hoppar.
   */
  async function spara(
    falt: string,
    kropp: Record<string, unknown>,
    lokalt?: (nu: Installningar) => Installningar
  ) {
    const fore = data;
    if (lokalt && fore) setData(lokalt(fore));
    setSparar(falt);
    setFel(null);
    try {
      const svar = await anropa({ method: "PUT", body: JSON.stringify(kropp) });
      setData(svar);
      if (falt === "amnesomrade") setAmne(svar.amnesomrade ?? "");
    } catch (orsak) {
      if (fore) setData(fore);
      setFel(orsak instanceof Error ? orsak.message : "Kunde inte spara.");
    } finally {
      setSparar(null);
    }
  }

  if (data === null) {
    return fel ? (
      <div className="mt-10">
        <p role="alert" className="max-w-[62ch] break-words text-[0.875rem] text-danger">
          {fel}
        </p>
        <button type="button" onClick={() => void ladda()} className={cn(btnSecondary, btnLiten, "mt-3")}>
          Försök igen
        </button>
      </div>
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
        <h2 className="font-display text-[1.25rem]">Ton, språk, faktakontroll och överlämning</h2>
        <p className="mt-1 max-w-[62ch] text-[0.9375rem] leading-6 text-ink/60">
          Hur agenten låter, vilket språk den svarar på, hur strängt svaren kontrolleras mot
          kunskapsbasen, och när en människa tar över. Överlämningen sker i kundens eget chattfönster, och hela
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
              onChange={(e) => {
                const tonlage = e.target.value as Installningar["tonlage"];
                void spara("tonlage", { tonlage }, (nu) => ({ ...nu, tonlage }));
              }}
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
            Svarsspråk
            <span className="mt-0.5 block text-[0.8125rem] leading-5 text-ink/55">
              Skriver kunden på engelska, arabiska eller något annat språk kan agenten svara
              på samma språk — kunskapsbasen kan fortfarande vara på svenska.
            </span>
          </span>
          <span className="flex items-center gap-2 justify-self-end">
            {spinner("sprak")}
            <select
              value={data.sprak}
              disabled={upptagen}
              aria-label="Svarsspråk"
              onChange={(e) => {
                const sprak = e.target.value as Installningar["sprak"];
                void spara("sprak", { sprak }, (nu) => ({ ...nu, sprak }));
              }}
              className={valjarKlass}
            >
              <option value="kundens">Kundens språk</option>
              <option value="svenska">Alltid svenska</option>
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
              onChange={(e) => {
                const faktakontroll = e.target.value as Installningar["faktakontroll"];
                void spara("faktakontroll", { faktakontroll }, (nu) => ({ ...nu, faktakontroll }));
              }}
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
              onChange={(e) => {
                const max_misslyckade = Number(e.target.value);
                void spara("max_misslyckade", { eskalering: { max_misslyckade } }, (nu) => ({
                  ...nu,
                  eskalering: { ...nu.eskalering, max_misslyckade }
                }));
              }}
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
              onChange={(e) => {
                const sentimentgrans = Number(e.target.value);
                void spara("sentimentgrans", { eskalering: { sentimentgrans } }, (nu) => ({
                  ...nu,
                  eskalering: { ...nu.eskalering, sentimentgrans }
                }));
              }}
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
              onChange={(e) => {
                const utanfor_amnet = e.target.value as Installningar["eskalering"]["utanfor_amnet"];
                void spara("utanfor_amnet", { eskalering: { utanfor_amnet } }, (nu) => ({
                  ...nu,
                  eskalering: { ...nu.eskalering, utanfor_amnet }
                }));
              }}
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
        onChange={(nytt) =>
          void spara("frustration_raknas", { eskalering: { frustration_raknas: nytt } }, (nu) => ({
            ...nu,
            eskalering: { ...nu.eskalering, frustration_raknas: nytt }
          }))
        }
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
