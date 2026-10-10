"use client";

import { Phone } from "lucide-react";
import { useCallback, useEffect, useId, useState } from "react";
import {
  Badge,
  Cell,
  SkeletonRows,
  Tabell,
  Tomt,
  btnLiten,
  btnPrimary,
  btnSecondary,
  chip,
  chipAktiv,
  chipInaktiv,
  chiplista,
  etikett,
  meta,
  tabellRad
} from "@/components/ui";
import { useSmal } from "@/components/leads/smal";
import { felmeddelande } from "@/lib/http/json";
import { useLocale, type Localized } from "@/lib/i18n";
import { UTFALL_ETIKETT, datumFormat, leadsAnrop, type Samtalsrad, type Utfall } from "@/lib/leads/suite";
import { cn } from "@/lib/utils";

/**
 * Leads › Samtal (Antons beställning 2026-10-07, leadsregel 15 och 17).
 *
 * Två listor över samma arbete, att ringa:
 *   Återkoppling: Iris-leads som fått mejl och har telefon, äldst kontakt först.
 *   Ringlista: bolag med bara telefon och namngiven VD (registrets nummer).
 *
 * "Ringd" fäller ut utfallen. Backenden (app/leads/samtal.py) verkställer dem:
 * avslutande utfall stoppar alla väntande utskick, kontakta inte spärrar
 * adressen, och ej svar/återkom tar fram leadet igen när det är dags. De som
 * ska ringas i dag står överst. Tabell på bred skärm, kort på telefon med
 * numret överst (samma uppdelning som Säljlistan).
 */

type Lista = "aterkoppling" | "ring";

const UTFALL: Utfall[] = ["ej_svar", "aterkom", "ej_intresserad", "kontakta_inte", "mote"];
const AVSLUTANDE: Utfall[] = ["ej_intresserad", "kontakta_inte", "mote"];

const T = {
  aterkoppling: { sv: "Återkoppling", en: "Follow-up calls" },
  ring: { sv: "Ringlista", en: "Call list" },
  idag: { sv: "i dag", en: "today" },
  aterkopplingIntro: {
    sv: "Kontaktade leads med telefonnummer, äldst kontakt först. De som ska ringas i dag står överst.",
    en: "Contacted leads with a phone number, oldest contact first. Today's calls are at the top."
  },
  ringIntro: {
    sv: "Bolag utan mejladress men med telefon och namngiven VD. Numret är bolagets och antas gå till VD.",
    en: "Companies with no email address but a phone number and a named CEO. The number is the company's and is assumed to reach the CEO."
  },
  tomAterkoppling: { sv: "Inga kontaktade leads med telefonnummer just nu.", en: "No contacted leads with a phone number right now." },
  tomRing: { sv: "Ringlistan är tom.", en: "The call list is empty." },
  bolag: { sv: "Bolag", en: "Company" },
  kontakt: { sv: "Kontakt", en: "Contact" },
  telefon: { sv: "Telefon", en: "Phone" },
  kontaktad: { sv: "Kontaktad", en: "Contacted" },
  senast: { sv: "Senaste samtal", en: "Last call" },
  nasta: { sv: "Nästa", en: "Next" },
  handling: { sv: "Handling", en: "Action" },
  ringd: { sv: "Ringd", en: "Called" },
  idagMarke: { sv: "I dag", en: "Today" },
  aldrig: { sv: "Inte ringd", en: "Not called" },
  utfall: { sv: "Utfall", en: "Outcome" },
  aterkomDatum: { sv: "Ring tillbaka", en: "Call back on" },
  anteckning: { sv: "Anteckning", en: "Note" },
  spara: { sv: "Spara", en: "Save" },
  sparar: { sv: "Sparar…", en: "Saving…" },
  avbryt: { sv: "Avbryt", en: "Cancel" },
  valjDatum: { sv: "Välj ett datum för återkom.", en: "Pick a date to call back." },
  listval: { sv: "Samtalslista", en: "Call list" }
} satisfies Record<string, Localized>;

function anstalldaText(rad: Samtalsrad, text: (v: Localized) => string): string | null {
  const n = rad.anstallda;
  if (n == null) return null;
  if (n <= 1) return text({ sv: "1 anställd", en: "1 employee" });
  const vem = rad.contact_name ?? text({ sv: "VD", en: "the CEO" });
  return text({
    sv: `${n} anställda, numret kan gå till någon annan än ${vem}`,
    en: `${n} employees, the number may reach someone other than ${vem}`
  });
}

