import type { Metadata } from "next";
import Link from "next/link";

import { Kunddata } from "@/components/admin/Kunddata";
import { hamtaKunddata } from "@/lib/actions/kunddata";

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
  const { kunddata, error } = await hamtaKunddata(id);

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
      <Link
        href="/admin/kunder"
        className="text-[0.8125rem] text-mineral underline underline-offset-4 hover:text-ochre"
      >
        Kunder
      </Link>
      <h1 className="mt-2 font-display text-4xl tracking-[-0.03em]">{kunddata.tenant.name}</h1>
      <p className="mt-3 max-w-[70ch] text-[0.9375rem] leading-7 text-mineral">
        Kontaktpersoner, fakturerings- och avtalsuppgifter. Agentens beteende styrs i{" "}
        <Link
          href={`/admin/kunder/${kunddata.tenant.id}`}
          className="focus-ring text-ochre underline underline-offset-4"
        >
          agentprofilen
        </Link>
        .
      </p>

      <div className="mt-10">
        <Kunddata data={kunddata} />
      </div>
    </div>
  );
}
