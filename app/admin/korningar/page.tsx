import Link from "next/link";
import { listRuns, unwrap } from "@/lib/data/admin";

export const dynamic = "force-dynamic";

// Backenden ligger på Renders gratisnivå och tar upp till ~35 s att vakna.
// Utan detta dödar Vercel renderingen mitt i uppvakningen. Se app/admin/page.tsx.
export const maxDuration = 60;

const TYPES = ["", "support", "leads_research", "leads_outreach", "demo"];

export default async function Page({
  searchParams
}: Readonly<{ searchParams: Promise<Record<string, string | undefined>> }>) {
  const params = await searchParams;
  const query = new URLSearchParams();
  if (params.tenant_id) query.set("tenant_id", params.tenant_id);
  if (params.agent_type) query.set("agent_type", params.agent_type);

  const queryString = query.toString();
  const { data, error } = unwrap(await listRuns(queryString ? `?${queryString}` : ""));

  if (error) {
    return (
      <div>
        <h1 className="font-display text-4xl italic-disp tighten">Körningar</h1>
        <p role="alert" className="mt-6 max-w-[70ch] break-words text-[15px] text-danger">
          {error}
        </p>
      </div>
    );
  }

  const runs = data ?? [];
  const active = params.agent_type ?? "";

  return (
    <div>
      <h1 className="font-display text-4xl italic-disp tighten">Körningar</h1>

      <div className="mt-6 flex min-w-0 flex-wrap gap-3">
        {TYPES.map((type) => (
          <Link
            key={type || "alla"}
            href={type ? `/admin/korningar?agent_type=${type}` : "/admin/korningar"}
            className={
              active === type
                ? "border border-ochre bg-ochre/10 px-4 py-2 font-mono text-[12px] uppercase tracking-[0.18em]"
                : "border border-ink/15 px-4 py-2 font-mono text-[12px] uppercase tracking-[0.18em] text-mineral transition hover:border-ochre hover:text-ochre"
            }
          >
            {type || "alla"}
          </Link>
        ))}
      </div>

      {runs.length === 0 ? (
        <p className="mt-8 max-w-[70ch] border-t border-ink/15 pt-5 text-[15px] leading-7 text-mineral">
          Inga körningar matchar. Är listan tom för leads: kontrollera att migration 025 är
          körd. Före den avvisade check-villkoret varje leads-körning, och ingen sparades
          någonsin — det syns som en tom lista, inte som ett fel.
        </p>
      ) : (
        <div className="mt-8 overflow-x-auto">
          <table className="w-full min-w-[880px] border-collapse text-[15px]">
            <thead>
              <tr className="border-b border-ink/15">
                {["Tid", "Kund", "Typ", "Pack", "Tokens", "Latens", ""].map((head, index) => (
                  <th
                    key={head || "spar"}
                    scope="col"
                    className={`kicker py-3 text-mineral ${index < 4 ? "text-left" : "text-right"}`}
                  >
                    {head}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {runs.map((run) => (
                <tr key={run.id} className="border-b border-ink/15">
                  <td className="py-4 tabular-nums">
                    {run.created_at.slice(0, 16).replace("T", " ")}
                  </td>
                  <td className="py-4">{run.tenant_slug ?? "—"}</td>
                  <td className="py-4">{run.agent_type}</td>
                  <td className="py-4 text-mineral">{run.pack_version}</td>
                  <td className="py-4 text-right tabular-nums">
                    {(run.tokens_in ?? 0) + (run.tokens_out ?? 0)}
                  </td>
                  <td className="py-4 text-right tabular-nums">{run.latency_ms ?? 0} ms</td>
                  <td className="py-4 text-right">
                    <Link
                      href={`/admin/korningar/${run.id}`}
                      className="underline underline-offset-4 hover:text-ochre"
                    >
                      Spår
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
