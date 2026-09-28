import type { Metadata } from "next";
import Link from "next/link";

import { Kunddata } from "@/components/admin/Kunddata";
import { Sidhuvud, btnSecondary, meta } from "@/components/ui";
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
 *
 * Sedan 2026-09-27 är länken till agentprofilen en åtgärd i sidhuvudet. Den
 * bodde förut i en ingress som beskrev sidan (F-016), och "Kunder" ovanför
 * rubriken upprepade railens aktiva post.
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
        <Sidhuvud title="Kunddata" />
        <p role="alert" className="mt-8 max-w-[70ch] break-words text-[0.9375rem] text-danger">
          {error ?? "Kunden gick inte att hämta."}
        </p>
      </div>
    );
  }

  return (
    <div>
      <Sidhuvud
        title={kunddata.tenant.name}
        action={
          <Link href={`/admin/kunder/${kunddata.tenant.id}`} className={btnSecondary}>
            Agentprofil
          </Link>
        }
      />

      {/* Bläddringen: samma ordning som kundlistan. Namnen står utskrivna —
          en pil utan namn säger inte vart den leder. Egen rad och inte i
          sidhuvudets åtgärder: två kundnamn bredvid rubriken bröt inte rad på
          smala skärmar. */}
      {position >= 0 && alla.length > 1 ? (
        <nav aria-label="Bläddra mellan kunder" className="mt-8 flex flex-wrap items-center gap-2">
          {forra ? (
            <Link href={`/admin/kunder/${forra.id}/data`} className={`${btnSecondary} max-w-[16rem]`}>
              {/* Ord i stället för pilglyfer (gate 97): riktningen står i texten. */}
              <span className="min-w-0 truncate">Förra: {forra.name}</span>
            </Link>
          ) : null}
          <span className={`${meta} num whitespace-nowrap px-2`}>
            {position + 1} av {alla.length}
          </span>
          {nasta ? (
            <Link href={`/admin/kunder/${nasta.id}/data`} className={`${btnSecondary} max-w-[16rem]`}>
              <span className="min-w-0 truncate">Nästa: {nasta.name}</span>
            </Link>
          ) : null}
        </nav>
      ) : null}

      <div className="mt-8">
        <Kunddata data={kunddata} />
      </div>
    </div>
  );
}
