"use client";

import type { ReactNode } from "react";

import { Nyckeltal, Radlista, Tabell, type TabellKolumn } from "@/components/ui";
import { a } from "@/lib/admin/sprak";
import { useLocale } from "@/lib/i18n";

/**
 * Adminytans texter i server-komponenter.
 *
 * Adminsidorna hämtar på servern och ska fortsätta göra det, men språkvalet är
 * klientstate i AdminShell. Samma skäl som Kundrubrik: en liten klientdel
 * slår upp texten, sidan förblir en server-komponent. Omslagen nedan finns för
 * de ställen där texten är en sträng-prop (aria-label, nyckeltalsetikett) och
 * inte kan vara en nod.
 */
export function AdminText({ n }: Readonly<{ n: string }>) {
  const { locale } = useLocale();
  return <>{a(n, locale)}</>;
}

export function AdminTabell({
  aria,
  kolumner,
  minBredd,
  children
}: Readonly<{ aria: string; kolumner: TabellKolumn[]; minBredd?: number; children: ReactNode }>) {
  const { locale } = useLocale();
  return (
    <Tabell ariaLabel={a(aria, locale)} kolumner={kolumner} minBredd={minBredd}>
      {children}
    </Tabell>
  );
}

export function AdminRadlista({
  aria,
  className,
  children
}: Readonly<{ aria: string; className?: string; children: ReactNode }>) {
  const { locale } = useLocale();
  return (
    <Radlista ariaLabel={a(aria, locale)} className={className}>
      {children}
    </Radlista>
  );
}

export function AdminNav({
  aria,
  className,
  children
}: Readonly<{ aria: string; className?: string; children: ReactNode }>) {
  const { locale } = useLocale();
  return (
    <nav aria-label={a(aria, locale)} className={className}>
      {children}
    </nav>
  );
}

export function AdminNyckeltal({
  poster
}: Readonly<{ poster: { n: string; varde: ReactNode; notis?: string }[] }>) {
  const { locale } = useLocale();
  return (
    <Nyckeltal
      poster={poster.map((post) => ({
        etikett: a(post.n, locale),
        varde: post.varde,
        notis: post.notis ? a(post.notis, locale) : undefined
      }))}
    />
  );
}
