import Link from "next/link";
import { notFound } from "next/navigation";
import { AppShell } from "@/components/AppShell";
import { getPlatformAdmin } from "@/lib/auth/admin";

export const dynamic = "force-dynamic";

/**
 * Adminytan, nu som en sektion i den vanliga dashboarden i stället för en egen
 * route. Admin behåller alla ordinarie flikar (AppShell ovanför) och får utöver
 * det de tre admin-flikarna här — med Kunder som startsida.
 *
 * Grinden är densamma som förut: `notFound()` och inte en redirect till /login,
 * eftersom ett 403 eller en redirect bekräftar att ytan finns och vem den är
 * till för. En 404 säger ingenting.
 *
 * Det här är grind ETT av tre. De andra två är `lib/data/admin.ts` egen kontroll
 * och backendens `require_master_key`. Ingen av dem litar på att de andra gjorde
 * sitt jobb.
 */
const TABS = [
  { href: "/dashboard/admin", label: "Kunder" },
  { href: "/dashboard/admin/korningar", label: "Körningar" },
  { href: "/dashboard/admin/handelser", label: "Händelser" }
];

export default async function AdminLayout({
  children
}: Readonly<{ children: React.ReactNode }>) {
  const admin = await getPlatformAdmin();
  if (!admin) {
    notFound();
  }

  return (
    <AppShell>
      <div className="border-b border-ink/15">
        <div className="mx-auto flex max-w-[1400px] min-w-0 flex-wrap items-baseline gap-x-8 gap-y-3 px-4 py-4 md:px-6">
          <span className="kicker text-mineral">Snajp · admin</span>
          <nav className="flex min-w-0 flex-wrap gap-6">
            {TABS.map((tab) => (
              <Link key={tab.href} href={tab.href} className="text-[15px] hover:text-ochre">
                {tab.label}
              </Link>
            ))}
          </nav>
          <span className="kicker ml-auto shrink-0 text-mineral">{admin.email}</span>
        </div>
      </div>

      <main className="mx-auto max-w-[1400px] px-4 py-10 md:px-6">{children}</main>
    </AppShell>
  );
}
