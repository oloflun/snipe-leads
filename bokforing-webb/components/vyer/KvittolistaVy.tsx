"use client";

import { Download, Loader2, Trash2, Upload } from "lucide-react";
import { useRef, useState } from "react";
import { PageHeader } from "@/components/PageHeader";
import { PeriodValjare } from "@/components/PeriodValjare";
import { Badge, EmptyState, SkeletonRows, btnLiten, btnPrimary, btnSecondary } from "@/components/ui";
import { kronor, procent } from "@/lib/format";
import { HttpJsonError, felmeddelande, readJson } from "@/lib/http/json";
import { KVBAS, LASBARA, type Kvitto, useKvitton } from "@/lib/kvitton";
import { cn } from "@/lib/utils";

/**
 * Kvittolistan — periodens alla kvitton, uppladdningen och exporten.
 *
 * Godkännandet av ett flaggat kvitto går genom backendens grind
 * (`POST /{id}/godkann`): saknas ett fält frågar vyn efter det, och grinden
 * körs IGEN på det rättade kvittot. Ett godkännande är aldrig en väg förbi
 * kontrollen.
 */

function feltext(orsak: unknown): string {
  if (orsak instanceof HttpJsonError) {
    const kropp =
      orsak.body && typeof orsak.body === "object" ? (orsak.body as Record<string, unknown>) : {};
    return (
      (typeof kropp.error === "string" && kropp.error) ||
      (typeof kropp.detail === "string" && kropp.detail) ||
      orsak.message
    );
  }
  return felmeddelande(orsak);
}

