import Link from "next/link";
import { listEvents, unwrap, type EventRow } from "@/lib/data/admin";

export const dynamic = "force-dynamic";

const LEVELS = ["", "error", "warning", "info"];

/**
 * Notiscentret. Grupperat på källa + meddelande, med antal och senaste
 * förekomst.
 *
 * Grupperingen är inte kosmetik: hundra rader av samma trasiga skrapkälla är
 * ETT problem, och en oplatt lista hade begravt de nittionio andra felen
 * under det. Sorteringen går på senaste förekomst, inte på antal — det som
 * händer nu är mer intressant än det som hände mest.
 */
export default async function Page({
  searchParams
}: Readonly<{ searchParams: Promise<Record<string, string | undefined>> }>) {
  const params = await searchParams;
  const level = params.level ?? "";
  const { data, error } = unwrap(await listEvents(level ? `?level=${level}` : ""));

  if (error) {
    return (
      <div>
        <h1 className="font-display text-4xl italic-disp tighten">Händelser</h1>
        <p role="alert" className="mt-6 max-w-[70ch] break-words text-[15px] text-danger">
          {error}
        </p>
      </div>
    );
  }

  const events = data ?? [];
  const grouped = new Map<string, { count: number; latest: EventRow }>();
  for (const event of events) {
    const key = `${event.source}::${event.message}`;
    const existing = grouped.get(key);
    if (existing) {
      existing.count += 1;
    } else {
      grouped.set(key, { count: 1, latest: event });
    }
  }

  const rows = [...grouped.values()].sort((a, b) =>
    b.latest.created_at.localeCompare(a.latest.created_at)
  );

  return (
    <div>
      <h1 className="font-display text-4xl italic-disp tighten">Händelser</h1>

      <div className="mt-6 flex min-w-0 flex-wrap gap-3">
        {LEVELS.map((value) => (
          <Link
            key={value || "alla"}
            href={value ? `/admin/handelser?level=${value}` : "/admin/handelser"}
            className={
              level === value
                ? "border border-ochre bg-ochre/10 px-4 py-2 font-mono text-[12px] uppercase tracking-[0.18em]"
                : "border border-ink/15 px-4 py-2 font-mono text-[12px] uppercase tracking-[0.18em] text-mineral transition hover:border-ochre hover:text-ochre"
            }
          >
            {value || "alla"}
          </Link>
        ))}
      </div>

      {rows.length === 0 ? (
        <p className="mt-8 border-t border-ink/15 pt-5 text-[15px] text-mineral">
          Inga händelser. Det är det önskade tillståndet.
        </p>
      ) : (
        <ul className="mt-8">
          {rows.map(({ count, latest }) => (
            <li key={latest.id} className="min-w-0 border-t border-ink/15 py-5">
              <div className="flex min-w-0 flex-wrap items-baseline justify-between gap-x-6 gap-y-2">
                <span className="min-w-0 break-words text-[16px]">{latest.message}</span>
                <span
                  className={
                    latest.level === "error"
                      ? "kicker shrink-0 text-warning"
                      : "kicker shrink-0 text-mineral"
                  }
                >
                  {latest.level} · {latest.source}
                  {count > 1 ? ` · ${count} ggr` : ""}
                </span>
              </div>

              <p className="mt-2 text-[14px] tabular-nums text-mineral">
                {latest.tenant_slug ?? "plattformsnivå"} ·{" "}
                {latest.created_at.slice(0, 19).replace("T", " ")}
                {latest.run_id ? (
                  <>
                    {" · "}
                    <Link
                      href={`/admin/korningar/${latest.run_id}`}
                      className="underline underline-offset-4 hover:text-ochre"
                    >
                      till körningen
                    </Link>
                  </>
                ) : null}
              </p>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
