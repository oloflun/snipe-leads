"use client";

import { useState } from "react";

import { Badge, btnLiten, btnPrimary, btnSecondary } from "@/components/ui";
import {
  skapaKontakt,
  sparaKunddata,
  taBortKontakt,
  uppdateraKontakt,
  type Kontakt,
  type Kunddata as Data
} from "@/lib/actions/kunddata";

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
 */

const FALT: { nyckel: string; etikett: string; typ: "text" | "date"; brett?: boolean }[] = [
  { nyckel: "orgnr", etikett: "Organisationsnummer", typ: "text" },
  { nyckel: "telefon", etikett: "Telefonnummer", typ: "text" },
  { nyckel: "faktureringsmejl", etikett: "Faktureringsmejl", typ: "text" },
  { nyckel: "kund_sedan", etikett: "Kund sedan", typ: "date" },
  { nyckel: "faktureringsadress", etikett: "Faktureringsadress", typ: "text", brett: true },
  { nyckel: "foretagsadress", etikett: "Företagets adress", typ: "text", brett: true },
  { nyckel: "avtal_signerat", etikett: "Avtal signerat", typ: "date" }
];

const KALLETIKETT: Record<string, string> = {
  manuell: "Manuellt ifylld",
  onboarding: "Auto: onboardingen",
  system: "Auto: registreringsdatum"
};

// 16px textstorlek är golvet (iOS force-zoomar under det); det kompakta
// sitter i paddingen, inte i typografin.
const inputKlass =
  "focus-ring mt-1 w-full rounded-input border border-ink/15 bg-paper px-2.5 py-1.5 text-[1rem] leading-6";

