import Link from "next/link";
import { ButtonLink } from "@/components/ui";
import { getCurrentTenant } from "@/lib/tenants/server";

export default async function NotFound() {
  const tenant = await getCurrentTenant();

  // En 404 på kundens domän får inte visa Snajps varumärke eller länka till
  // Snajps dashboard. Besökaren vet inte vem Snajp är och ska inte behöva veta.
  if (tenant) {
    return (
      <main className="grid min-h-screen place-items-center bg-paper p-6">
        <div className="max-w-lg text-center">
          <p className="kicker text-mineral">{tenant.name}</p>
          <h1 className="mt-4 font-display text-[2.5rem] leading-tight tracking-[-0.02em]">
            Sidan finns inte
          </h1>
          <p className="mt-4 text-[17px] leading-8 text-ink2">
            Adressen kan ha ändrats. Starta ett supportärende nedan, eller hör av dig på{" "}
            <a href={`mailto:${tenant.company.email}`} className="text-ochre">
              {tenant.company.email}
            </a>
            .
          </p>
          <p className="mt-8 flex flex-wrap justify-center gap-x-6 gap-y-2">
            <Link href={`/chat/${tenant.slug}`} className="kicker text-ochre">
              Till kundtjänst
            </Link>
            <a href={tenant.website} className="kicker text-mineral hover:text-ochre">
              {tenant.name}
            </a>
          </p>
        </div>
      </main>
    );
  }

  // Typografi, inget kort. DESIGN.md ställer /not-found i gruppen "Content —
  // single column, typography only", och tenant-grenen ovan följer det redan.
  // Snajp-grenen låg i en EmptyState, vars ikon är en grön BOCK: en
  // bekräftelsesymbol på ett felmeddelande. Sett i skärmdump bredvid
  // app/error.tsx såg de två sidorna ut att komma från olika produkter.
  return (
    <main className="grid min-h-screen place-items-center bg-paper p-6">
      <div className="max-w-lg text-center">
        <h1 className="font-display text-[2.5rem] leading-tight tracking-[-0.02em]">
          Sidan finns inte
        </h1>
        <p className="mt-4 text-[17px] leading-8 text-ink2">
          Adressen kan ha ändrats eller skrivits fel. Länkarna i menyn leder alltid rätt.
        </p>
        <div className="mt-8 flex justify-center">
          <ButtonLink href="/dashboard">Till dashboard</ButtonLink>
        </div>
      </div>
    </main>
  );
}
