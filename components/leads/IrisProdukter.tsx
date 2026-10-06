"use client";

/* design · pre-emit critique: P4 H4 E4 S4 R5 V3 — Operate-yta i det låsta systemet
   (DESIGN.md, Tier 0): husets etiketter, fält och knappar, ingen ny riktning. */

import { ArrowDown, ArrowUp, Plus, Trash2 } from "lucide-react";
import { useEffect, useState } from "react";
import { btnPrimary, btnSecondary, btnLiten, etikett, meta, rubrikPanel } from "@/components/ui";
import { felmeddelande } from "@/lib/http/json";
import { useLocale, type Localized } from "@/lib/i18n";
import { leadsAnrop } from "@/lib/leads/suite";
import { cn } from "@/lib/utils";

/**
 * Iris › Inställningar › Produkter och målgrupp (fas 8, 2026-10-06).
 *
 * Kundens egna produkter (Iris väljer EN per bolag och skriver bara om den),
 * målsegmenten i rangordning (sökningen tar dem i tur och ordning) och om
 * kunden säljer till offentlig sektor. Lagras i `agent_configs.settings` via
 * `PUT /leads/config`; profilkompilatorn och researchen läser samma fält.
 * Texten är kundskriven och hamnar i användarposition (INV-SEC-009).
 */

type Produkt = { namn: string; nytta: string };
type Segment = { bransch: string; varfor: string };
type Config = { produkter?: Produkt[]; segment?: Segment[]; offentlig_sektor?: boolean };

const MAX_PRODUKTER = 8;
const MAX_SEGMENT = 6;

const T = {
  rubrik: { sv: "Produkter och målgrupp", en: "Products and target group" },
  om: {
    sv: "Iris väljer den produkt som passar varje bolag bäst och skriver bara om den. Segmenten söks i den ordning de står.",
    en: "Iris picks the product that fits each company best and writes only about that one. Segments are searched in the order listed."
  },
  produkter: { sv: "Produkter", en: "Products" },
  namn: { sv: "Namn", en: "Name" },
  nytta: { sv: "Nyttan för kunden", en: "The benefit to the customer" },
  laggTillProdukt: { sv: "Lägg till produkt", en: "Add product" },
  segment: { sv: "Målsegment, bäst först", en: "Target segments, best first" },
  bransch: { sv: "Bransch", en: "Industry" },
  varfor: { sv: "Varför de passar", en: "Why they fit" },
  laggTillSegment: { sv: "Lägg till segment", en: "Add segment" },
  offentlig: { sv: "Vi säljer till offentlig sektor och skolor", en: "We sell to the public sector and schools" },
  offentligHjalp: {
    sv: "Annars väljer Iris bara privata bolag.",
    en: "Otherwise Iris only picks private companies."
  },
  upp: { sv: "Flytta upp", en: "Move up" },
  ned: { sv: "Flytta ned", en: "Move down" },
  taBort: { sv: "Ta bort", en: "Remove" },
  spara: { sv: "Spara produkter och målgrupp", en: "Save products and target group" },
  sparar: { sv: "Sparar…", en: "Saving…" },
  sparat: { sv: "Sparat. Gäller från nästa körning.", en: "Saved. Applies from the next run." },
  hamtaFel: { sv: "Inställningarna kunde inte hämtas:", en: "The settings could not be loaded:" }
} satisfies Record<string, Localized>;

const falt = "focus-ring w-full rounded-input border border-ink/15 bg-paper px-3 py-2.5 text-[16px] leading-6";

function flytta<X>(lista: X[], i: number, steg: number): X[] {
  const j = i + steg;
  if (j < 0 || j >= lista.length) return lista;
  const ny = [...lista];
  [ny[i], ny[j]] = [ny[j], ny[i]];
  return ny;
}

