"use client";

import { Download, Loader2, ScanLine, Trash2 } from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import { PageHeader } from "@/components/PageHeader";
import { PeriodValjare } from "@/components/PeriodValjare";
import { Badge, EmptyState, SkeletonRows, btnLiten, btnPrimary, btnSecondary } from "@/components/ui";
import { BAS } from "@/lib/api";
import { kronor, procent } from "@/lib/format";
import { felmeddelande, readJson } from "@/lib/http/json";
import { useProfil } from "@/lib/profil";
import { useBokforing } from "@/lib/useBokforing";
import { cn } from "@/lib/utils";

/**
 * Alla uppladdade dokument i perioden, med exporten och rensningen.
 *
 * SIE-exporten är en VANLIG länk, inte fetch: filen ska sparas, inte visas,
 * och webbläsaren gör nedladdningen bättre än vi gör den. Företagsnamn och
 * orgnr i filhuvudet kommer ur profilen under Inställningar.
 *
 * Rensningen är äkta radering — originalfilerna finns inte kvar (bara
 * sha256 sparades), så det som försvinner går bara att få tillbaka genom att
 * läsa av kvittona på nytt. Därav window.confirm.
 */
export function DokumentVy() {
  const { period, underlag, rapport, fel, hamta } = useBokforing();
  const { profil } = useProfil();
  const [rensar, setRensar] = useState(false);
  const [rensfel, setRensfel] = useState<string | null>(null);

  const laddar = underlag === null && !fel;
  const harUnderlag = (underlag?.length ?? 0) > 0;
  const klar = rapport?.status === "klar";

  const exportUrl =
    `${BAS}/period.sie?fran=${period.fran}&till=${period.till}` +
    `&foretagsnamn=${encodeURIComponent(profil.foretagsnamn || "Företaget")}` +
    `&orgnr=${encodeURIComponent(profil.orgnr)}`;

  async function rensa() {
    if (!harUnderlag) return;
    const bekraftat = window.confirm(
      `Rensa ${period.fran} till ${period.till}?\n\n` +
        `${underlag?.length ?? 0} underlag och deras konteringar raderas. Det går inte att ångra.`
    );
    if (!bekraftat) return;
    setRensar(true);
    setRensfel(null);
    try {
      const svar = await fetch(`${BAS}/period?fran=${period.fran}&till=${period.till}`, {
        method: "DELETE"
      });
      await readJson(svar);
      await hamta();
    } catch (orsak) {
      setRensfel(felmeddelande(orsak));
    } finally {
      setRensar(false);
    }
  }

  return (
    <div className="space-y-8">
      <PageHeader
        rubrik="PDF-filer"
        beskrivning="Periodens uppladdade underlag med de avlästa fälten. Själva filerna sparas aldrig — det som listas är vad agenten läste ur dem."
        actions={<PeriodValjare />}
      />

      {fel ? (
        <p role="alert" className="max-w-[70ch] text-[0.875rem] text-danger">
          {fel}
        </p>
      ) : null}
      {rensfel ? (
        <p role="alert" className="max-w-[70ch] text-[0.875rem] text-danger">
          {rensfel}
        </p>
      ) : null}

      <section>
        <div className="flex flex-wrap items-center justify-between gap-x-4 gap-y-3">
          <h2 className="font-display text-[1.25rem]">
            {harUnderlag ? `${underlag?.length} dokument i perioden` : "Dokument"}
          </h2>
          <div className="flex flex-wrap items-center gap-2">
            <Link href="/agenten" className={cn(btnPrimary, btnLiten)}>
              <ScanLine className="h-4 w-4" aria-hidden />
              Ladda upp
            </Link>
            <a
              href={klar ? exportUrl : undefined}
              aria-disabled={!klar}
              title={
                klar
                  ? "Ladda ner perioden som SIE4-fil för ditt bokföringsprogram."
                  : "Perioden går inte ihop och kan inte exporteras ännu."
              }
              className={cn(btnSecondary, btnLiten, !klar && "pointer-events-none opacity-40")}
            >
              <Download className="h-4 w-4" aria-hidden />
              Exportera SIE
            </a>
            <button
              type="button"
              disabled={rensar || !harUnderlag}
              onClick={() => void rensa()}
              title={harUnderlag ? undefined : "Det finns inget att rensa i perioden."}
              className={cn(btnSecondary, btnLiten)}
            >
              {rensar ? (
                <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
              ) : (
                <Trash2 className="h-4 w-4" aria-hidden />
              )}
              Rensa perioden
            </button>
          </div>
        </div>

        {!profil.orgnr && harUnderlag ? (
          <p className="mt-3 max-w-[70ch] text-[0.8125rem] leading-5 text-ink/50">
            Tips: fyll i företagsnamn och organisationsnummer under{" "}
            <Link href="/installningar" className="focus-ring rounded-[4px] underline decoration-ochre/50 underline-offset-4">
              Inställningar
            </Link>
            , så hamnar de i SIE-filens huvud.
          </p>
        ) : null}

        {laddar ? (
          <div className="mt-4">
            <SkeletonRows />
          </div>
        ) : !harUnderlag ? (
          <div className="mt-4">
            <EmptyState
              title="Inga dokument i perioden"
              body="Ladda upp ett kvitto eller en faktura hos Bokföringsagenten, så läses det av och hamnar här."
            />
          </div>
        ) : (
          <div className="mt-4 divide-y divide-ink/12 border-y border-ink/15">
            {(underlag ?? []).map((rad) => (
              <div key={rad.id} className="flex flex-wrap items-baseline gap-x-4 gap-y-1 py-3">
                <span className="num w-[6.5rem] shrink-0 text-[0.9375rem] text-ink/62">
                  {rad.datum ?? "—"}
                </span>
                <span className="min-w-0 flex-1 truncate text-[0.9375rem]" title={rad.filnamn}>
                  {rad.motpart || rad.filnamn}
                </span>
                <span className="text-[0.9375rem] text-ink/62">{procent(rad.momssats)}</span>
                <span className="num w-[7.5rem] text-right text-[0.9375rem] font-medium">
                  {kronor(rad.brutto)}
                </span>
                {rad.betalstatus === "obetald" ? <Badge tone="warn">Obetald</Badge> : null}
                <Badge tone={rad.status === "granska_manuellt" ? "warn" : "good"}>
                  {rad.status === "granska_manuellt" ? "Granska" : "Klar"}
                </Badge>
                {rad.anmarkning ? (
                  <p className="w-full text-[0.875rem] text-ink/55">{rad.anmarkning}</p>
                ) : null}
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