/** Exempelrader för /demo: samma form som backendens svar, inga riktiga bolag. */
function demoRader(lista: Lista): Samtalsrad[] {
  const bas = {
    ort: "Kungsbacka", website: null, contact_email: null, status: "contacted", antal_samtal: 0,
    senaste_utfall: null, senaste_samtal: null, aterkom_datum: null, nasta: null, ring_idag: true
  } as const;
  return lista === "ring"
    ? [{ ...bas, prospect_id: "demo-r1", company_name: "Exempel Bygg AB", contact_name: "Eva Exempel", contact_role: "VD",
         contact_phone: "031-000 00 01", anstallda: 4, kontaktad: null, status: "new" }]
    : [
        { ...bas, prospect_id: "demo-a1", company_name: "Exempel Måleri AB", contact_name: "Per Exempel", contact_role: "Ägare",
          contact_phone: "031-000 00 02", anstallda: 2, kontaktad: "2026-09-28" },
        { ...bas, prospect_id: "demo-a2", company_name: "Exempel Rör AB", contact_name: null, contact_role: null,
          contact_phone: "031-000 00 03", anstallda: 12, kontaktad: "2026-10-02", antal_samtal: 1,
          senaste_utfall: "ej_svar", senaste_samtal: "2026-10-06T09:00:00+00:00", nasta: "2026-10-08", ring_idag: true }
      ];
}

export function Samtalslista({ demo = false }: Readonly<{ demo?: boolean }>) {
  const { locale, text } = useLocale();
  const smal = useSmal();
  const [lista, setLista] = useState<Lista>("aterkoppling");
  const [rader, setRader] = useState<Record<Lista, Samtalsrad[] | null>>({ aterkoppling: null, ring: null });
  const [fel, setFel] = useState<string | null>(null);
  const [oppen, setOppen] = useState<string | null>(null);

  const hamta = useCallback(async () => {
    if (demo) {
      setRader({ aterkoppling: demoRader("aterkoppling"), ring: demoRader("ring") });
      return;
    }
    try {
      const [a, r] = await Promise.all(
        (["aterkoppling", "ring"] as const).map((l) => leadsAnrop<{ rader: Samtalsrad[] }>(`/leads/samtal?lista=${l}`))
      );
      setRader({ aterkoppling: a.rader, ring: r.rader });
      setFel(null);
    } catch (orsak) {
      setFel(felmeddelande(orsak));
    }
  }, [demo]);

  useEffect(() => {
    void hamta();
  }, [hamta]);

  const datum = (iso: string | null) =>
    iso ? new Date(iso.length === 10 ? `${iso}T12:00:00` : iso).toLocaleDateString(datumFormat(locale), { day: "numeric", month: "short" }) : "–";

  const visade = rader[lista];
  const antalIdag = (l: Lista) => rader[l]?.filter((r) => r.ring_idag).length ?? 0;

  const radProps = (rad: Samtalsrad) => ({
    oppen: oppen === rad.prospect_id,
    onOppna: () => setOppen(oppen === rad.prospect_id ? null : rad.prospect_id),
    datum,
    demo,
    onSparat: (utfall: Utfall) => {
      setOppen(null);
      if (!demo) {
        void hamta();
        return;
      }
      // Demon har ingen backend: avslutade försvinner, resten väntar till nästa gång.
      setRader((nu) => ({
        ...nu,
        [lista]: (nu[lista] ?? [])
          .filter((r) => r.prospect_id !== rad.prospect_id || !AVSLUTANDE.includes(utfall))
          .map((r) => (r.prospect_id === rad.prospect_id ? { ...r, senaste_utfall: utfall, ring_idag: false } : r))
      }));
    }
  });

  return (
    <section aria-label={text(T.listval)} className="space-y-4">
      <div role="tablist" aria-label={text(T.listval)} className={chiplista}>
        {(["aterkoppling", "ring"] as const).map((l) => (
          <button
            key={l}
            type="button"
            role="tab"
            aria-selected={lista === l}
            onClick={() => {
              setLista(l);
              setOppen(null);
            }}
            className={cn(chip, lista === l ? chipAktiv : chipInaktiv)}
          >
            {text(T[l])}
            {antalIdag(l) > 0 ? ` · ${antalIdag(l)} ${text(T.idag)}` : ""}
          </button>
        ))}
      </div>
      <p className={cn(meta, "max-w-[70ch]")}>{text(lista === "ring" ? T.ringIntro : T.aterkopplingIntro)}</p>

      {fel ? <p role="alert" className="text-[0.9375rem] text-danger">{fel}</p> : null}

      {visade === null ? (
        <SkeletonRows />
      ) : visade.length === 0 ? (
        <Tomt>{text(lista === "ring" ? T.tomRing : T.tomAterkoppling)}</Tomt>
      ) : (
        <>
          {/* Bred skärm: tabellen. */}
          <div className={smal ? "hidden" : "hidden md:block"}>
            <Tabell
              ariaLabel={text(T[lista])}
              minBredd={860}
              kolumner={[
                { rubrik: text(T.bolag), bredd: "22%" },
                { rubrik: text(T.kontakt), bredd: "18%" },
                { rubrik: text(T.telefon), bredd: "21%" },
                { rubrik: text(T.kontaktad), bredd: "10%" },
                { rubrik: text(T.senast), bredd: "12%" },
                { rubrik: text(T.nasta), bredd: "8%" },
                { rubrik: text(T.handling), srOnly: true }
              ]}
            >
              {visade.map((rad) => (
                <TabellRad key={rad.prospect_id} rad={rad} {...radProps(rad)} />
              ))}
            </Tabell>
          </div>
          {/* Telefon: ett kort per bolag, numret överst att ringa från. */}
          <ul className={cn("grid gap-3", !smal && "md:hidden")} aria-label={text(T[lista])}>
            {visade.map((rad) => (
              <Kort key={rad.prospect_id} rad={rad} {...radProps(rad)} />
            ))}
          </ul>
        </>
      )}
    </section>
  );
}