export function IrisProdukter() {
  const { text } = useLocale();
  const [produkter, setProdukter] = useState<Produkt[] | null>(null);
  const [segment, setSegment] = useState<Segment[]>([]);
  const [offentlig, setOffentlig] = useState(false);
  const [busy, setBusy] = useState(false);
  const [fel, setFel] = useState<string | null>(null);
  const [klart, setKlart] = useState(false);

  useEffect(() => {
    let avbruten = false;
    leadsAnrop<Config>("/leads/config")
      .then((c) => {
        if (avbruten) return;
        setProdukter(c.produkter ?? []);
        setSegment(c.segment ?? []);
        setOffentlig(Boolean(c.offentlig_sektor));
      })
      .catch((orsak) => {
        if (avbruten) return;
        setProdukter([]);
        setFel(`${text(T.hamtaFel)} ${felmeddelande(orsak)}`);
      });
    return () => {
      avbruten = true;
    };
  }, [text]);

  async function spara() {
    setBusy(true);
    setFel(null);
    setKlart(false);
    try {
      await leadsAnrop<Config>("/leads/config", {
        method: "PUT",
        body: JSON.stringify({
          produkter: (produkter ?? []).filter((p) => p.namn.trim()),
          segment: segment.filter((s) => s.bransch.trim()),
          offentlig_sektor: offentlig
        })
      });
      setKlart(true);
    } catch (orsak) {
      setFel(felmeddelande(orsak));
    } finally {
      setBusy(false);
    }
  }

  if (produkter === null) {
    return <div className="h-48 animate-pulse rounded-card bg-ink/[0.055]" aria-busy="true" />;
  }

  return (
    <section aria-labelledby="iris-produkter-rubrik" className="grid gap-8">
      <div>
        <h2 id="iris-produkter-rubrik" className={rubrikPanel}>
          {text(T.rubrik)}
        </h2>
        <p className="mt-1 max-w-[62ch] text-[0.9375rem] leading-6 text-ink-muted">{text(T.om)}</p>
      </div>

      <fieldset className="grid gap-4">
        <legend className={etikett}>{text(T.produkter)}</legend>
        {produkter.map((p, i) => (
          <div key={i} className="grid gap-3 border-t border-ink/12 pt-4 sm:grid-cols-[minmax(0,14rem)_minmax(0,1fr)_auto] sm:items-end">
            <label className="grid gap-1">
              <span className={meta}>{text(T.namn)}</span>
              <input
                value={p.namn}
                maxLength={80}
                onChange={(e) => setProdukter(produkter.map((x, j) => (j === i ? { ...x, namn: e.target.value } : x)))}
                className={falt}
              />
            </label>
            <label className="grid gap-1">
              <span className={meta}>{text(T.nytta)}</span>
              <input
                value={p.nytta}
                maxLength={400}
                onChange={(e) => setProdukter(produkter.map((x, j) => (j === i ? { ...x, nytta: e.target.value } : x)))}
                className={falt}
              />
            </label>
            <button
              type="button"
              onClick={() => setProdukter(produkter.filter((_, j) => j !== i))}
              className={cn(btnSecondary, btnLiten)}
              aria-label={`${text(T.taBort)}: ${p.namn || text(T.produkter)}`}
            >
              <Trash2 className="h-4 w-4" aria-hidden />
            </button>
          </div>
        ))}
        {produkter.length < MAX_PRODUKTER ? (
          <button
            type="button"
            onClick={() => setProdukter([...produkter, { namn: "", nytta: "" }])}
            className={cn(btnSecondary, btnLiten, "justify-self-start")}
          >
            <Plus className="h-4 w-4" aria-hidden /> {text(T.laggTillProdukt)}
          </button>
        ) : null}
      </fieldset>

      <fieldset className="grid gap-4">
        <legend className={etikett}>{text(T.segment)}</legend>
        <ol className="grid gap-4">
          {segment.map((s, i) => (
            <li
              key={i}
              className="grid gap-3 border-t border-ink/12 pt-4 sm:grid-cols-[2rem_minmax(0,14rem)_minmax(0,1fr)_auto] sm:items-end"
            >
              <span className="num pb-3 text-[0.9375rem] text-ink-muted" aria-hidden>
                {i + 1}
              </span>
              <label className="grid gap-1">
                <span className={meta}>{text(T.bransch)}</span>
                <input
                  value={s.bransch}
                  maxLength={80}
                  onChange={(e) => setSegment(segment.map((x, j) => (j === i ? { ...x, bransch: e.target.value } : x)))}
                  className={falt}
                />
              </label>
              <label className="grid gap-1">
                <span className={meta}>{text(T.varfor)}</span>
                <input
                  value={s.varfor}
                  maxLength={240}
                  onChange={(e) => setSegment(segment.map((x, j) => (j === i ? { ...x, varfor: e.target.value } : x)))}
                  className={falt}
                />
              </label>
              <div className="flex gap-2">
                <button
                  type="button"
                  disabled={i === 0}
                  onClick={() => setSegment(flytta(segment, i, -1))}
                  className={cn(btnSecondary, btnLiten)}
                  aria-label={`${text(T.upp)}: ${s.bransch}`}
                >
                  <ArrowUp className="h-4 w-4" aria-hidden />
                </button>
                <button
                  type="button"
                  disabled={i === segment.length - 1}
                  onClick={() => setSegment(flytta(segment, i, 1))}
                  className={cn(btnSecondary, btnLiten)}
                  aria-label={`${text(T.ned)}: ${s.bransch}`}
                >
                  <ArrowDown className="h-4 w-4" aria-hidden />
                </button>
                <button
                  type="button"
                  onClick={() => setSegment(segment.filter((_, j) => j !== i))}
                  className={cn(btnSecondary, btnLiten)}
                  aria-label={`${text(T.taBort)}: ${s.bransch}`}
                >
                  <Trash2 className="h-4 w-4" aria-hidden />
                </button>
              </div>
            </li>
          ))}
        </ol>
        {segment.length < MAX_SEGMENT ? (
          <button
            type="button"
            onClick={() => setSegment([...segment, { bransch: "", varfor: "" }])}
            className={cn(btnSecondary, btnLiten, "justify-self-start")}
          >
            <Plus className="h-4 w-4" aria-hidden /> {text(T.laggTillSegment)}
          </button>
        ) : null}
      </fieldset>

      <label className="inline-flex min-h-11 items-start gap-3 text-[0.9375rem] text-ink">
        <input
          type="checkbox"
          checked={offentlig}
          onChange={(e) => setOffentlig(e.target.checked)}
          aria-describedby="iris-offentlig-hjalp"
          className="focus-ring mt-0.5 size-5 accent-[var(--color-ink)]"
        />
        <span>
          {text(T.offentlig)}
          <span id="iris-offentlig-hjalp" className="block text-ink-muted">
            {text(T.offentligHjalp)}
          </span>
        </span>
      </label>

      <div className="flex flex-wrap items-center gap-x-4 gap-y-3">
        <button type="button" onClick={() => void spara()} disabled={busy} className={btnPrimary}>
          {busy ? text(T.sparar) : text(T.spara)}
        </button>
        <span aria-live="polite" className="text-[0.9375rem] text-moss">
          {klart ? text(T.sparat) : ""}
        </span>
        {fel ? (
          <p role="alert" className="max-w-[62ch] break-words text-[0.9375rem] text-danger">
            {fel}
          </p>
        ) : null}
      </div>
    </section>
  );
}
