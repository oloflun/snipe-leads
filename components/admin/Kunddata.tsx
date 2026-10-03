"use client";

import { useState } from "react";

import {
  Badge,
  Rad,
  Radlista,
  Sektion,
  Tomt,
  btnLiten,
  btnPrimary,
  btnSecondary,
  etikett,
  rubrikPanel
} from "@/components/ui";
import {
  skapaKontakt,
  sparaKunddata,
  taBortKontakt,
  uppdateraKontakt,
  type Kontakt,
  type Kunddata as Data
} from "@/lib/actions/kunddata";
import { ADMIN, a, ordagrant } from "@/lib/admin/sprak";
import { useLocale, type Localized } from "@/lib/i18n";

/**
 * Kundregistret för EN kund: kontaktpersoner överst, kunduppgifterna under.
 *
 * ## Varför varje fält bär en källmärkning
 *
 * Hälften av värdena är härledda (orgnr ur onboardingens affärskontext,
 * kund-sedan ur registreringsdatumet) och hälften manuellt ifyllda. I ett
 * formulär ser de identiska ut, och ett härlett värde som ser bekräftat ut
 * är precis vad ett faktureringsunderlag inte får innehålla. Märket kommer
 * från backenden per fält — vyn hittar aldrig på en källa själv.
 *
 * ## Varför sparandet bara skickar ÄNDRADE fält
 *
 * Backenden skiljer på "utelämnat" (rör inte) och "tom sträng" (nollställ).
 * Att skicka hela formuläret hade gjort varje härlett värde manuellt vid
 * första sparning — datumet som kom ur registreringen hade plötsligt sett
 * handbekräftat ut. Diffen mot utgångsläget är alltså semantik, inte en
 * optimering.
 *
 * ## Vad som togs bort 2026-09-27
 *
 * Ingresserna under båda sektionsrubrikerna (F-016) och meningen om
 * avtalsstatus under fälten. Den senare upprepade fältet "Avtal signerat",
 * vars märke redan säger "Saknas" när inget avtal är registrerat. Att ett
 * manuellt värde vinner över det automatiska, och att ett tömt fält går
 * tillbaka till det automatiska, syns i märket efter sparning.
 */

const FALT: { nyckel: string; etikett: Localized; typ: "text" | "date"; brett?: boolean }[] = [
  { nyckel: "orgnr", etikett: { sv: "Organisationsnummer", en: "Company registration number" }, typ: "text" },
  { nyckel: "telefon", etikett: { sv: "Telefonnummer", en: "Phone number" }, typ: "text" },
  { nyckel: "faktureringsmejl", etikett: { sv: "Faktureringsmejl", en: "Billing email" }, typ: "text" },
  { nyckel: "kund_sedan", etikett: { sv: "Kund sedan", en: "Customer since" }, typ: "date" },
  {
    nyckel: "faktureringsadress",
    etikett: { sv: "Faktureringsadress", en: "Billing address" },
    typ: "text",
    brett: true
  },
  {
    nyckel: "foretagsadress",
    etikett: { sv: "Företagets adress", en: "Company address" },
    typ: "text",
    brett: true
  },
  // Obligatorisk i kallmejlfoten sedan migration 073 — utan den blockerar
  // send_guard varje utskick för kunden, med besked som pekar hit.
  {
    nyckel: "policy_url",
    etikett: { sv: "Integritetspolicy (URL)", en: "Privacy policy (URL)" },
    typ: "text",
    brett: true
  },
  { nyckel: "avtal_signerat", etikett: { sv: "Avtal signerat", en: "Contract signed" }, typ: "date" }
];

const KALLETIKETT: Record<string, Localized> = {
  manuell: { sv: "Manuellt ifylld", en: "Entered manually" },
  onboarding: { sv: "Auto: onboardingen", en: "Auto: onboarding" },
  system: { sv: "Auto: registreringsdatum", en: "Auto: registration date" }
};

// 16px textstorlek är golvet (iOS force-zoomar under det); det kompakta
// sitter i paddingen, inte i typografin.
const inputKlass =
  "focus-ring mt-1 w-full rounded-input border border-ink/15 bg-paper px-2.5 py-1.5 text-[1rem] leading-6 text-ink";

