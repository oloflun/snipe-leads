"use client";

/* design · pre-emit critique: P4 H4 E4 S4 R5 V3 — Operate-yta i det låsta systemet
   (DESIGN.md, Tier 0): husets etiketter, fält och knappar, ingen ny riktning. */

import { ArrowDown, ArrowUp, Plus, Trash2 } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
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
 *
 * Tillgänglighet (granskning 2026-10-06): knapparna är `aria-disabled`, inte
 * `disabled`, så att fokus stannar kvar när de låses under en sparning; en
 * borttagen rad går att ångra; fokus följer en flyttad rad (stabila id:n, inte
 * index) och flytten annonseras. Gick inställningarna inte att hämta visas
 * inget formulär: ett tomt formulär hade sparat tomma listor över kundens.
 */

type Produkt = { id: string; namn: string; nytta: string };
type Segment = { id: string; bransch: string; varfor: string };
type Config = {
  produkter?: Omit<Produkt, "id">[];
  segment?: Omit<Segment, "id">[];
  offentlig_sektor?: boolean;
};
type Borttagen = { typ: "produkt"; rad: Produkt; plats: number } | { typ: "segment"; rad: Segment; plats: number };

const MAX_PRODUKTER = 8;
const MAX_SEGMENT = 6;

const T = {
  rubrik: { sv: "Produkter och målgrupp", en: "Products and target group" },
  om: {
    sv: "Iris väljer den produkt som passar varje bolag bäst och skriver bara om den. Segmenten söks i den ordning de står.",
    en: "Iris picks the product that fits each company best and writes only about that one. Segments are searched in the order listed."
  },
  produkter: { sv: "Produkter", en: "Products" },
  produkt: { sv: "Produkt", en: "Product" },
  namn: { sv: "Namn", en: "Name" },
  nytta: { sv: "Nyttan för kunden", en: "The benefit to the customer" },
  laggTillProdukt: { sv: "Lägg till produkt", en: "Add product" },
  segment: { sv: "Målsegment, bäst först", en: "Target segments, best first" },
  segmentNamn: { sv: "Segment", en: "Segment" },
  bransch: { sv: "Bransch", en: "Industry" },
  varfor: { sv: "Varför de passar", en: "Why they fit" },
  laggTillSegment: { sv: "Lägg till segment", en: "Add segment" },
  offentlig: { sv: "Vi säljer till offentlig sektor och skolor", en: "We sell to the public sector and schools" },
  offentligHjalp: { sv: "Annars väljer Iris bara privata bolag.", en: "Otherwise Iris only picks private companies." },
  upp: { sv: "Flytta upp", en: "Move up" },
  ned: { sv: "Flytta ned", en: "Move down" },
  taBort: { sv: "Ta bort", en: "Remove" },
  borttagen: { sv: "borttagen.", en: "removed." },
  angra: { sv: "Ångra", en: "Undo" },
  spara: { sv: "Spara produkter och målgrupp", en: "Save products and target group" },
  sparar: { sv: "Sparar…", en: "Saving…" },
  sparat: { sv: "Sparat. Gäller från nästa körning.", en: "Saved. Applies from the next run." },
  hamtaFel: { sv: "Inställningarna kunde inte hämtas, så inget kan sparas här just nu:", en: "The settings could not be loaded, so nothing can be saved here right now:" },
  forsokIgen: { sv: "Försök igen", en: "Try again" }
} satisfies Record<string, Localized>;

const falt = "focus-ring w-full rounded-input border border-ink/15 bg-paper px-3 py-2.5 text-[16px] leading-6";

