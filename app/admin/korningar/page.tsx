import Link from "next/link";
import { Cell, Sidhuvud, Tabell, Tomt, flik, flikAktiv, flikInaktiv, tabellRad } from "@/components/ui";
import { listRuns, unwrap } from "@/lib/data/admin";
import { cn } from "@/lib/utils";

export const dynamic = "force-dynamic";

// Backenden ligger på Renders gratisnivå och tar upp till ~35 s att vakna.
// Utan detta dödar Vercel renderingen mitt i uppvakningen. Se app/admin/page.tsx.
export const maxDuration = 60;

// "bookkeeping" saknades ända tills agenten fick en adminvy. Filtret är en
// uppräkning, alltså en lista som glider: en ny agenttyp syns i tabellen men
// går inte att filtrera på förrän någon lägger till den här.
//
// Namnen är produktens (railens Iris, Kundtjänst, Kvitton), inte agent_type-
// koderna: en kod som etikett är en intern detalj på fel ställe. En okänd typ
// visas i tabellen som koden själv, i mono, så att ingen ny typ döljs bakom ett
// påhittat namn.
const TYPES: [string, string][] = [
  ["", "Alla"],
  ["support", "Kundtjänst"],
  ["leads_research", "Iris, research"],
  ["leads_outreach", "Iris, utskick"],
  ["bookkeeping", "Kvitton"],
  ["demo", "Demo"]
];
const TYPNAMN = new Map(TYPES);

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
        <Sidhuvud title="Körningar" />
        <p role="alert" className="mt-8 max-w-[70ch] break-words text-[15px] text-danger">
          {error}
        </p>
      </div>
    );
  }

  const runs = data ?? [];
  const active = params.agent_type ?? "";

  return (
    <div>
      <Sidhuvud title="Körningar" />

      <div className="mt-8 flex min-w-0 flex-wrap gap-2">
        {TYPES.map(([type, namn]) => (
          <Link
            key={type || "alla"}
            href={type ? `/admin/korningar?agent_type=${type}` : "/admin/korningar"}
            aria-current={active === type ? "page" : undefined}
            className={cn(flik, active === type ? flikAktiv : flikInaktiv)}
          >
            {namn}
          </Link>
        ))}
      </div>

      {/* En tom lista för leads var en gång migration 025 som saknades: check-
          villkoret avvisade varje leads-körning och ingen sparades. Det syns
          som en tom lista, inte som ett fel. */}
      {runs.length === 0 ? (
        <div className="mt-6">
          <Tomt>Inga körningar matchar.</Tomt>
        </div>
      ) : (
        <div className="mt-6">
          <Tabell
            minBredd={880}
            ariaLabel="Körningar"
            kolumner={[
              { rubrik: "Tid", bredd: "17%" },
              { rubrik: "Kund", bredd: "20%" },
              { rubrik: "Typ", bredd: "17%" },
              { rubrik: "Pack", bredd: "14%" },
              { rubrik: "Tokens", bredd: "11%", hoger: true },
              { rubrik: "Latens", bredd: "11%", hoger: true },
              { rubrik: "Spår", bredd: "10%", hoger: true, srOnly: true }
            ]}
          >
            {runs.map((run) => (
              <tr key={run.id} className={tabellRad}>
                <Cell className="num">{run.created_at.slice(0, 16).replace("T", " ")}</Cell>
                <Cell className="break-words">{run.tenant_name || run.tenant_slug || "–"}</Cell>
                <Cell className="break-words">
                  {TYPNAMN.get(run.agent_type) ?? (
                    <span className="font-mono text-[0.8125rem]">{run.agent_type}</span>
                  )}
                </Cell>
                {/* En rad: hela hashen bröt varje körning över tre rader. Värdet
                    står kvar i title för den som behöver det. */}
                <Cell className="truncate font-mono text-[0.8125rem] text-ink-subtle">
                  <span title={run.pack_version}>{run.pack_version}</span>
                </Cell>
                <Cell hoger>
                  {((run.tokens_in ?? 0) + (run.tokens_out ?? 0)).toLocaleString("sv-SE")}
                </Cell>
                <Cell hoger>{run.latency_ms ?? 0} ms</Cell>
                <Cell hoger>
                  <Link
                    href={`/admin/korningar/${run.id}`}
                    className="focus-ring underline underline-offset-4 hover:text-ochre"
                  >
                    Spår
                  </Link>
                </Cell>
              </tr>
            ))}
          </Tabell>
        </div>
      )}
    </div>
  );
}
