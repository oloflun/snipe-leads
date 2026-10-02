"use client";

import { useMemo, useState, useTransition } from "react";
import { Sektion, btnPrimary, btnSecondary, etikett } from "@/components/ui";
import {
  konverteraTestkund,
  type KonverteraRapport
} from "@/lib/actions/konvertera";
import { a, ordagrant } from "@/lib/admin/sprak";
import { useLocale, type Localized } from "@/lib/i18n";

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
  const [fel, setFel] = useState<Localized | null>(null);
  const [pending, start] = useTransition();
  const { locale, text } = useLocale();

  const valda = useMemo(() => mal.find((m) => m.slug === till), [mal, till]);

  const kora = (apply: boolean) => {
    if (!till) return;
    start(async () => {
      setFel(null);
      const svar = await konverteraTestkund({ fran, till, apply });
      if (svar.error) {
        setFel(ordagrant(svar.error));
        return;
      }
      setRapport(svar.rapport ?? null);
    });
  };

  if (!fran.startsWith("testkund-")) {
    return null;
  }

  return (
    <Sektion title={a("flyttaTillRiktigt", locale)}>
      <label className={`block ${etikett}`}>
        {a("malkonto", locale)}
        <select
          value={till}
          onChange={(event) => {
            setTill(event.target.value);
            setRapport(null);
          }}
          className="focus-ring mt-2 block min-h-11 w-full max-w-md rounded-input bg-paper2 px-3 text-[1rem] text-ink"
        >
          {mal.length === 0 ? <option value="">{a("ingaRiktigaKonton", locale)}</option> : null}
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
          {pending ? a("kor", locale) : a("visaVadSomFlyttas", locale)}
        </button>
        {rapport && !rapport.apply ? (
          <button
            type="button"
            disabled={pending || !till}
            onClick={() => kora(true)}
            className={btnPrimary}
          >
            {a("skrivOver", locale)} {valda?.name ?? till}
          </button>
        ) : null}
      </div>

      {fel ? (
        <p role="alert" className="mt-4 text-[0.9375rem] text-danger">
          {text(fel)}
        </p>
      ) : null}

      {rapport ? (
        <div className="mt-6 max-w-[70ch] border-y border-ink/15 py-4 text-[0.9375rem] leading-7">
          <p>{rapport.meddelande}</p>
          {rapport.kunskapsbas ? (
            <ul className="mt-3 space-y-1 text-ink-muted">
              <li>
                {a("kunskapsbasKolon", locale)} {rapport.kunskapsbas.till} {a("raderIMaletRaderas", locale)}{" "}
                {rapport.kunskapsbas.fran} {a("kopieras", locale)}
              </li>
              <li>
                {a("rostdokumentKolon", locale)} {rapport.rostdokument?.till ?? 0} {a("raderas", locale)}{" "}
                {rapport.rostdokument?.fran ?? 0} {a("kopieras", locale)}
              </li>
              <li>
                {a("fackreglerKolon", locale)} {rapport.fackregler?.till ?? 0} {a("raderas", locale)}{" "}
                {rapport.fackregler?.fran ?? 0} {a("kopieras", locale)}
              </li>
            </ul>
          ) : null}
        </div>
      ) : null}
    </Sektion>
  );
}
