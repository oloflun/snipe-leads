"use client";

import { useMemo, useState, useTransition } from "react";
import { Sektion, btnPrimary, btnSecondary, etikett } from "@/components/ui";
import {
  konverteraTestkund,
  type KonverteraRapport
} from "@/lib/actions/konvertera";

type Mal = { slug: string; name: string };

/**
 * Flyttar en testkunds inställningar till ett riktigt konto. Default är
 * torrkörning — apply skriver över målets kunskapsbas, röst och regler.
 * Ärenden och mail följer inte med.
 *
 * Ingressen under rubriken togs bort 2026-09-27 (F-016). Det den varnade för
 * säger flödet självt: torrkörningens besked räknar upp vad som skrivs över,
 * knappen heter "Skriv över <mål>", och kvittot efter flytten säger att
 * ärenden, mail och körningar inte kopierades.
 */
export function KonverteraTestkund({
  fran,
  mal
}: Readonly<{ fran: string; mal: Mal[] }>) {
  const [till, setTill] = useState(mal[0]?.slug ?? "");
  const [rapport, setRapport] = useState<KonverteraRapport | null>(null);
  const [fel, setFel] = useState<string | null>(null);
  const [pending, start] = useTransition();

  const valda = useMemo(() => mal.find((m) => m.slug === till), [mal, till]);

  const kora = (apply: boolean) => {
    if (!till) return;
    start(async () => {
      setFel(null);
      const svar = await konverteraTestkund({ fran, till, apply });
      if (svar.error) {
        setFel(svar.error);
        return;
      }
      setRapport(svar.rapport ?? null);
    });
  };

  if (!fran.startsWith("testkund-")) {
    return null;
  }

  return (
    <Sektion title="Flytta till riktigt konto">
      <label className={`block ${etikett}`}>
        Målkonto
        <select
          value={till}
          onChange={(event) => {
            setTill(event.target.value);
            setRapport(null);
          }}
          className="focus-ring mt-2 block min-h-11 w-full max-w-md rounded-input bg-paper2 px-3 text-[1rem] text-ink"
        >
          {mal.length === 0 ? <option value="">Inga riktiga konton att flytta till</option> : null}
          {mal.map((m) => (
            <option key={m.slug} value={m.slug}>
              {m.name} ({m.slug})
            </option>
          ))}
        </select>
      </label>

      <div className="mt-4 flex flex-wrap gap-2">
        <button
          type="button"
          disabled={pending || !till}
          onClick={() => kora(false)}
          className={btnSecondary}
        >
          {pending ? "Kör…" : "Visa vad som skulle flyttas"}
        </button>
        {rapport && !rapport.apply ? (
          <button
            type="button"
            disabled={pending || !till}
            onClick={() => kora(true)}
            className={btnPrimary}
          >
            Skriv över {valda?.name ?? till}
          </button>
        ) : null}
      </div>

      {fel ? (
        <p role="alert" className="mt-4 text-[0.9375rem] text-danger">
          {fel}
        </p>
      ) : null}

      {rapport ? (
        <div className="mt-6 max-w-[70ch] border-y border-ink/15 py-4 text-[0.9375rem] leading-7">
          <p>{rapport.meddelande}</p>
          {rapport.kunskapsbas ? (
            <ul className="mt-3 space-y-1 text-ink-muted">
              <li>
                Kunskapsbas: {rapport.kunskapsbas.till} rader i målet raderas,{" "}
                {rapport.kunskapsbas.fran} kopieras.
              </li>
              <li>
                Röstdokument: {rapport.rostdokument?.till ?? 0} raderas,{" "}
                {rapport.rostdokument?.fran ?? 0} kopieras.
              </li>
              <li>
                Fackregler: {rapport.fackregler?.till ?? 0} raderas,{" "}
                {rapport.fackregler?.fran ?? 0} kopieras.
              </li>
            </ul>
          ) : null}
        </div>
      ) : null}
    </Sektion>
  );
}
