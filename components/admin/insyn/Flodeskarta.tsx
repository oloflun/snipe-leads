"use client";

import { Fragment } from "react";

import { etikett, meta } from "@/components/ui";
import { a } from "@/lib/admin/sprak";
import type { InsynBana, InsynGrind, InsynSteg } from "@/lib/data/admin";
import { useLocale } from "@/lib/i18n";
import { cn } from "@/lib/utils";

/**
 * Flödeskartan (Fas 7). Varje bana är en playbook ur koden med sina steg i
 * körordning; kodgrindarna står som egna noder mellan dem. Kartan ritas ur
 * backendens `banor`, som byggs ur Playbook-objekten (app/agentcore/insyn.py)
 * — här finns ingen egen lista över steg.
 *
 * En nod är en knapp: valet visar stegets lager under kartan. Med en vald
 * körning färgas noderna efter utfall (kördes, släppt, fälld, stoppad,
 * hoppades över, nåddes inte). Färgen står aldrig ensam: utfallet står i
 * text i noden, för den som inte ser färgen.
 */

export type Utfall = "kord" | "slappt" | "falld" | "stoppad" | "hoppad" | "ej_nadd" | "okant";

const UTFALL_KANT: Record<Utfall, string> = {
  kord: "border-moss",
  slappt: "border-moss",
  falld: "border-danger",
  stoppad: "border-danger",
  hoppad: "border-dashed border-ink/30",
  ej_nadd: "border-dashed border-ink/20",
  okant: "border-ink/30"
};

const UTFALL_TEXT: Record<Utfall, string> = {
  kord: "text-moss",
  slappt: "text-moss",
  falld: "text-danger",
  stoppad: "text-danger",
  hoppad: "text-ink-subtle",
  ej_nadd: "text-ink-subtle",
  okant: "text-ink-muted"
};

function Nod({
  nod,
  vald,
  utfall,
  onValj
}: Readonly<{
  nod: InsynSteg | InsynGrind;
  vald: boolean;
  utfall?: Utfall;
  onValj: (id: string) => void;
}>) {
  const { locale } = useLocale();
  const grind = nod.typ === "grind";
  return (
    <button
      type="button"
      onClick={() => onValj(nod.id)}
      aria-pressed={vald}
      title={grind ? nod.kod : undefined}
      className={cn(
        "focus-ring flex min-h-[4.5rem] w-44 shrink-0 flex-col items-start justify-between gap-1 rounded-input border-2 px-3 py-2 text-left transition-colors",
        grind ? "bg-paper2" : "bg-paper",
        utfall ? UTFALL_KANT[utfall] : grind ? "border-dashed border-ink/25" : "border-ink/15",
        vald && "ring-2 ring-ochre ring-offset-2 ring-offset-paper",
        "hover:bg-paper2"
      )}
    >
      <span className={cn(etikett, "text-[0.75rem]")}>
        {grind ? a("kodgrind", locale) : `${a("steg", locale)} ${Number(nod.id.split(":")[1]) + 1}`}
      </span>
      <span className={cn("min-w-0 break-all text-[0.8125rem] font-medium text-ink", !grind && "font-mono")}>
        {grind ? a(`grind_${nod.grind}`, locale) : nod.skill}
      </span>
      {!grind ? (
        <span className={cn(meta, "text-[0.75rem]")}>
          {a(nod.laddning === "hel" ? "insynHel" : "insynSkopa", locale)}
          {nod.villkor ? ` · ${a("insynVillkor", locale).toLowerCase()}` : ""}
        </span>
      ) : null}
      {utfall ? (
        <span className={cn("text-[0.75rem] font-medium", UTFALL_TEXT[utfall])}>{a(`utfall_${utfall}`, locale)}</span>
      ) : null}
    </button>
  );
}

export function Flodeskarta({
  banor,
  vald,
  utfall,
  onValj
}: Readonly<{
  banor: InsynBana[];
  vald: string | null;
  utfall: Record<string, Utfall>;
  onValj: (id: string) => void;
}>) {
  const { locale } = useLocale();
  return (
    <div role="group" aria-label={a("insynKartaAria", locale)} className="space-y-5">
      {banor.map((bana) => (
        <section key={bana.id} aria-label={a(`bana_${bana.id}`, locale)} className="min-w-0">
          <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
            <h3 className="text-[0.9375rem] font-semibold text-ink">{a(`bana_${bana.id}`, locale)}</h3>
            {bana.villkor ? <p className={meta}>{a(`banaVillkor_${bana.villkor}`, locale)}</p> : null}
          </div>
          {/* Banan scrollar i sidled på smala skärmar i stället för att trycka
              sidan bred: kartan är en rad i körordning och ska läsas som en. */}
          <ol className="thin-scrollbar mt-2 flex items-center overflow-x-auto pb-2">
            {bana.noder.map((nod, i) => (
              <Fragment key={nod.id}>
                {i > 0 ? <li aria-hidden className="h-0.5 w-4 shrink-0 bg-ink/25" /> : null}
                <li className="shrink-0">
                  <Nod nod={nod} vald={vald === nod.id} utfall={utfall[nod.id]} onValj={onValj} />
                </li>
              </Fragment>
            ))}
          </ol>
        </section>
      ))}
    </div>
  );
}