export function KvittolistaVy() {
  const { period, kvitton, samman, fel: hamtfel, hamta } = useKvitton();
  const [fel, setFel] = useState<string | null>(null);
  const [laddarUpp, setLaddarUpp] = useState(false);
  const [uppladdningsfel, setUppladdningsfel] = useState<string[]>([]);
  const [rensar, setRensar] = useState(false);
  const filväljare = useRef<HTMLInputElement>(null);

  const harKvitton = (kvitton?.length ?? 0) > 0;

  async function laddaUpp(filer: File[]) {
    if (!filer.length) return;
    setLaddarUpp(true);
    setFel(null);
    setUppladdningsfel([]);
    const misslyckade: string[] = [];
    try {
      for (const fil of filer) {
        try {
          const kropp = new FormData();
          kropp.append("fil", fil);
          const svar = await fetch(`${KVBAS}/underlag`, { method: "POST", body: kropp });
          await readJson(svar);
        } catch (orsak) {
          misslyckade.push(`${fil.name}: ${feltext(orsak)}`);
        }
      }
      setUppladdningsfel(misslyckade);
      await hamta();
    } finally {
      setLaddarUpp(false);
    }
  }

  async function godkann(rad: Kvitto) {
    setFel(null);
    const kropp: Record<string, string> = {};
    if (rad.brutto === null) {
      const belopp = window.prompt(
        rad.belopp_original
          ? `Kvittot är på ${rad.belopp_original}. Ange beloppet omräknat till kronor (t.ex. 495,00):`
          : "Kvittot saknar läsbart belopp. Ange beloppet i kronor (t.ex. 495,00):"
      );
      if (!belopp) return;
      kropp.brutto = belopp.replace(/\s/g, "").replace(",", ".");
    }
    if (rad.momssats === null) {
      const sats = window.prompt("Ange momssatsen i procent (25, 12, 6 eller 0):");
      if (sats === null) return;
      const normaliserad = { "25": "0.25", "12": "0.12", "6": "0.06", "0": "0" }[sats.trim()];
      if (!normaliserad) {
        setFel("Momssatsen ska vara 25, 12, 6 eller 0.");
        return;
      }
      kropp.momssats = normaliserad;
    }
    if (rad.datum === null) {
      const datum = window.prompt("Kvittot saknar datum. Ange köpdatum (ÅÅÅÅ-MM-DD):");
      if (!datum) return;
      kropp.datum = datum.trim();
    }
    if (rad.motpart === null) {
      const motpart = window.prompt("Vilken butik eller leverantör är kvittot från?");
      if (!motpart) return;
      kropp.motpart = motpart.trim();
    }    if (rad.kategori === null) {
      const kategori = window.prompt(
        "Ange kategori: drivmedel, biljett, kost_och_logi, representation, kontorsmateriel, programvara, forbrukningsinventarier eller ovrig_extern_kostnad:"
      );
      if (!kategori) return;
      kropp.kategori = kategori.trim().toLowerCase();
    }
    if (rad.betalstatus === null) {
      // Frågas, gissas aldrig: betalstatus avgör om kvittot bokas mot
      // bankkontot eller som en obetald skuld.
      const betald = window.confirm(
        "Är kvittot redan betalt?\n\nOK = betalt (kort, Swish, kontant)\nAvbryt = obetald faktura"
      );
      kropp.betalstatus = betald ? "betald" : "obetald";
    }
    try {
      const svar = await fetch(`${KVBAS}/${rad.id}/godkann`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(kropp)
      });
      const data = await readJson<{ godkand: boolean; brister?: string[] }>(svar);
      if (data && !data.godkand) {
        setFel(
          `Kvittot kunde inte godkännas ännu: ${(data.brister ?? []).join("; ") || "fält saknas."}`
        );
      }
      await hamta();
    } catch (orsak) {
      setFel(feltext(orsak));
    }
  }

  async function rensa() {
    if (!harKvitton) return;
    const bekraftat = window.confirm(
      `Rensa ${period.fran} till ${period.till}?\n\n` +
        `${kvitton?.length ?? 0} kvitton raderas. Det går inte att ångra.`
    );
    if (!bekraftat) return;
    setRensar(true);
    setFel(null);
    try {
      const svar = await fetch(`${KVBAS}/period?fran=${period.fran}&till=${period.till}`, {
        method: "DELETE"
      });
      await readJson(svar);
      await hamta();
    } catch (orsak) {
      setFel(feltext(orsak));
    } finally {
      setRensar(false);
    }
  }

  return (
    <div className="space-y-8">
      <PageHeader
        rubrik="Kvitton"
        beskrivning="Periodens alla kvitton — ur mejlen och uppladdade. Flaggade rader räknas inte in i summorna förrän du godkänt dem."
        actions={
          <>
            <PeriodValjare />
            <button
              type="button"
              disabled={laddarUpp}
              onClick={() => filväljare.current?.click()}
              className={cn(btnPrimary, btnLiten)}
            >
              {laddarUpp ? (
                <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
              ) : (
                <Upload className="h-4 w-4" aria-hidden />
              )}
              Ladda upp
            </button>
            <a
              href={
                harKvitton
                  ? `${KVBAS}/export.csv?fran=${period.fran}&till=${period.till}`
                  : undefined
              }
              aria-disabled={!harKvitton}
              title={harKvitton ? undefined : "Det finns inga kvitton att exportera."}
              className={cn(btnSecondary, btnLiten, !harKvitton && "pointer-events-none opacity-40")}
            >
              <Download className="h-4 w-4" aria-hidden />
              Exportera
            </a>
            <button
              type="button"
              disabled={rensar || !harKvitton}
              onClick={() => void rensa()}
              title={harKvitton ? undefined : "Det finns inget att rensa i perioden."}
              className={cn(btnSecondary, btnLiten)}
            >
              {rensar ? (
                <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
              ) : (
                <Trash2 className="h-4 w-4" aria-hidden />
              )}
              Rensa
            </button>
          </>
        }
      />

      {fel || hamtfel ? (
        <p role="alert" className="max-w-[70ch] text-[0.875rem] text-danger">
          {fel ?? hamtfel}
        </p>
      ) : null}

      {uppladdningsfel.length ? (
        <div role="status" className="max-w-[78ch] border-y border-ink/15 py-3">
          <p className="text-[0.9375rem] font-semibold text-ink">
            {uppladdningsfel.length}{" "}
            {uppladdningsfel.length === 1 ? "fil kom" : "filer kom"} inte in
          </p>
          <ul className="mt-2 space-y-1">
            {uppladdningsfel.map((rad, i) => (
              <li key={i} className="text-[0.875rem] text-ink/62">
                {rad}
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      {samman && samman.antal > 0 ? (
        <p className="text-[0.875rem] text-ink/60">
          <span className="num font-medium text-ink">{kronor(samman.totalt)}</span> i{" "}
          {samman.antal_klara} avlästa kvitton · ingående moms{" "}
          <span className="num">{kronor(samman.moms)}</span>
          {samman.antal_granska > 0 ? (
            <>
              {" "}
              · <span className="text-ink">{samman.antal_granska} att granska</span>
            </>
          ) : null}
        </p>
      ) : null}

      {kvitton === null ? (
        <SkeletonRows />
      ) : kvitton.length === 0 ? (
        <EmptyState
          title="Inga kvitton i perioden"
          body="Skanna inkorgen eller ladda upp ett kvitto, så läser agenten av belopp, moms, datum och kategori."
        />
      ) : (
        <div className="thin-scrollbar overflow-x-auto">
          <table className="w-full table-fixed border-collapse text-[15px]" style={{ minWidth: "760px" }}>
            <colgroup>
              <col style={{ width: "12%" }} />
              <col style={{ width: "32%" }} />
              <col style={{ width: "15%" }} />
              <col style={{ width: "11%" }} />
              <col style={{ width: "7%" }} />
              <col style={{ width: "12%" }} />
              <col style={{ width: "11%" }} />
            </colgroup>
            <thead>
              <tr className="border-b border-ink/15 text-left">
                {["Datum", "Butik", "Kategori", "Källa"].map((rubrik) => (
                  <th key={rubrik} className="py-3 pr-4 text-[0.75rem] font-medium uppercase tracking-[0.1em] text-mineral">
                    {rubrik}
                  </th>
                ))}
                {["Moms", "Belopp", "Status"].map((rubrik) => (
                  <th key={rubrik} className="py-3 pr-4 text-right text-[0.75rem] font-medium uppercase tracking-[0.1em] text-mineral last:pr-0">
                    {rubrik}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-ink/12 border-b border-ink/15">
              {kvitton.map((rad) => (
                <tr key={rad.id} className="transition-colors hover:bg-paper2/60">
                  <td className="py-3.5 pr-4 align-top">
                    <span className="tabular-nums text-ink/62">{rad.datum ?? "—"}</span>
                  </td>
                  <td className="min-w-0 py-3.5 pr-4 align-top">
                    <p className="truncate">{rad.motpart || rad.mejl_amne || rad.filnamn}</p>
                    {rad.anmarkning ? (
                      <p className="mt-1 text-[0.8125rem] text-ink/55">{rad.anmarkning}</p>
                    ) : null}
                  </td>
                  <td className="py-3.5 pr-4 align-top">
                    <span className="text-[0.875rem] text-ink/62">{rad.kategorietikett}</span>
                  </td>
                  <td className="py-3.5 pr-4 align-top">
                    <span className="text-[0.875rem] text-ink/62">
                      {rad.kalla === "mejl" ? "Mejl" : "Uppladdad"}
                    </span>
                  </td>
                  <td className="py-3.5 pr-4 text-right align-top">
                    <span className="text-[0.875rem] text-ink/62">{procent(rad.momssats)}</span>
                  </td>
                  <td className="num py-3.5 pr-4 text-right align-top">
                    <span className="font-medium">
                      {rad.brutto !== null ? kronor(rad.brutto) : (rad.belopp_original ?? "—")}
                    </span>
                  </td>
                  <td className="py-3.5 text-right align-top">
                    <span className="flex flex-wrap items-center justify-end gap-1.5">
                      <Badge tone={rad.status === "granska_manuellt" ? "warn" : "good"}>
                        {rad.status === "granska_manuellt" ? "Granska" : "Klar"}
                      </Badge>
                      {rad.status === "granska_manuellt" ? (
                        <button
                          type="button"
                          onClick={() => void godkann(rad)}
                          className="focus-ring rounded-[4px] text-[0.8125rem] font-medium text-ink underline underline-offset-4 hover:text-ochre"
                        >
                          Godkänn
                        </button>
                      ) : null}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <input
        ref={filväljare}
        type="file"
        multiple
        accept={LASBARA}
        onChange={(e) => {
          void laddaUpp(Array.from(e.target.files ?? []));
          e.target.value = "";
        }}
        className="sr-only"
      />
    </div>
  );
}
