"use client";

import { Badge, etikett, meta } from "@/components/ui";
import { a, antal } from "@/lib/admin/sprak";
import type { Insyn } from "@/lib/data/admin";
import { useLocale } from "@/lib/i18n";
import { cn } from "@/lib/utils";

/**
 * Källmatrisen (Fas 7): varje underlag mot varje steg. Cellen säger om texten
 * läses där, i vilken position och hur många tecken. Rött betyder antingen att
 * ett ifyllt underlag inte når något steg (raden), eller att ett steg kräver
 * ett underlag som är tomt (cellen). Klick på en cell öppnar stegets prompt
 * med stycket markerat.
 *
 * Egen tabell och inte `Tabell`: kolumnerna är stegen, och en kedja har upp
 * till tjugo. Fasta procentbredder hade gett tio pixlar per kolumn; här får
 * varje kolumn sin minsta läsbara bredd och tabellen scrollar i sidled.
 */
export function Kallmatris({
  matris,
  onValj
}: Readonly<{ matris: Insyn["matris"]; onValj: (steg: string, hash: string | null) => void }>) {
  const { locale } = useLocale();
  return (
    <div>
      <div className="thin-scrollbar overflow-x-auto">
        <table aria-label={a("insynMatrisAria", locale)} className="border-collapse text-[0.8125rem]">
          <thead>
            <tr className="border-b border-ink/15 text-left">
              <th scope="col" className={cn(etikett, "sticky left-0 z-10 min-w-[12rem] bg-paper py-2 pr-4")}>
                {a("insynUnderlag", locale)}
              </th>
              {matris.kolumner.map((k) => (
                <th key={k.id} scope="col" className={cn(etikett, "min-w-[6.5rem] px-2 py-2 align-bottom font-normal")}>
                  <span className="block font-mono text-[0.75rem] text-ink-muted">{k.id}</span>
                  <span className="block break-all font-mono text-[0.75rem] text-ink">{k.skill}</span>
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-ink/12 border-b border-ink/15">
            {matris.rader.map((rad) => (
              <tr key={rad.id} className={cn(rad.dott && "bg-danger/5")}>
                <th scope="row" className="sticky left-0 z-10 bg-paper py-2 pr-4 text-left align-top font-normal">
                  <span className="block font-medium text-ink">{a(`underlag_${rad.id}`, locale)}</span>
                  <span className={cn(meta, "num block")}>
                    {rad.tecken ? antal(rad.tecken, locale) : a("insynTomt", locale)}
                  </span>
                  {rad.dott ? (
                    <span className="mt-1 block">
                      <Badge tone="danger">{a("insynDott", locale)}</Badge>
                    </span>
                  ) : rad.okant ? (
                    <span className={cn(meta, "mt-1 block")}>{a("insynOkant", locale)}</span>
                  ) : null}
                </th>
                {matris.kolumner.map((k) => {
                  const cell = rad.celler[k.id];
                  const saknas = rad.saknas_i.includes(k.id);
                  if (!cell && !saknas) {
                    return (
                      <td key={k.id} className="px-2 py-2 align-top text-ink-subtle">
                        <span aria-hidden>·</span>
                      </td>
                    );
                  }
                  return (
                    <td key={k.id} className={cn("px-2 py-1.5 align-top", saknas && "bg-danger/10")}>
                      <button
                        type="button"
                        onClick={() => onValj(k.id, cell?.hash ?? null)}
                        title={saknas ? a("insynSaknas", locale) : undefined}
                        className={cn(
                          "focus-ring num inline-flex min-h-8 items-center gap-1 rounded-input px-1.5 text-left hover:bg-paper2",
                          saknas ? "font-medium text-ink" : "text-ink"
                        )}
                      >
                        {cell ? (
                          <>
                            <span className="font-medium">{a(cell.position === "system" ? "posSystem" : "posUser", locale)}</span>
                            <span>{antal(cell.tecken, locale)}</span>
                          </>
                        ) : (
                          <span>{a("insynTomt", locale)}</span>
                        )}
                        {saknas ? <span className="sr-only">{a("insynSaknas", locale)}</span> : null}
                      </button>
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className={cn(meta, "mt-2")}>{a("insynForklaring", locale)}</p>
    </div>
  );
}