function KallaBadge({ kalla }: Readonly<{ kalla: string | null }>) {
  const { locale, text } = useLocale();
  if (!kalla) {
    // "Saknas" är arbetslistan i den här vyn — det är de fälten någon ska
    // fylla i. Warn-tonen pekar ut dem utan att skrika.
    return <Badge tone="warn">{a("saknasStor", locale)}</Badge>;
  }
  return <Badge tone="neutral">{KALLETIKETT[kalla] ? text(KALLETIKETT[kalla]) : kalla}</Badge>;
}

// -- Kontaktpersoner --------------------------------------------------------

const TOM_KONTAKT = { namn: "", roll: "", mejl: "", telefon: "" };

function KontaktFalt({
  varden,
  satt,
  prefix
}: Readonly<{
  varden: typeof TOM_KONTAKT;
  satt: (v: typeof TOM_KONTAKT) => void;
  prefix: string;
}>) {
  const { locale } = useLocale();
  return (
    <div className="grid gap-2.5 sm:grid-cols-2 lg:grid-cols-4">
      {(
        [
          ["namn", "kontaktNamn"],
          ["roll", "kontaktRoll"],
          ["mejl", "kontaktMejl"],
          ["telefon", "kontaktDirektnummer"]
        ] as const
      ).map(([falt, etikett]) => (
        <label key={falt} className={`block ${etikett}`}>
          {a(etikett, locale)}
          <input
            type={falt === "mejl" ? "email" : "text"}
            name={`${prefix}-${falt}`}
            value={varden[falt]}
            onChange={(e) => satt({ ...varden, [falt]: e.target.value })}
            className={inputKlass}
          />
        </label>
      ))}
    </div>
  );
}

function KontaktRad({
  tenantId,
  kontakt,
  onFel
}: Readonly<{ tenantId: string; kontakt: Kontakt; onFel: (fel: Localized) => void }>) {
  const { locale, text } = useLocale();
  const [varden, setVarden] = useState({
    namn: kontakt.namn,
    roll: kontakt.roll ?? "",
    mejl: kontakt.mejl ?? "",
    telefon: kontakt.telefon ?? ""
  });
  const [arbetar, setArbetar] = useState(false);
  const [kvitto, setKvitto] = useState<Localized | null>(null);

  function spara() {
    setArbetar(true);
    setKvitto(null);
    void (async () => {
      const svar = await uppdateraKontakt(tenantId, kontakt.id, varden);
      if (!svar.success) onFel(svar.error ? ordagrant(svar.error) : ADMIN.kundeInteSparaKontakt);
      else setKvitto(ADMIN.sparatPunkt);
      setArbetar(false);
    })();
  }

  function taBort() {
    setArbetar(true);
    void (async () => {
      const svar = await taBortKontakt(tenantId, kontakt.id);
      if (!svar.success) {
        onFel(svar.error ? ordagrant(svar.error) : ADMIN.kundeInteTaBortKontakt);
        setArbetar(false);
      }
      // Lyckad borttagning: raden försvinner när sidan revalideras — att
      // återställa arbetsläget här hade fått knappen att blinka till.
    })();
  }

  return (
    <Rad>
      <KontaktFalt varden={varden} satt={setVarden} prefix={kontakt.id} />
      <div className="mt-2.5 flex flex-wrap items-center gap-3">
        <button type="button" onClick={spara} disabled={arbetar} className={`${btnSecondary} ${btnLiten}`}>
          {arbetar ? a("sparar", locale) : a("spara", locale)}
        </button>
        <button
          type="button"
          onClick={taBort}
          disabled={arbetar}
          className="focus-ring inline-flex h-9 items-center rounded-input px-3 text-[0.875rem] font-medium text-danger hover:bg-danger/10"
        >
          {a("taBort", locale)}
        </button>
        <span aria-live="polite" className="text-[0.8125rem] text-mineral">
          {kvitto ? text(kvitto) : ""}
        </span>
      </div>
    </Rad>
  );
}

// -- Hela vyn ---------------------------------------------------------------

