"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { OppnaArbetsyta } from "@/components/admin/OppnaArbetsyta";
import { Sidhuvud, flik, flikAktiv, flikInaktiv, fliklista, radLank } from "@/components/ui";
import { useLocale } from "@/lib/i18n";
import { cn } from "@/lib/utils";

/**
 * Kundposten (Snajp Suite fas 3, 2026-10-03): EN kund, en rubrik, vyerna i en
 * flikrad. Agentprofilen och uppgiftssidan var två sidor med var sitt sidhuvud
 * ("Kunder"-länk och agentflikar på den ena, en knapp "Agentprofil" på den
 * andra), och vägen mellan dem stod på olika ställen.
 */
export function KundHuvud({
  id,
  namn,
  slug
}: Readonly<{ id: string; namn: string; slug?: string | null }>) {
  const pathname = usePathname();
  const { text } = useLocale();
  const vyer = [
    { href: `/admin/kunder/${id}`, etikett: text({ sv: "Agentprofil och tillägg", en: "Agent profile and add-ons" }) },
    { href: `/admin/kunder/${id}/data`, etikett: text({ sv: "Uppgifter och kontakter", en: "Details and contacts" }) }
  ];
  return (
    <>
      <Link href="/admin/kunder" className={cn(radLank, "-ml-1 mb-1")}>
        {text({ sv: "Kunder", en: "Customers" })}
      </Link>
      <Sidhuvud title={namn} action={slug ? <OppnaArbetsyta slug={slug} namn={namn} /> : undefined} />
      <nav aria-label={namn} className={cn("mt-4", fliklista)}>
        {vyer.map((vy) => {
          const aktiv = pathname === vy.href;
          return (
            <Link
              key={vy.href}
              href={vy.href}
              aria-current={aktiv ? "page" : undefined}
              className={cn(flik, aktiv ? flikAktiv : flikInaktiv)}
            >
              {vy.etikett}
            </Link>
          );
        })}
      </nav>
    </>
  );
}
