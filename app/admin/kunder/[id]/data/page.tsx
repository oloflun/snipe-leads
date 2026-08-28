import type { Metadata } from "next";
import Link from "next/link";

import { Kunddata } from "@/components/admin/Kunddata";
import { hamtaKunddata } from "@/lib/actions/kunddata";
import { listTenants, unwrap } from "@/lib/data/admin";

export const dynamic = "force-dynamic";
export const maxDuration = 60;

export const metadata: Metadata = { title: "Snajp - Kunder&Data" };

/**
 * En enskild kunds registeruppgifter — fliken Kunder & Data:s detaljvy.
 *
 * Egen sida bredvid agentprofilen (`/admin/kunder/[id]`), inte en sektion i
 * den: profilen ändrar hur agenten BETER sig, det här är fakturering och
 * kontaktvägar. Två skrivytor med olika blastradie i samma formulär är hur
 * fel uppgift hamnar i fel ruta. Korslänkarna binder ihop dem i stället.
 */
export default async function Page({
  params
}: Readonly<{ params: Promise<{ id: string }> }>) {
  const { id } = await params;
  // Kundlistan hämtas parallellt för bläddringen föregående/nästa — samma
  // sortering som listsidan (namn, sv), så ordningen man bläddrar i är
  // ordningen man kom ifrån.
  const [kunddataSvar, tenantsSvar] = await Promise.all([hamtaKunddata(id), listTenants()]);
  const { kunddata, error } = kunddataSvar;
  const alla = [...(unwrap(tenantsSvar).data ?? [])].sort((a, b) =>
    a.name.localeCompare(b.name, "sv")
  );
  const position = alla.findIndex((t) => String(t.id) === id);
  const forra = position > 0 ? alla[position - 1] : null;
  const nasta = position >= 0 && position < alla.length - 1 ? alla[position + 1] : null;

  if (error || !kunddata) {
    return (
      <div>
        <h1 className="font-display text-4xl tracking-[-0.03em]">Kunddata</h1>
        <p role="alert" className="mt-6 max-w-[70ch] break-words text-[0.9375rem] text-danger">
          {error ?? "Kunden gick inte att hämta."}
        </p>
        <Link
          href="/admin/kunder"
          className="mt-6 inline-block text-[0.9375rem] underline underline-offset-4"
        >
          Tillbaka till kundlistan
        </Link>
      </div>
    );
  }

  return (
    <div>
      <div className="flex flex-wrap items-center justify-between gap-x-6 gap-y-2">
        <Link
          href="/admin/kunder"
          className="text-[0.8125rem] text-mineral underline underline-offset-4 hover:text-ochre"
        >
          Kunder
        </Link>

        {/* Bläddringen: samma ordning som kundlistan. Namnen står utskrivna —
            en pil utan namn säger inte vart den leder. */}
        {position >= 0 && alla.length > 1 ? (
          <nav
            aria-label="Bläddra mellan kunder"
            className="flex items-center gap-4 text-[0.8125rem]"
          >
            {forra ? (
              <Link
                href={`/admin/kunder/${forra.id}/data`}
                className="focus-ring inline-flex min-h-9 max-w-[16rem] items-center gap-1 truncate rounded-input text-mineral hover:text-ochre"
              >
                <span aria-hidden>←</span> {forra.name}
              </Link>
            ) : null}
            <span className="tabular-nums text-ink/45">
              {position + 1} av {alla.length}
            </span>
            {nasta ? (
              <Link
                href={`/admin/kunder/${nasta.id}/data`}
                className="focus-ring inline-flex min-h-9 max-w-[16rem] items-center gap-1 truncate rounded-input text-mineral hover:text-ochre"
              >
                {nasta.name} <span aria-hidden>→</span>
              </Link>
            ) : null}
          </nav>
        ) : null}
      </div>
      <h1 className="mt-2 font-display text-2xl tracking-[-0.02em]">{kunddata.tenant.name}</h1>
      <p className="mt-2 max-w-[70ch] text-[0.875rem] leading-6 text-mineral">
        Kontaktpersoner, fakturerings- och avtalsuppgifter. Agentens beteende styrs i{" "}
        <Link
          href={`/admin/kunder/${kunddata.tenant.id}`}
          className="focus-ring text-ochre underline underline-offset-4"
        >
          agentprofilen
        </Link>
        .
      </p>

      <div className="mt-7">
        <Kunddata data={kunddata} />
      </div>
    </div>
  );
}
