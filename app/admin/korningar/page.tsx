import Link from "next/link";
import { AdminTabell, AdminText } from "@/components/admin/AdminText";
import { Cell, Tomt, chip, chipAktiv, chipInaktiv, chiplista, tabellRad, panelKort } from "@/components/ui";
import { listRuns, unwrap } from "@/lib/data/admin";
import { cn } from "@/lib/utils";
import { AdminVyhuvud } from "@/components/admin/AdminVyhuvud";
import { KorningsOversikt } from "@/components/admin/KorningsOversikt";
import { Panelrubrik } from "@/components/dashboard/OversiktPaneler";
import { KORNINGSTYPER, KORNINGSTYPNAMN } from "@/lib/admin/korningstyper";
import { ADMIN } from "@/lib/admin/sprak";

export const dynamic = "force-dynamic";

// Backenden ligger på Renders gratisnivå och tar upp till ~35 s att vakna.
// Utan detta dödar Vercel renderingen mitt i uppvakningen. Se app/admin/page.tsx.
export const maxDuration = 60;

// Agenttyperna och deras namn bor i lib/admin/korningstyper.ts: översikten
// ovanför tabellen läser samma lista.
const TYPES = KORNINGSTYPER;
const TYPNAMN = KORNINGSTYPNAMN;

/** Hämtningen. Backendens tak per anrop (admin.py, `min(limit, 200)`). */
const HAMTA = 200;
/** Tabellens rader innan "Visa alla": översikten räknar på alla hämtade. */
const VISA = 50;

export default async function Page({
  searchParams
}: Readonly<{ searchParams: Promise<Record<string, string | undefined>> }>) {
  const params = await searchParams;
  const query = new URLSearchParams();
  if (params.tenant_id) query.set("tenant_id", params.tenant_id);
  if (params.agent_type) query.set("agent_type", params.agent_type);
  query.set("limit", String(HAMTA));
  // Listan visar aldrig spåret (det öppnas per körning på /admin/korningar/[id]).
  // Med hela raderna var sidan 7,3 MB per besök.
  query.set("sammandrag", "true");

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
  const alla = params.alla === "1";
  const visade = alla ? runs : runs.slice(0, VISA);
  // "Visa alla" behåller filtret: länken bygger på samma parametrar.
  const allaHref = (pa: boolean) => {
    const q = new URLSearchParams();
    if (params.tenant_id) q.set("tenant_id", params.tenant_id);
    if (active) q.set("agent_type", active);
    if (pa) q.set("alla", "1");
    const qs = q.toString();
    return qs ? `/admin/korningar?${qs}` : "/admin/korningar";
  };

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

      <KorningsOversikt runs={runs} filter={active} />

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
        <section aria-labelledby="logg-tabell" className={cn(panelKort, "mt-4 min-w-0")}>
          <Panelrubrik id="logg-tabell" titel={ADMIN.korningarRubrik} antal={runs.length} />
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
            {visade.map((run) => (
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
          {runs.length > VISA ? (
            <Link
              href={allaHref(!alla)}
              scroll={false}
              className="focus-ring mt-3 inline-flex items-center rounded-input text-[0.8125rem] font-medium text-ink-muted underline-offset-4 hover:text-ink hover:underline"
            >
              {alla ? <AdminText n="visaFarre" /> : <AdminText n="visaAllaKorningar" />}
              {alla ? null : <span className="num ml-1 tabular-nums">({runs.length})</span>}
            </Link>
          ) : null}
        </section>
      )}
    </div>
  );
}