let nastaId = 0;
const nyttId = () => `rad-${++nastaId}`;

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
  const [laddfel, setLaddfel] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [fel, setFel] = useState<string | null>(null);
  const [status, setStatus] = useState("");
  const [borttagen, setBorttagen] = useState<Borttagen | null>(null);
  // Fokus efter en ändring: elementets id, satt före render och läst efter.
  const fokusEfter = useRef<string | null>(null);

  useEffect(() => {
    if (!fokusEfter.current) return;
    document.getElementById(fokusEfter.current)?.focus();
    fokusEfter.current = null;
  });

  const hamta = useCallback(() => {
    setLaddfel(null);
    setProdukter(null);
    leadsAnrop<Config>("/leads/config")
      .then((c) => {
        setProdukter((c.produkter ?? []).map((p) => ({ ...p, id: nyttId() })));
        setSegment((c.segment ?? []).map((s) => ({ ...s, id: nyttId() })));
        setOffentlig(Boolean(c.offentlig_sektor));
      })
      .catch((orsak) => setLaddfel(felmeddelande(orsak)));
  }, []);

  useEffect(() => {
    hamta();
  }, [hamta]);

  async function spara() {
    if (busy || !produkter) return;
    setBusy(true);
    setFel(null);
    setStatus("");
    try {
      await leadsAnrop<Config>("/leads/config", {
        method: "PUT",
        body: JSON.stringify({
          produkter: produkter.filter((p) => p.namn.trim()).map(({ namn, nytta }) => ({ namn, nytta })),
          segment: segment.filter((s) => s.bransch.trim()).map(({ bransch, varfor }) => ({ bransch, varfor })),
          offentlig_sektor: offentlig
        })
      });
      setBorttagen(null);
      setStatus(text(T.sparat));
    } catch (orsak) {
      setFel(felmeddelande(orsak));
    } finally {
      setBusy(false);
    }
  }

  if (laddfel) {
    return (
      <div role="alert" className="grid gap-3">
        <p className="max-w-[62ch] text-[0.9375rem] leading-6 text-danger">
          {text(T.hamtaFel)} {laddfel}
        </p>
        <button type="button" onClick={hamta} className={cn(btnSecondary, "justify-self-start")}>
          {text(T.forsokIgen)}
        </button>
      </div>
    );
  }
  if (produkter === null) {
    return <div className="h-48 animate-pulse rounded-card bg-ink/[0.055]" aria-busy="true" />;
  }

  function taBortProdukt(i: number) {
    if (!produkter) return;
    const rad = produkter[i];
    const kvar = produkter.filter((_, j) => j !== i);
    setProdukter(kvar);
    setBorttagen({ typ: "produkt", rad, plats: i });
    setStatus(`${rad.namn || text(T.produkt)} ${text(T.borttagen)}`);
    fokusEfter.current = kvar[Math.min(i, kvar.length - 1)] ? `produkt-namn-${kvar[Math.min(i, kvar.length - 1)].id}` : "lagg-till-produkt";
  }

  function taBortSegment(i: number) {
    const rad = segment[i];
    const kvar = segment.filter((_, j) => j !== i);
    setSegment(kvar);
    setBorttagen({ typ: "segment", rad, plats: i });
    setStatus(`${rad.bransch || text(T.segmentNamn)} ${text(T.borttagen)}`);
    fokusEfter.current = kvar[Math.min(i, kvar.length - 1)] ? `segment-bransch-${kvar[Math.min(i, kvar.length - 1)].id}` : "lagg-till-segment";
  }

  function angra() {
    if (!borttagen || !produkter) return;
    if (borttagen.typ === "produkt") {
      const ny = [...produkter];
      ny.splice(borttagen.plats, 0, borttagen.rad);
      setProdukter(ny);
      fokusEfter.current = `produkt-namn-${borttagen.rad.id}`;
    } else {
      const ny = [...segment];
      ny.splice(borttagen.plats, 0, borttagen.rad);
      setSegment(ny);
      fokusEfter.current = `segment-bransch-${borttagen.rad.id}`;
    }
    setBorttagen(null);
    setStatus("");
  }

  function flyttaSegment(i: number, steg: number) {
    const ny = flytta(segment, i, steg);
    if (ny === segment) return;
    setSegment(ny);
    const plats = i + steg;
    const namn = segment[i].bransch || `${text(T.segmentNamn)} ${i + 1}`;
    setStatus(text({ sv: `${namn} flyttad till plats ${plats + 1} av ${ny.length}.`, en: `${namn} moved to position ${plats + 1} of ${ny.length}.` }));
    // Fokus följer raden; vid kanten byts till den andra pilen, som går att trycka.
    const kant = plats === 0 || plats === ny.length - 1;
    fokusEfter.current = `segment-${kant ? (steg < 0 ? "ned" : "upp") : steg < 0 ? "upp" : "ned"}-${segment[i].id}`;
  }

  const segmentNamn = (s: Segment, i: number) => s.bransch || `${text(T.segmentNamn)} ${i + 1}`;
  const lastKnapp = (villkor: boolean) => ({ "aria-disabled": villkor || undefined });

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
        <ol className="grid gap-4">
          {produkter.map((p, i) => (
            <li
              key={p.id}
              className="grid gap-3 border-t border-ink/12 pt-4 sm:grid-cols-[minmax(0,14rem)_minmax(0,1fr)_auto] sm:items-end"
            >
              <label className="grid gap-1">
                <span className={meta}>{text(T.namn)}</span>
                <input
                  id={`produkt-namn-${p.id}`}
                  value={p.namn}
                  maxLength={80}
                  onChange={(e) => setProdukter(produkter.map((x) => (x.id === p.id ? { ...x, namn: e.target.value } : x)))}
                  className={falt}
                />
              </label>
              <label className="grid gap-1">
                <span className={meta}>{text(T.nytta)}</span>
                <input
                  value={p.nytta}
                  maxLength={400}
                  onChange={(e) => setProdukter(produkter.map((x) => (x.id === p.id ? { ...x, nytta: e.target.value } : x)))}
                  className={falt}
                />
              </label>
              <button
                type="button"
                onClick={() => taBortProdukt(i)}
                className={cn(btnSecondary, btnLiten, "justify-self-start")}
                aria-label={`${text(T.taBort)}: ${p.namn || `${text(T.produkt)} ${i + 1}`}`}
              >
                <Trash2 className="h-4 w-4" aria-hidden />
              </button>
            </li>
          ))}
        </ol>
        {produkter.length < MAX_PRODUKTER ? (
          <button
            id="lagg-till-produkt"
            type="button"
            onClick={() => {
              const rad = { id: nyttId(), namn: "", nytta: "" };
              setProdukter([...produkter, rad]);
              fokusEfter.current = `produkt-namn-${rad.id}`;
            }}
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
              key={s.id}
              className="grid gap-3 border-t border-ink/12 pt-4 sm:grid-cols-[2rem_minmax(0,14rem)_minmax(0,1fr)_auto] sm:items-end"
            >
              <span className="num pb-3 text-[0.9375rem] text-ink-muted" aria-hidden>
                {i + 1}
              </span>
              <label className="grid gap-1">
                <span className={meta}>{text(T.bransch)}</span>
                <input
                  id={`segment-bransch-${s.id}`}
                  value={s.bransch}
                  maxLength={80}
                  onChange={(e) => setSegment(segment.map((x) => (x.id === s.id ? { ...x, bransch: e.target.value } : x)))}
                  className={falt}
                />
              </label>
              <label className="grid gap-1">
                <span className={meta}>{text(T.varfor)}</span>
                <input
                  value={s.varfor}
                  maxLength={240}
                  onChange={(e) => setSegment(segment.map((x) => (x.id === s.id ? { ...x, varfor: e.target.value } : x)))}
                  className={falt}
                />
              </label>
              <div className="flex gap-2">
                <button
                  id={`segment-upp-${s.id}`}
                  type="button"
                  {...lastKnapp(i === 0)}
                  onClick={() => flyttaSegment(i, -1)}
                  className={cn(btnSecondary, btnLiten, "aria-disabled:opacity-40")}
                  aria-label={`${text(T.upp)}: ${segmentNamn(s, i)}`}
                >
                  <ArrowUp className="h-4 w-4" aria-hidden />
                </button>
                <button
                  id={`segment-ned-${s.id}`}
                  type="button"
                  {...lastKnapp(i === segment.length - 1)}
                  onClick={() => flyttaSegment(i, 1)}
                  className={cn(btnSecondary, btnLiten, "aria-disabled:opacity-40")}
                  aria-label={`${text(T.ned)}: ${segmentNamn(s, i)}`}
                >
                  <ArrowDown className="h-4 w-4" aria-hidden />
                </button>
                <button
                  type="button"
                  onClick={() => taBortSegment(i)}
                  className={cn(btnSecondary, btnLiten)}
                  aria-label={`${text(T.taBort)}: ${segmentNamn(s, i)}`}
                >
                  <Trash2 className="h-4 w-4" aria-hidden />
                </button>
              </div>
            </li>
          ))}
        </ol>
        {segment.length < MAX_SEGMENT ? (
          <button
            id="lagg-till-segment"
            type="button"
            onClick={() => {
              const rad = { id: nyttId(), bransch: "", varfor: "" };
              setSegment([...segment, rad]);
              fokusEfter.current = `segment-bransch-${rad.id}`;
            }}
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
          className="focus-ring mt-0.5 size-5 accent-[var(--color-ink)]"
        />
        <span>
          {text(T.offentlig)}
          <span className="block text-ink-muted">{text(T.offentligHjalp)}</span>
        </span>
      </label>

      <div className="flex flex-wrap items-center gap-x-4 gap-y-3">
        <button
          type="button"
          onClick={() => void spara()}
          {...lastKnapp(busy)}
          className={cn(btnPrimary, "aria-disabled:opacity-60")}
        >
          {busy ? text(T.sparar) : text(T.spara)}
        </button>
        {/* Statusregionen renderas alltid, tom från början, så att varje
            ändring annonseras. Ångra ligger bredvid den borttagna radens kvitto. */}
        <span aria-live="polite" className="text-[0.9375rem] text-ink-muted">
          {status}
        </span>
        {borttagen ? (
          <button type="button" onClick={angra} className={cn(btnSecondary, btnLiten)}>
            {text(T.angra)}
          </button>
        ) : null}
        {fel ? (
          <p role="alert" className="max-w-[62ch] break-words text-[0.9375rem] text-danger">
            {fel}
          </p>
        ) : null}
      </div>
    </section>
  );
}
