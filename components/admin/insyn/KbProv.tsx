"use client";

import { useState } from "react";

import { btnLiten, btnSecondary, etikett, faltTatt, meta } from "@/components/ui";
import { provaKb, type KbProv as KbProvSvar } from "@/lib/actions/insyn";
import { a, antal } from "@/lib/admin/sprak";
import { useLocale } from "@/lib/i18n";
import { cn } from "@/lib/utils";

/**
 * Prova en fråga (Fas 7): vilka kunskapsartiklar supportagenten hade hämtat
 * för en fråga. Samma sökning som agenten kör (support_agent._sok_kb och den
 * förenklade andra frågan), utan modellanrop. Triagestegets svenska
 * omformulering är ett modellanrop och ingår därför inte, vilket står under
 * svaret.
 */
export function KbProv({ tenantId }: Readonly<{ tenantId: string }>) {
  const { locale } = useLocale();
  const [fraga, setFraga] = useState("");
  const [svar, setSvar] = useState<KbProvSvar | null>(null);
  const [fel, setFel] = useState<string | null>(null);
  const [laddar, setLaddar] = useState(false);

  async function prova(e: React.FormEvent) {
    e.preventDefault();
    if (!fraga.trim()) return;
    setLaddar(true);
    setFel(null);
    const ut = await provaKb(tenantId, fraga.trim());
    setLaddar(false);
    if (ut.prov) setSvar(ut.prov);
    else setFel(ut.error ?? a("insynFel", locale));
  }

  return (
    <div>
      <form onSubmit={prova} className="flex flex-wrap items-end gap-2">
        <label className="flex min-w-0 flex-1 flex-col gap-1">
          <span className={etikett}>{a("insynKbFraga", locale)}</span>
          <input
            value={fraga}
            onChange={(e) => setFraga(e.target.value)}
            className={cn(faltTatt, "w-full min-w-[12rem]")}
            maxLength={2000}
          />
        </label>
        <button type="submit" disabled={laddar || !fraga.trim()} className={cn(btnSecondary, btnLiten)}>
          {laddar ? a("insynLaddar", locale) : a("insynKbKnapp", locale)}
        </button>
      </form>
      {fel ? (
        <p role="alert" className="mt-3 text-[0.875rem] text-danger">
          {fel}
        </p>
      ) : null}
      {svar ? (
        <div className="mt-4" aria-live="polite">
          <p className={meta}>
            {a("insynKbForsok", locale)}: {svar.forsok.join(" · ")}
          </p>
          {svar.artiklar.length ? (
            <ol className="mt-2 divide-y divide-ink/12 border-y border-ink/15">
              {svar.artiklar.map((art, i) => (
                <li key={art.id || i} className="py-2.5">
                  <div className="flex flex-wrap items-baseline justify-between gap-2">
                    <span className="text-[0.9375rem] font-medium text-ink">
                      {i + 1}. {art.title ?? art.id}
                    </span>
                    <span className={cn(meta, "num")}>{antal(art.tecken, locale)}</span>
                  </div>
                  <p className="mt-1 max-w-[70ch] break-words text-[0.875rem] leading-6 text-ink-muted">{art.utdrag}</p>
                </li>
              ))}
            </ol>
          ) : (
            <p className="mt-2 text-[0.9375rem] text-ink-muted">{a("insynKbIngen", locale)}</p>
          )}
          {svar.utan_omformulering ? <p className={cn(meta, "mt-2")}>{a("insynKbUtan", locale)}</p> : null}
        </div>
      ) : null}
    </div>
  );
}
