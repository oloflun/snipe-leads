"use client";

import { Loader2 } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { Rad, Radlista, btnLiten, btnSecondary } from "@/components/ui";
import { Vaxel } from "@/components/settings/Vaxel";
import { readJsonBody } from "@/lib/http/json";
import { cn } from "@/lib/utils";
import { useLocale, type Localized } from "@/lib/i18n";

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

const TONLAGEN: { varde: Installningar["tonlage"]; etikett: Localized }[] = [
  { varde: "standard", etikett: { sv: "Standard", en: "Standard" } },
  { varde: "formell", etikett: { sv: "Formell", en: "Formal" } },
  { varde: "personlig", etikett: { sv: "Personlig", en: "Personal" } },
  { varde: "kortfattad", etikett: { sv: "Kortfattad", en: "Brief" } }
];

const FAKTAKONTROLL: { varde: Installningar["faktakontroll"]; etikett: Localized; forklaring: Localized }[] = [
  {
    varde: "tillatande",
    etikett: { sv: "Tillåtande", en: "Lenient" },
    forklaring: {
      sv: "Telefonnummer, mejladresser och länkar måste finnas i kunskapsbasen.",
      en: "Phone numbers, email addresses and links must be in the knowledge base."
    }
  },
  {
    varde: "forsiktig",
    etikett: { sv: "Försiktig", en: "Careful" },
    forklaring: {
      sv: "Dessutom siffror: priser, frister, leveranstider.",
      en: "Also figures: prices, deadlines, delivery times."
    }
  },
  {
    varde: "strikt",
    etikett: { sv: "Strikt", en: "Strict" },
    forklaring: {
      sv: "Dessutom löften som gratis, återbetalning eller garanti.",
      en: "Also promises such as free, refund or warranty."
    }
  }
];

const ord = (s: string): Localized => ({ sv: s, en: s });

const SENTIMENTGRANSER = [0, 10, 20, 30, 40, 50, 60];

const valjarKlass = cn(
  "focus-ring min-h-11 rounded-input border border-ink/15 bg-paper px-3 text-[16px]",
  "disabled:cursor-not-allowed disabled:opacity-40"
);