function KallaBadge({ kalla }: Readonly<{ kalla: string | null }>) {
  if (!kalla) {
    // "Saknas" är arbetslistan i den här vyn — det är de fälten någon ska
    // fylla i. Warn-tonen pekar ut dem utan att skrika.
    return <Badge tone="warn">Saknas</Badge>;
  }
  return <Badge tone="neutral">{KALLETIKETT[kalla] ?? kalla}</Badge>;
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
  return (
    <div className="grid gap-2.5 sm:grid-cols-2 lg:grid-cols-4">
      {(
        [
          ["namn", "Namn"],
          ["roll", "Roll"],
          ["mejl", "Mejl"],
          ["telefon", "Direktnummer"]
        ] as const
      ).map(([falt, etikett]) => (
        <label key={falt} className="block text-[0.8125rem] text-mineral">
          {etikett}
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
}: Readonly<{ tenantId: string; kontakt: Kontakt; onFel: (fel: string) => void }>) {
  const [varden, setVarden] = useState({
    namn: kontakt.namn,
    roll: kontakt.roll ?? "",
    mejl: kontakt.mejl ?? "",
    telefon: kontakt.telefon ?? ""
  });
  const [arbetar, setArbetar] = useState(false);
  const [kvitto, setKvitto] = useState("");

  function spara() {
    setArbetar(true);
    setKvitto("");
    void (async () => {
      const svar = await uppdateraKontakt(tenantId, kontakt.id, varden);
      if (!svar.success) onFel(svar.error ?? "Kunde inte spara kontaktpersonen.");
      else setKvitto("Sparat.");
      setArbetar(false);
    })();
  }

  function taBort() {
    setArbetar(true);
    void (async () => {
      const svar = await taBortKontakt(tenantId, kontakt.id);
      if (!svar.success) {
        onFel(svar.error ?? "Kunde inte ta bort kontaktpersonen.");
        setArbetar(false);
      }
      // Lyckad borttagning: raden försvinner när sidan revalideras — att
      // återställa arbetsläget här hade fått knappen att blinka till.
    })();
  }

  return (
    <li className="border-t border-ink/10 py-3 first:border-t-0">
      <KontaktFalt varden={varden} satt={setVarden} prefix={kontakt.id} />
      <div className="mt-2.5 flex flex-wrap items-center gap-3">
        <button type="button" onClick={spara} disabled={arbetar} className={`${btnSecondary} ${btnLiten}`}>
          {arbetar ? "Sparar…" : "Spara"}
        </button>
        <button
          type="button"
          onClick={taBort}
          disabled={arbetar}
          className="focus-ring inline-flex h-9 items-center rounded-input px-3 text-[0.875rem] font-medium text-danger hover:bg-danger/10"
        >
          Ta bort
        </button>
        <span aria-live="polite" className="text-[0.8125rem] text-mineral">
          {kvitto}
        </span>
      </div>
    </li>
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
  const [kvitto, setKvitto] = useState("");
  const [fel, setFel] = useState("");

  const [ny, setNy] = useState(TOM_KONTAKT);
  const [laggerTill, setLaggerTill] = useState(false);

  function sparaUppgifter() {
    const andrade = Object.fromEntries(
      Object.entries(varden).filter(([nyckel, varde]) => varde !== utgangslage[nyckel])
    );
    if (Object.keys(andrade).length === 0) {
      setKvitto("Inget ändrat.");
      return;
    }
    setSparar(true);
    setKvitto("");
    setFel("");
    void (async () => {
      const svar = await sparaKunddata(tenantId, andrade);
      if (svar.success) setKvitto("Sparat.");
      else setFel(svar.error ?? "Kunde inte spara.");
      setSparar(false);
    })();
  }

  function laggTill() {
    if (!ny.namn.trim()) {
      setFel("Kontaktpersonen behöver ett namn.");
      return;
    }
    setLaggerTill(true);
    setFel("");
    void (async () => {
      const svar = await skapaKontakt(tenantId, ny);
      if (svar.success) setNy(TOM_KONTAKT);
      else setFel(svar.error ?? "Kunde inte lägga till kontaktpersonen.");
      setLaggerTill(false);
    })();
  }

  const avtal = data.falt.avtal_signerat?.varde;

  return (
    <div className="grid gap-7">
      {fel ? (
        <p role="alert" className="max-w-[70ch] break-words text-[0.9375rem] text-danger">
          {fel}
        </p>
      ) : null}

      {/* Kontaktpersonerna först — det är det enda i vyn som ALLTID är
          manuellt, och den som öppnar en kund gör det oftast för att ringa
          någon, inte för att läsa ett orgnr. */}
      <section className="border-t border-ink/15 pt-4">
        <h2 className="kicker text-mineral">Kontaktpersoner</h2>
        <p className="mt-1.5 max-w-[70ch] text-[0.875rem] leading-6 text-ink/65">
          Förvaltas för hand. Namn krävs; roll, mejl och direktnummer är valfria.
        </p>

        {data.kontakter.length === 0 ? (
          <p className="mt-4 text-[0.875rem] text-ink/60">Inga kontaktpersoner ännu.</p>
        ) : (
          <ul className="mt-4">
            {data.kontakter.map((kontakt) => (
              <KontaktRad key={kontakt.id} tenantId={tenantId} kontakt={kontakt} onFel={setFel} />
            ))}
          </ul>
        )}

        <div className="mt-4 rounded-input border border-ink/15 bg-paper2/40 p-3.5">
          <h3 className="text-[0.875rem] font-semibold">Lägg till kontaktperson</h3>
          <div className="mt-2.5">
            <KontaktFalt varden={ny} satt={setNy} prefix="ny" />
          </div>
          <button
            type="button"
            onClick={laggTill}
            disabled={laggerTill}
            className={`${btnPrimary} ${btnLiten} mt-3`}
          >
            {laggerTill ? "Lägger till…" : "Lägg till"}
          </button>
        </div>
      </section>

      <section className="border-t border-ink/15 pt-4">
        <h2 className="kicker text-mineral">Kunduppgifter</h2>
        <p className="mt-1.5 max-w-[70ch] text-[0.875rem] leading-6 text-ink/65">
          Märket vid varje fält säger var värdet kommer ifrån. Det som fylls i här
          sparas som manuellt och vinner över det automatiska. Ett tömt fält går
          tillbaka till det automatiska värdet, om ett finns.
        </p>

        <div className="mt-4 grid gap-x-6 gap-y-3.5 sm:grid-cols-2">
          {FALT.map((falt) => (
            <label
              key={falt.nyckel}
              className={`block text-[0.8125rem] text-mineral ${falt.brett ? "sm:col-span-2" : ""}`}
            >
              <span className="flex flex-wrap items-baseline gap-x-2 gap-y-1">
                {falt.etikett}
                <KallaBadge kalla={data.falt[falt.nyckel]?.kalla ?? null} />
              </span>
              <input
                type={falt.typ}
                name={falt.nyckel}
                value={varden[falt.nyckel] ?? ""}
                onChange={(e) => {
                  setVarden((v) => ({ ...v, [falt.nyckel]: e.target.value }));
                  setKvitto("");
                }}
                className={inputKlass}
              />
            </label>
          ))}
        </div>

        {/* Avtalsstatusen utskriven i klartext. Datumfältet ensamt säger inte
            "inget avtal finns" — ett tomt fält ser likadant ut som ett ofyllt. */}
        <p className="mt-3 text-[0.875rem] text-ink/65">
          {avtal
            ? `Avtal finns, signerat ${avtal}.`
            : "Inget avtal registrerat. Fyll i signeringsdatumet ovan när det finns."}
        </p>

        <div className="mt-4 flex flex-wrap items-center gap-3">
          <button
            type="button"
            onClick={sparaUppgifter}
            disabled={sparar}
            className={`${btnPrimary} ${btnLiten}`}
          >
            {sparar ? "Sparar…" : "Spara kunduppgifter"}
          </button>
          <span aria-live="polite" className="text-[0.8125rem] text-mineral">
            {kvitto}
          </span>
        </div>
      </section>
    </div>
  );
}