type RadProps = Readonly<{
  rad: Samtalsrad;
  oppen: boolean;
  onOppna: () => void;
  datum: (iso: string | null) => string;
  demo: boolean;
  onSparat: (utfall: Utfall) => void;
}>;

function Telefon({ rad }: Readonly<{ rad: Samtalsrad }>) {
  const { text } = useLocale();
  const anstallda = anstalldaText(rad, text);
  return (
    <>
      {rad.contact_phone ? (
        <a
          href={`tel:${rad.contact_phone.replace(/[^\d+]/g, "")}`}
          aria-label={text({ sv: `Ring ${rad.company_name ?? ""}`, en: `Call ${rad.company_name ?? ""}` })}
          className="focus-ring inline-flex min-h-8 items-center gap-1.5 rounded-input font-medium text-ink underline-offset-4 hover:underline"
        >
          <Phone className="h-3.5 w-3.5" aria-hidden="true" />
          <span className="num">{rad.contact_phone}</span>
        </a>
      ) : (
        "–"
      )}
      {anstallda ? <span className={cn(meta, "mt-0.5 block")}>{anstallda}</span> : null}
    </>
  );
}

function Senaste({ rad, datum }: Readonly<{ rad: Samtalsrad; datum: (iso: string | null) => string }>) {
  const { text } = useLocale();
  return rad.senaste_utfall ? (
    <>
      <span className="block">{text(UTFALL_ETIKETT[rad.senaste_utfall])}</span>
      <span className={meta}>{datum(rad.senaste_samtal)}</span>
    </>
  ) : (
    <span className="text-ink-muted">{text(T.aldrig)}</span>
  );
}

function RingdKnapp({ oppen, onOppna, formId }: Readonly<{ oppen: boolean; onOppna: () => void; formId: string }>) {
  const { text } = useLocale();
  return (
    <button
      type="button"
      aria-expanded={oppen}
      aria-controls={formId}
      onClick={onOppna}
      className={cn(oppen ? btnPrimary : btnSecondary, btnLiten)}
    >
      {text(T.ringd)}
    </button>
  );
}

function TabellRad({ rad, oppen, onOppna, datum, demo, onSparat }: RadProps) {
  const { text } = useLocale();
  const formId = `${useId()}-form`;
  return (
    <>
      <tr className={tabellRad}>
        <Cell titel>
          <span className="block truncate font-medium text-ink">{rad.company_name ?? "–"}</span>
          {rad.ort ? <span className={cn(meta, "block truncate")}>{rad.ort}</span> : null}
        </Cell>
        <Cell>
          <span className="block truncate">{rad.contact_name ?? "–"}</span>
          {rad.contact_role ? <span className={cn(meta, "block truncate")}>{rad.contact_role}</span> : null}
        </Cell>
        <Cell>
          <Telefon rad={rad} />
        </Cell>
        <Cell>{datum(rad.kontaktad)}</Cell>
        <Cell>
          <Senaste rad={rad} datum={datum} />
        </Cell>
        <Cell>{rad.ring_idag ? <Badge tone="warn">{text(T.idagMarke)}</Badge> : datum(rad.nasta)}</Cell>
        <Cell>
          <RingdKnapp oppen={oppen} onOppna={onOppna} formId={formId} />
        </Cell>
      </tr>
      {oppen ? (
        <tr id={formId}>
          <td colSpan={7} className="bg-paper2/60 px-3 py-4">
            <UtfallForm rad={rad} demo={demo} onSparat={onSparat} onAvbryt={onOppna} />
          </td>
        </tr>
      ) : null}
    </>
  );
}

