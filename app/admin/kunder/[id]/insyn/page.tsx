import type { Metadata } from "next";
import Link from "next/link";

import { AdminText } from "@/components/admin/AdminText";
import { Insynsvy, type KorningVal } from "@/components/admin/insyn/Insynsvy";
import { KundHuvud } from "@/components/admin/KundHuvud";
import { Sidhuvud, chip, chipAktiv, chipInaktiv, chiplista, meta } from "@/components/ui";
import { getInsyn, listRuns, listTenants, unwrap } from "@/lib/data/admin";

export const dynamic = "force-dynamic";
export const maxDuration = 60;

export const metadata: Metadata = { title: "Snajp - Insyn" };

/**
 * Admin › Kund › Underlag och flöde (plan 2026-10-06, Fas 7): allt agenten
 * läser, visat som flöde. Hämtar insynen och kundens senaste körningar på
 * servern; kartan, stapeln, matrisen och körningsväljaren är en klientdel.
 *
 * Körningarna skickas till klienten utan sina spår: listan bär id, typ, tid
 * och en etikett att filtrera på. Spåret för en vald körning hämtas när den
 * väljs (lib/actions/insyn.ts), annars hade sidan dragit med sig hela
 * användarmeddelanden för fyrtio körningar.
 */
const TYPER = {
  leads: ["leads_research", "leads_outreach", "leads_svar", "leads_followup"],
  support: ["support"]
} as const;

function etikettFor(run: { input?: string | null; output?: string | null; agent_type: string }): string {
  // Researchens utdata är JSON med bolagets sammanfattning; utkastets är ämne
  // och brödtext; supportens indata är kundens meddelande.
  let text = run.agent_type === "support" ? run.input ?? "" : run.output ?? run.input ?? "";
  try {
    const tolkat = JSON.parse(text) as { company_summary?: string };
    if (tolkat?.company_summary) text = tolkat.company_summary;
  } catch {
    /* inte JSON */
  }
  return text.replace(/\s+/g, " ").trim().slice(0, 140);
}

export default async function Page({
  params,
  searchParams
}: Readonly<{ params: Promise<{ id: string }>; searchParams: Promise<{ agent?: string }> }>) {
  const { id } = await params;
  const { agent: valdAgent } = await searchParams;
  const agent = valdAgent === "support" ? "support" : "leads";

  const [insynSvar, korningarSvar, tenantsSvar] = await Promise.all([
    getInsyn(id, agent),
    listRuns(`?tenant_id=${encodeURIComponent(id)}&limit=80`),
    listTenants()
  ]);
  const { data: insyn, error } = unwrap(insynSvar);
  const tenant = (unwrap(tenantsSvar).data ?? []).find((t) => String(t.id) === id);
  const typer: readonly string[] = TYPER[agent];
  const korningar: KorningVal[] = (unwrap(korningarSvar).data ?? [])
    .filter((r) => typer.includes(r.agent_type))
    .slice(0, 40)
    .map((r) => ({
      id: r.id,
      agent_type: r.agent_type,
      created_at: r.created_at,
      prospect_id: r.prospect_id ?? null,
      etikett: etikettFor(r)
    }));

  return (
    <div>
      {tenant ? (
        <KundHuvud id={id} namn={tenant.name} slug={tenant.slug} />
      ) : (
        <Sidhuvud title={<AdminText n="insynRubrik" />} />
      )}

      <div className="mt-5 flex flex-wrap items-center justify-between gap-3">
        <div className={chiplista}>
          {(["leads", "support"] as const).map((typ) => (
            <Link
              key={typ}
              href={`/admin/kunder/${id}/insyn?agent=${typ}`}
              aria-current={agent === typ ? "page" : undefined}
              className={`${chip} ${agent === typ ? chipAktiv : chipInaktiv}`}
            >
              <AdminText n={typ === "support" ? "insynKundtjanst" : "insynIris"} />
            </Link>
          ))}
        </div>
        {insyn ? (
          <p className={meta}>
            <AdminText n="insynKedja" />: <span className="font-mono">{insyn.kedja}</span>
          </p>
        ) : null}
      </div>

      {error || !insyn ? (
        <p role="alert" className="mt-8 max-w-[70ch] break-words text-[0.9375rem] text-danger">
          {error ?? <AdminText n="insynFel" />}
        </p>
      ) : (
        <div className="mt-8">
          <Insynsvy tenantId={id} insyn={insyn} korningar={korningar} />
        </div>
      )}
    </div>
  );
}