export function SupportEskalering() {
  const { text } = useLocale();
  const [data, setData] = useState<Installningar | null>(null);
  const [amne, setAmne] = useState("");
  const [sparar, setSparar] = useState<string | null>(null);
  const [fel, setFel] = useState<Localized | null>(null);

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
          : (kropp?.error ??
              text({
                sv: `Kunde inte nå inställningarna (${response.status}).`,
                en: `Could not reach the settings (${response.status}).`
              }))
      );
    }
    return kropp;
  }, [text]);

  const ladda = useCallback(async () => {
    setFel(null);
    try {
      const svar = await anropa();
      setData(svar);
      setAmne(svar.amnesomrade ?? "");
    } catch (orsak) {
      setFel(
        orsak instanceof Error
          ? ord(orsak.message)
          : { sv: "Kunde inte hämta inställningarna.", en: "Could not load the settings." }
      );
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
      setFel(orsak instanceof Error ? ord(orsak.message) : { sv: "Kunde inte spara.", en: "Could not save." });
    } finally {
      setSparar(null);
    }
  }

  if (data === null) {
    return fel ? (
      <div className="mt-10">
        <p role="alert" className="max-w-[62ch] break-words text-[0.875rem] text-danger">
          {text(fel)}
        </p>
        <button type="button" onClick={() => void ladda()} className={cn(btnSecondary, btnLiten, "mt-3")}>
          {text({ sv: "Försök igen", en: "Try again" })}
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
    sparar === falt ? <Loader2 className="h-4 w-4 animate-spin text-ink-subtle" aria-hidden /> : null;

  return (
    <div className="mt-12 grid gap-7">
      <div>
        <h2 className="font-display text-[1.25rem]">
          {text({ sv: "Ton, språk, faktakontroll och överlämning", en: "Tone, language, fact check and handover" })}
        </h2>
      </div>

      <Radlista ariaLabel={text({ sv: "Ton och faktakontroll", en: "Tone and fact check" })}>
        <Rad className="grid grid-cols-[minmax(0,1fr)_auto] items-center gap-x-6">
          <span className="min-w-0 text-[0.9375rem]">{text({ sv: "Tonläge", en: "Tone" })}</span>
          <span className="flex items-center gap-2 justify-self-end">
            {spinner("tonlage")}
            <select
              value={data.tonlage}
              disabled={upptagen}
              aria-label={text({ sv: "Tonläge", en: "Tone" })}
              onChange={(e) => {
                const tonlage = e.target.value as Installningar["tonlage"];
                void spara("tonlage", { tonlage }, (nu) => ({ ...nu, tonlage }));
              }}
              className={valjarKlass}
            >
              {TONLAGEN.map((t) => (
                <option key={t.varde} value={t.varde}>
                  {text(t.etikett)}
                </option>
              ))}
            </select>
          </span>
        </Rad>
        <Rad className="grid grid-cols-[minmax(0,1fr)_auto] items-center gap-x-6">
          <span className="min-w-0 text-[0.9375rem]">{text({ sv: "Svarsspråk", en: "Reply language" })}</span>
          <span className="flex items-center gap-2 justify-self-end">
            {spinner("sprak")}
            <select
              value={data.sprak}
              disabled={upptagen}
              aria-label={text({ sv: "Svarsspråk", en: "Reply language" })}
              onChange={(e) => {
                const sprak = e.target.value as Installningar["sprak"];
                void spara("sprak", { sprak }, (nu) => ({ ...nu, sprak }));
              }}
              className={valjarKlass}
            >
              <option value="kundens">{text({ sv: "Kundens språk", en: "Customer's language" })}</option>
              <option value="svenska">{text({ sv: "Alltid svenska", en: "Always Swedish" })}</option>
            </select>
          </span>
        </Rad>
        <Rad className="grid grid-cols-[minmax(0,1fr)_auto] items-center gap-x-6">
          <span className="min-w-0 text-[0.9375rem]">
            {text({ sv: "Faktakontroll", en: "Fact check" })}
            <span className="mt-0.5 block text-[0.8125rem] leading-5 text-ink-muted">
              {text(FAKTAKONTROLL.find((f) => f.varde === data.faktakontroll)?.forklaring ?? { sv: "", en: "" })}
            </span>
          </span>
          <span className="flex items-center gap-2 justify-self-end">
            {spinner("faktakontroll")}
            <select
              value={data.faktakontroll}
              disabled={upptagen}
              aria-label={text({ sv: "Faktakontroll", en: "Fact check" })}
              onChange={(e) => {
                const faktakontroll = e.target.value as Installningar["faktakontroll"];
                void spara("faktakontroll", { faktakontroll }, (nu) => ({ ...nu, faktakontroll }));
              }}
              className={valjarKlass}
            >
              {FAKTAKONTROLL.map((f) => (
                <option key={f.varde} value={f.varde}>
                  {text(f.etikett)}
                </option>
              ))}
            </select>
          </span>
        </Rad>
      </Radlista>

      <Radlista ariaLabel={text({ sv: "När en människa tar över", en: "When a person takes over" })}>
        <Rad className="grid grid-cols-[minmax(0,1fr)_auto] items-center gap-x-6">
          <span className="min-w-0 text-[0.9375rem]">
            {text({ sv: "Misslyckade försök innan överlämning", en: "Failed attempts before handover" })}
            <span className="mt-0.5 block text-[0.8125rem] leading-5 text-ink-muted">
              {text({
                sv: "Motfrågor i följd, eller gånger kunden säger att svaret missade.",
                en: "Follow-up questions in a row, or times the customer says the answer missed."
              })}
            </span>
          </span>
          <span className="flex items-center gap-2 justify-self-end">
            {spinner("max_misslyckade")}
            <select
              value={esk.max_misslyckade}
              disabled={upptagen}
              aria-label={text({ sv: "Misslyckade försök innan överlämning", en: "Failed attempts before handover" })}
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
            {text({ sv: "Lämna över vid missnöje under", en: "Hand over when satisfaction drops below" })}
            <span className="mt-0.5 block text-[0.8125rem] leading-5 text-ink-muted">
              {text({ sv: "Hur negativ kundens ton får vara.", en: "How negative the customer's tone may get." })}
            </span>
          </span>
          <span className="flex items-center gap-2 justify-self-end">
            {spinner("sentimentgrans")}
            <select
              value={esk.sentimentgrans}
              disabled={upptagen}
              aria-label={text({ sv: "Gräns för missnöje", en: "Dissatisfaction threshold" })}
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
          <span className="min-w-0 text-[0.9375rem]">{text({ sv: "Frågor utanför ämnesområdet", en: "Questions outside the scope" })}</span>
          <span className="flex items-center gap-2 justify-self-end">
            {spinner("utanfor_amnet")}
            <select
              value={esk.utanfor_amnet}
              disabled={upptagen}
              aria-label={text({ sv: "Frågor utanför ämnesområdet", en: "Questions outside the scope" })}
              onChange={(e) => {
                const utanfor_amnet = e.target.value as Installningar["eskalering"]["utanfor_amnet"];
                void spara("utanfor_amnet", { eskalering: { utanfor_amnet } }, (nu) => ({
                  ...nu,
                  eskalering: { ...nu.eskalering, utanfor_amnet }
                }));
              }}
              className={valjarKlass}
            >
              <option value="erbjud">{text({ sv: "Erbjud en människa", en: "Offer a person" })}</option>
              <option value="eskalera">{text({ sv: "Lämna över direkt", en: "Hand over right away" })}</option>
            </select>
          </span>
        </Rad>
      </Radlista>

      <Vaxel
        etikett={text({ sv: "Räkna frustration som ett misslyckat försök", en: "Count frustration as a failed attempt" })}
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
          {text({ sv: "Vad agenten ska hjälpa till med", en: "What the agent should help with" })}
        </label>
        <p className="mt-1 text-[0.875rem] leading-6 text-ink-muted">
          {text({ sv: "Tomt: agenten utgår från kunskapsbasen.", en: "Empty: the agent works from the knowledge base." })}
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
            {text({ sv: "Spara", en: "Save" })}
          </button>
          <span className="text-[0.8125rem] num text-ink-subtle">
            {amne.length} / {tak}
          </span>
        </div>
      </div>

      {fel ? (
        <p role="alert" className="max-w-[62ch] break-words text-[0.875rem] text-danger">
          {text(fel)}
        </p>
      ) : null}
    </div>
  );
}