function Kort({ rad, oppen, onOppna, datum, demo, onSparat }: RadProps) {
  const { text } = useLocale();
  const formId = `${useId()}-form`;
  return (
    <li className="rounded-card border border-ink/12 bg-paper p-4">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="truncate font-medium text-ink">{rad.company_name ?? "–"}</p>
          <p className={cn(meta, "truncate")}>
            {[rad.contact_name, rad.contact_role, rad.ort].filter(Boolean).join(" · ") || "–"}
          </p>
        </div>
        {rad.ring_idag ? <Badge tone="warn">{text(T.idagMarke)}</Badge> : <span className={meta}>{datum(rad.nasta)}</span>}
      </div>
      <div className="mt-3">
        <Telefon rad={rad} />
      </div>
      <dl className={cn(meta, "mt-3 grid grid-cols-2 gap-x-4 gap-y-1")}>
        <dt>{text(T.kontaktad)}</dt>
        <dd className="text-ink">{datum(rad.kontaktad)}</dd>
        <dt>{text(T.senast)}</dt>
        <dd className="text-ink">
          <Senaste rad={rad} datum={datum} />
        </dd>
      </dl>
      <div className="mt-3">
        <RingdKnapp oppen={oppen} onOppna={onOppna} formId={formId} />
      </div>
      {oppen ? (
        <div id={formId} className="mt-3 border-t border-ink/12 pt-3">
          <UtfallForm rad={rad} demo={demo} onSparat={onSparat} onAvbryt={onOppna} />
        </div>
      ) : null}
    </li>
  );
}

function UtfallForm({
  rad,
  demo,
  onSparat,
  onAvbryt
}: Readonly<{ rad: Samtalsrad; demo: boolean; onSparat: (utfall: Utfall) => void; onAvbryt: () => void }>) {
  const { text } = useLocale();
  const id = useId();
  const [utfall, setUtfall] = useState<Utfall>("ej_svar");
  const [aterkom, setAterkom] = useState("");
  const [anteckning, setAnteckning] = useState("");
  const [sparar, setSparar] = useState(false);
  const [fel, setFel] = useState<string | null>(null);
  const idag = new Date().toISOString().slice(0, 10);

  async function spara() {
    if (utfall === "aterkom" && !aterkom) {
      setFel(text(T.valjDatum));
      return;
    }
    setSparar(true);
    setFel(null);
    try {
      if (!demo) {
        await leadsAnrop(`/leads/prospects/${rad.prospect_id}/samtal`, {
          method: "POST",
          body: JSON.stringify({
            utfall,
            aterkom_datum: utfall === "aterkom" ? aterkom : null,
            anteckning: anteckning.trim() || null
          })
        });
      }
      onSparat(utfall);
    } catch (orsak) {
      setFel(felmeddelande(orsak));
    } finally {
      setSparar(false);
    }
  }

  return (
    <fieldset className="space-y-3">
      <legend className={etikett}>{text(T.utfall)}</legend>
      <div className={chiplista}>
        {UTFALL.map((u) => (
          <label
            key={u}
            className={cn(chip, "cursor-pointer has-[:focus-visible]:ring-2 has-[:focus-visible]:ring-ochre", utfall === u ? chipAktiv : chipInaktiv)}
          >
            <input
              type="radio"
              name={`${id}-utfall`}
              value={u}
              checked={utfall === u}
              onChange={() => setUtfall(u)}
              className="sr-only"
            />
            {text(UTFALL_ETIKETT[u])}
          </label>
        ))}
      </div>
      <div className="flex flex-wrap items-end gap-3">
        {utfall === "aterkom" ? (
          <label className="grid gap-1">
            <span className={etikett}>{text(T.aterkomDatum)}</span>
            <input
              type="date"
              min={idag}
              value={aterkom}
              onChange={(e) => setAterkom(e.target.value)}
              className="focus-ring min-h-10 rounded-input border border-ink/15 bg-paper px-3 text-[16px] text-ink"
            />
          </label>
        ) : null}
        <label className="grid min-w-0 flex-1 basis-56 gap-1">
          <span className={etikett}>{text(T.anteckning)}</span>
          <input
            value={anteckning}
            onChange={(e) => setAnteckning(e.target.value)}
            maxLength={4000}
            className="focus-ring min-h-10 w-full rounded-input border border-ink/15 bg-paper px-3 text-[16px] text-ink"
          />
        </label>
        <div className="flex gap-2">
          <button type="button" onClick={() => void spara()} disabled={sparar} className={cn(btnPrimary, btnLiten)}>
            {sparar ? text(T.sparar) : text(T.spara)}
          </button>
          <button type="button" onClick={onAvbryt} className={cn(btnSecondary, btnLiten)}>
            {text(T.avbryt)}
          </button>
        </div>
      </div>
      {fel ? <p role="alert" className="text-[0.875rem] text-danger">{fel}</p> : null}
    </fieldset>
  );
}
