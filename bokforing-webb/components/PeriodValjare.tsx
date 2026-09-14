"use client";

import { usePeriod } from "@/lib/period";

/**
 * Datumintervallet som styr hela sajten — bor i sidhuvudens åtgärdsyta.
 * type="date" och inte en egen väljare: webbläsarens är tillgänglig,
 * lokaliserad och kostar noll kilobyte.
 */
export function PeriodValjare() {
  const { period, sattPeriod } = usePeriod();
  return (
    <div className="flex flex-wrap items-end gap-2">
      <label className="flex flex-col gap-1">
        <span className="text-[0.75rem] font-medium text-ink/55">Från</span>
        <input
          type="date"
          value={period.fran}
          onChange={(e) => sattPeriod({ ...period, fran: e.target.value })}
          className="focus-ring h-9 rounded-input bg-paper2 px-2.5 text-[0.875rem]"
        />
      </label>
      <label className="flex flex-col gap-1">
        <span className="text-[0.75rem] font-medium text-ink/55">Till</span>
        <input
          type="date"
          value={period.till}
          onChange={(e) => sattPeriod({ ...period, till: e.target.value })}
          className="focus-ring h-9 rounded-input bg-paper2 px-2.5 text-[0.875rem]"
        />
      </label>
    </div>
  );
}
