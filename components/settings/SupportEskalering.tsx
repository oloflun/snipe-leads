"use client";

import { Loader2 } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { Rad, Radlista, Sektion, btnSecondary, meta, rubrikPanel } from "@/components/ui";
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
 *
 * Etiketterna är riktiga <label htmlFor>. Väljarna bar tidigare egna
 * aria-label, och "Gräns för missnöje" stod där den synliga texten var
 * "Lämna över vid missnöje under": det hörda namnet ska innehålla det synliga.
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

/**
 * Radformen, samma som i resten av inställningarna: etikett och ev. en mening
 * hjälp till vänster, kontrollen till höger. Under sm staplas de, annars
 * pressade en bred väljare hjälptexten till en smal spalt.
 */
const rad = "grid gap-x-6 gap-y-3 sm:grid-cols-[minmax(0,1fr)_auto] sm:items-center";
const hjalp = "mt-1 block max-w-[62ch] text-[0.9375rem] leading-6 text-ink-muted";
const kontroll = "flex items-center gap-2 sm:justify-self-end";

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
      <div className="mt-12">
        <p role="alert" className="max-w-[62ch] break-words text-[0.9375rem] text-danger">
          {fel}
        </p>
        <button type="button" onClick={() => void ladda()} className={cn(btnSecondary, "mt-3")}>
          Försök igen
        </button>
      </div>
    ) : (
      <div className="mt-12 grid gap-3" aria-busy="true">
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
    sparar === falt ? <Loader2 className="h-4 w-4 animate-spin text-ink-subtle" aria-hidden /> : null;

  return (
    // Tre grupper i stället för en lista med ingress. Frustrationsväxeln står
    // direkt under gränsen den räknar mot ("gränsen ovan" pekade tidigare på
    // raden om ämnesområdet), och frågan om vad som händer utanför ämnet står
    // bredvid fältet som definierar ämnet.
    <div className="mt-12">
      <Sektion title="Ton och faktakontroll">
        <Radlista ariaLabel="Ton och faktakontroll">
          <Rad className={rad}>
            <label htmlFor="eskalering-tonlage" className={rubrikPanel}>
              Tonläge
            </label>
            <span className={kontroll}>
              {spinner("tonlage")}
              <select
                id="eskalering-tonlage"
                value={data.tonlage}
                disabled={upptagen}
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
          <Rad className={rad}>
            <span className="min-w-0">
              <label htmlFor="eskalering-sprak" className={cn(rubrikPanel, "block")}>
                Svarsspråk
              </label>
              <span id="eskalering-sprak-hjalp" className={hjalp}>
                Skriver kunden på engelska, arabiska eller något annat språk kan agenten svara på
                samma språk, även om kunskapsbasen är på svenska.
              </span>
            </span>
            <span className={kontroll}>
              {spinner("sprak")}
              <select
                id="eskalering-sprak"
                aria-describedby="eskalering-sprak-hjalp"
                value={data.sprak}
                disabled={upptagen}
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
          <Rad className={rad}>
            <span className="min-w-0">
              <label htmlFor="eskalering-faktakontroll" className={cn(rubrikPanel, "block")}>
                Faktakontroll
              </label>
              <span id="eskalering-faktakontroll-hjalp" className={hjalp}>
                {FAKTAKONTROLL.find((f) => f.varde === data.faktakontroll)?.forklaring}
              </span>
            </span>
            <span className={kontroll}>
              {spinner("faktakontroll")}
              <select
                id="eskalering-faktakontroll"
                aria-describedby="eskalering-faktakontroll-hjalp"
                value={data.faktakontroll}
                disabled={upptagen}
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
      </Sektion>

      <Sektion title="Ämnesområde">
        <Radlista ariaLabel="Ämnesområde">
          <Rad className="grid gap-3">
            <div>
              <label htmlFor="amnesomrade" className={cn(rubrikPanel, "block")}>
                Vad agenten ska hjälpa till med
              </label>
              <p id="amnesomrade-hjalp" className={hjalp}>
                Några meningar om ert område. Lämna tomt så utgår agenten från kunskapsbasen.
              </p>
            </div>
            <textarea
              id="amnesomrade"
              aria-describedby="amnesomrade-hjalp amnesomrade-antal"
              value={amne}
              onChange={(e) => setAmne(e.target.value.slice(0, tak))}
              rows={3}
              maxLength={tak}
              className="focus-ring w-full resize-y rounded-input border border-ink/15 bg-paper px-3 py-2.5 text-[16px] leading-6"
            />
            <div className="flex items-center gap-3">
              <button
                type="button"
                disabled={upptagen || amne === (data.amnesomrade ?? "")}
                onClick={() => void spara("amnesomrade", { amnesomrade: amne })}
                className={btnSecondary}
              >
                {spinner("amnesomrade")}
                Spara
              </button>
              <span id="amnesomrade-antal" className={cn(meta, "num")}>
                {amne.length} / {tak}
              </span>
            </div>
          </Rad>
          <Rad className={rad}>
            <label htmlFor="eskalering-utanfor" className={rubrikPanel}>
              Frågor utanför ämnesområdet
            </label>
            <span className={kontroll}>
              {spinner("utanfor_amnet")}
              <select
                id="eskalering-utanfor"
                value={esk.utanfor_amnet}
                disabled={upptagen}
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
      </Sektion>

      <Sektion title="Överlämning till en människa">
        <Radlista ariaLabel="Överlämning till en människa">
          <Rad className={rad}>
            <span className="min-w-0">
              <label htmlFor="eskalering-forsok" className={cn(rubrikPanel, "block")}>
                Misslyckade försök innan överlämning
              </label>
              <span id="eskalering-forsok-hjalp" className={hjalp}>
                Motfrågor i följd, eller gånger kunden säger att svaret missade.
              </span>
            </span>
            <span className={kontroll}>
              {spinner("max_misslyckade")}
              <select
                id="eskalering-forsok"
                aria-describedby="eskalering-forsok-hjalp"
                value={esk.max_misslyckade}
                disabled={upptagen}
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
          <Rad>
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
          </Rad>
          <Rad className={rad}>
            <span className="min-w-0">
              <label htmlFor="eskalering-missnoje" className={cn(rubrikPanel, "block")}>
                Lämna över vid missnöje under
              </label>
              <span id="eskalering-missnoje-hjalp" className={hjalp}>
                Hur negativ tonen i kundens meddelande får vara innan en människa tar över.
              </span>
            </span>
            <span className={kontroll}>
              {spinner("sentimentgrans")}
              <select
                id="eskalering-missnoje"
                aria-describedby="eskalering-missnoje-hjalp"
                value={esk.sentimentgrans}
                disabled={upptagen}
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
        </Radlista>
      </Sektion>

      {fel ? (
        <p role="alert" className="mt-6 max-w-[62ch] break-words text-[0.9375rem] text-danger">
          {fel}
        </p>
      ) : null}
    </div>
  );
}
