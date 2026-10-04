import Link from "next/link";
import { AdminTabell, AdminText } from "@/components/admin/AdminText";
import { Cell, Tomt, chip, chipAktiv, chipInaktiv, chiplista, tabellRad } from "@/components/ui";
import { listRuns, unwrap } from "@/lib/data/admin";
import { cn } from "@/lib/utils";
import { AdminVyhuvud } from "@/components/admin/AdminVyhuvud";

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
// påhittat namn. Andra kolumnen är en nyckel i ADMIN (lib/admin/sprak.ts).
const TYPES: [string, string][] = [
  ["", "filterAlla"],
  ["support", "railKundtjanst"],
  ["leads_research", "typIrisResearch"],
  ["leads_outreach", "typIrisUtskick"],
  // Samma typer som Kostnad per agent räknar (agentanvandning/page.tsx).
  ["leads_svar", "typIrisSvar"],
  ["leads_followup", "typIrisUppfoljning"],
  ["bookkeeping", "railKvitton"],
  ["demo", "typDemo"]
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
        <AdminVyhuvud grupp="logg" />
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
      <AdminVyhuvud grupp="logg" />

      <div className={cn("mt-5 min-w-0", chiplista)}>
        {TYPES.map(([type, namn]) => (
          <Link
            key={type || "alla"}
            href={type ? `/admin/korningar?agent_type=${type}` : "/admin/korningar"}
            aria-current={active === type ? "page" : undefined}
            className={cn(chip, active === type ? chipAktiv : chipInaktiv)}
          >
            <AdminText n={namn} />
          </Link>
        ))}
      </div>

      {/* En tom lista för leads var en gång migration 025 som saknades: check-
          villkoret avvisade varje leads-körning och ingen sparades. Det syns
          som en tom lista, inte som ett fel. */}
      {runs.length === 0 ? (
        <div className="mt-6">
          <Tomt>
            <AdminText n="ingaKorningarMatchar" />
          </Tomt>
        </div>
      ) : (
        <div className="mt-6">
          <AdminTabell
            minBredd={880}
            aria="korningarRubrik"
            kolumner={[
              { rubrik: <AdminText n="kolTid" />, bredd: "17%" },
              { rubrik: <AdminText n="kolKund" />, bredd: "20%" },
              { rubrik: <AdminText n="kolTyp" />, bredd: "17%" },
              { rubrik: <AdminText n="kolPack" />, bredd: "14%" },
              { rubrik: <AdminText n="kolTokens" />, bredd: "11%", hoger: true },
              { rubrik: <AdminText n="kolLatens" />, bredd: "11%", hoger: true },
              { rubrik: <AdminText n="kolSpar" />, bredd: "10%", hoger: true, srOnly: true }
            ]}
          >
            {runs.map((run) => (
              <tr key={run.id} className={tabellRad}>
                <Cell className="num">{run.created_at.slice(0, 16).replace("T", " ")}</Cell>
                <Cell className="break-words">{run.tenant_name || run.tenant_slug || "–"}</Cell>
                <Cell className="break-words">
                  {TYPNAMN.has(run.agent_type) ? (
                    <AdminText n={TYPNAMN.get(run.agent_type) as string} />
                  ) : (
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
                    <AdminText n="kolSpar" />
                  </Link>
                </Cell>
              </tr>
            ))}
          </AdminTabell>
        </div>
      )}
    </div>
  );
}
