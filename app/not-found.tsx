import Link from "next/link";
import { ButtonLink, EmptyState } from "@/components/ui";
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

  return (
    <main className="grid min-h-screen place-items-center bg-paper p-6">
      <div className="max-w-lg">
        <EmptyState title="Sidan finns inte" body="Route-strukturen är skapad, men den här adressen matchar ingen vy i Snajp." />
        <div className="mt-5 flex justify-center">
          <ButtonLink href="/dashboard">Till dashboard</ButtonLink>
        </div>
      </div>
    </main>
  );
}
