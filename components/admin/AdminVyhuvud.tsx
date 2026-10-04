"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Sidhuvud, flik, flikAktiv, flikInaktiv, fliklista } from "@/components/ui";
import { useLocale, type Localized } from "@/lib/i18n";
import { cn } from "@/lib/utils";

/**
 * Adminens objekt och deras vyer (Snajp Suite fas 3, 2026-10-03).
 *
 * Twenty-mönstret utan nya rutter: Kunder och Logg är EN menypost var, och
 * sidorna som tidigare var egna poster (Paket, Körningar, Testkörningar,
 * Agentanvändning, Händelser) är vyer i en flikrad under objektets namn.
 * Adresserna står kvar, så bokmärken och länkar i loggar fungerar.
 */
export const ADMIN_GRUPPER = {
  kunder: {
    rubrik: { sv: "Kunder", en: "Customers" },
    vyer: [
      { href: "/admin/kunder", etikett: { sv: "Alla kunder", en: "All customers" } },
      { href: "/admin/paket", etikett: { sv: "Paket och avtal", en: "Plans and contracts" } }
    ]
  },
  logg: {
    rubrik: { sv: "Logg", en: "Log" },
    vyer: [
      { href: "/admin/korningar", etikett: { sv: "Körningar", en: "Runs" } },
      { href: "/admin/handelser", etikett: { sv: "Händelser", en: "Events" } },
      { href: "/admin/testkorningar", etikett: { sv: "Testkörningar", en: "Test runs" } },
      { href: "/admin/agentanvandning", etikett: { sv: "Kostnad per agent", en: "Cost per agent" } }
    ]
  }
} satisfies Record<string, { rubrik: Localized; vyer: { href: string; etikett: Localized }[] }>;

export type AdminGrupp = keyof typeof ADMIN_GRUPPER;

export function AdminVyhuvud({ grupp, action }: Readonly<{ grupp: AdminGrupp; action?: React.ReactNode }>) {
  const pathname = usePathname();
  const { text } = useLocale();
  const { rubrik, vyer } = ADMIN_GRUPPER[grupp];
  return (
    <>
      <Sidhuvud title={text(rubrik)} action={action} />
      <nav aria-label={text(rubrik)} className={cn("mt-4", fliklista)}>
        {vyer.map((vy) => {
          const aktiv = pathname === vy.href || pathname.startsWith(`${vy.href}/`);
          return (
            <Link
              key={vy.href}
              href={vy.href}
              aria-current={aktiv ? "page" : undefined}
              className={cn(flik, aktiv ? flikAktiv : flikInaktiv)}
            >
              {text(vy.etikett)}
            </Link>
          );
        })}
      </nav>
    </>
  );
}