export function Kunddata({ data }: Readonly<{ data: Data }>) {
  const tenantId = data.tenant.id;

  // Utgångsläget för diffen: det backenden visade, härledda värden inräknade.
  const [utgangslage] = useState<Record<string, string>>(() =>
    Object.fromEntries(FALT.map((f) => [f.nyckel, data.falt[f.nyckel]?.varde ?? ""]))
  );
  const [varden, setVarden] = useState(utgangslage);
  const [sparar, setSparar] = useState(false);
  const [kvitto, setKvitto] = useState<Localized | null>(null);
  const [fel, setFel] = useState<Localized | null>(null);
  const { locale, text } = useLocale();

  const [ny, setNy] = useState(TOM_KONTAKT);
  const [laggerTill, setLaggerTill] = useState(false);

  function sparaUppgifter() {
    const andrade = Object.fromEntries(
      Object.entries(varden).filter(([nyckel, varde]) => varde !== utgangslage[nyckel])
    );
    if (Object.keys(andrade).length === 0) {
      setKvitto(ADMIN.ingetAndrat);
      return;
    }
    setSparar(true);
    setKvitto(null);
    setFel(null);
    void (async () => {
      const svar = await sparaKunddata(tenantId, andrade);
      if (svar.success) setKvitto(ADMIN.sparatPunkt);
      else setFel(svar.error ? ordagrant(svar.error) : ADMIN.kundeInteSpara);
      setSparar(false);
    })();
  }

  function laggTill() {
    if (!ny.namn.trim()) {
      setFel(ADMIN.kontaktBehoverNamn);
      return;
    }
    setLaggerTill(true);
    setFel(null);
    void (async () => {
      const svar = await skapaKontakt(tenantId, ny);
      if (svar.success) setNy(TOM_KONTAKT);
      else setFel(svar.error ? ordagrant(svar.error) : ADMIN.kundeInteLaggaTillKontakt);
      setLaggerTill(false);
    })();
  }

  return (
    <div>
      {fel ? (
        <p role="alert" className="mb-8 max-w-[70ch] break-words text-[0.9375rem] text-danger">
          {text(fel)}
        </p>
      ) : null}

      {/* Kontaktpersonerna först — det är det enda i vyn som ALLTID är
          manuellt, och den som öppnar en kund gör det oftast för att ringa
          någon, inte för att läsa ett orgnr. */}
      <Sektion title={a("kontaktpersoner", locale)}>
        {data.kontakter.length === 0 ? (
          <Tomt>{a("ingaKontaktpersoner", locale)}</Tomt>
        ) : (
          <Radlista>
            {data.kontakter.map((kontakt) => (
              <KontaktRad key={kontakt.id} tenantId={tenantId} kontakt={kontakt} onFel={setFel} />
            ))}
          </Radlista>
        )}

        <div className="mt-4 rounded-input border border-ink/15 bg-paper2/40 p-4">
          <h3 className={rubrikPanel}>{a("laggTillKontaktperson", locale)}</h3>
          <div className="mt-3">
            <KontaktFalt varden={ny} satt={setNy} prefix="ny" />
          </div>
          <button
            type="button"
            onClick={laggTill}
            disabled={laggerTill}
            className={`${btnPrimary} ${btnLiten} mt-3`}
          >
            {laggerTill ? a("laggerTill", locale) : a("laggTill", locale)}
          </button>
        </div>
      </Sektion>

      <Sektion title={a("kunduppgifter", locale)}>
        <div className="grid gap-x-6 gap-y-3.5 sm:grid-cols-2">
          {FALT.map((falt) => (
            <label
              key={falt.nyckel}
              className={`block ${etikett} ${falt.brett ? "sm:col-span-2" : ""}`}
            >
              <span className="flex flex-wrap items-baseline gap-x-2 gap-y-1">
                {text(falt.etikett)}
                <KallaBadge kalla={data.falt[falt.nyckel]?.kalla ?? null} />
              </span>
              <input
                type={falt.typ}
                name={falt.nyckel}
                value={varden[falt.nyckel] ?? ""}
                onChange={(e) => {
                  setVarden((v) => ({ ...v, [falt.nyckel]: e.target.value }));
                  setKvitto(null);
                }}
                className={inputKlass}
              />
            </label>
          ))}
        </div>

        <div className="mt-4 flex flex-wrap items-center gap-3">
          <button
            type="button"
            onClick={sparaUppgifter}
            disabled={sparar}
            className={`${btnPrimary} ${btnLiten}`}
          >
            {sparar ? a("sparar", locale) : a("sparaKunduppgifter", locale)}
          </button>
          <span aria-live="polite" className="text-[0.8125rem] text-mineral">
            {kvitto ? text(kvitto) : ""}
          </span>
        </div>
      </Sektion>
    </div>
  );
}
