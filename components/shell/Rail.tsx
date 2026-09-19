"use client";

import type { LucideIcon } from "lucide-react";
import Link from "next/link";
import { Fragment } from "react";
import { Logo } from "@/components/Logo";
import { cn } from "@/lib/utils";

/**
 * Den delade vänsterrailen. Extraherad ur `AppShell` 2026-09-18 så att
 * adminytan kan bära SAMMA rail i stället för en egen topp-header med
 * flikrad — se `components/admin/AdminShell.tsx` för varför den ytan höll
 * en separat chrome så länge.
 *
 * `AppShell` fortsätter äga sin egen sammansättning (kontrollrad, demo-
 * banners) och skickar in exakt samma markup som förut i `brand` och
 * `footer` — därför är kund- och demoytans renderade DOM oförändrad av den
 * här extraktionen. Adminytan komponerar sin egen `brand`/`footer` och får
 * ett andra navgrupp under en hårlinje, se `groups`.
 */

/**
 * Ett barn i en undernavigering (t.ex. Iris framtida Bolag/Granskning/
 * Inställningar). Inget eget ikon-fält: barn ritas med en punktmarkör i
 * stället för `RailNavItem`s ikon, se `RailRad`s `Ikon?`.
 */
export type RailNavChild = {
  href: string;
  label: string;
  active: boolean;
};

export type RailNavItem = {
  href: string;
  label: string;
  Icon: LucideIcon;
  active: boolean;
  onClick?: () => void;
  /**
   * Undersidor till posten, t.ex. Iris tre flikar. Renderas som en indragen
   * lista under posten NÄR `active` är sant — anroparen avgör det, med samma
   * pathname-prefix-logik som toppnivåns `active` redan använder (exakt match
   * eller `pathname.startsWith(`${href}/`)`), så Rail behöver aldrig känna
   * till pathname själv.
   *
   * Utelämnad eller tom: posten renderas EXAKT som innan barn-stödet fanns —
   * ingen extra wrapper, ingen förändrad markup. Se `Rail` nedan.
   */
  children?: RailNavChild[];
};

export type RailNavGroup = {
  key?: string;
  /** Hårlinje + liten etikett ovanför gruppen. Utelämnas för den första gruppen. */
  label?: string;
  items: RailNavItem[];
};

/**
 * En rad i railen. Ochre-markör på aktiv flik — DESIGN.md:s "current
 * selection" — och etikett bara från lg; under det bär `title` namnet.
 *
 * `Ikon` är valfri och `compact` finns för barnposter i en undernavigering:
 * utan ikon ritas en liten punkt i dess ställe, och `compact` sänker höjd och
 * textstorlek ett steg. Standardanropet (ikon, inte compact) ger EXAKT samma
 * className-sträng som innan de två fälten fanns — `cn()` filtrerar bort
 * `false`, så `compact && "…"` bidrar ingenting när `compact` är `false`.
 */
export function RailRad({
  href,
  etikett,
  Ikon,
  aktiv,
  onClick,
  compact = false
}: Readonly<{
  href: string;
  etikett: string;
  Ikon?: LucideIcon;
  aktiv: boolean;
  onClick?: () => void;
  compact?: boolean;
}>) {
  return (
    <Link
      href={href}
      onClick={onClick}
      aria-current={aktiv ? "page" : undefined}
      title={etikett}
      className={cn(
        "focus-ring relative flex h-11 shrink-0 items-center gap-3 rounded-input px-3 text-[0.9375rem] transition-colors",
        "justify-center lg:justify-start",
        compact && "h-9 px-2 text-[0.8125rem]",
        aktiv
          ? "bg-paper/10 font-semibold text-paper"
          : "text-paper-muted hover:bg-paper/5 hover:text-paper"
      )}
    >
      <span
        aria-hidden
        className={cn(
          "absolute bottom-2 left-0 top-2 w-[2px] rounded-full bg-ochre transition-opacity",
          aktiv ? "opacity-100" : "opacity-0"
        )}
      />
      {Ikon ? (
        <Ikon className={cn("h-[18px] w-[18px] shrink-0", aktiv && "text-ochre")} aria-hidden />
      ) : (
        <span
          aria-hidden
          className={cn("h-1.5 w-1.5 shrink-0 rounded-full", aktiv ? "bg-ochre" : "bg-paper/30")}
        />
      )}
      <span className="hidden truncate lg:inline">{etikett}</span>
    </Link>
  );
}

export function Rail({
  logoHref,
  logoAriaLabel,
  brand,
  navLabel,
  groups,
  footer
}: Readonly<{
  logoHref: string;
  logoAriaLabel: string;
  /** Renderas direkt under märket — arbetsytans namn, demomarkören eller "Admin". */
  brand: React.ReactNode;
  navLabel: string;
  groups: RailNavGroup[];
  /** Botten av railen — inställningslänk, kontosaker, utloggning. */
  footer: React.ReactNode;
}>) {
  return (
    <aside className="rail sticky top-0 flex h-dvh w-[64px] shrink-0 flex-col bg-ink text-paper lg:w-[260px]">
      <div className="flex items-center gap-3 px-3 pb-4 pt-6 lg:px-5">
        <Link href={logoHref} className="focus-ring rounded-[6px]" aria-label={logoAriaLabel}>
          <span className="hidden lg:block">
            <Logo tone="paper" />
          </span>
          <span className="lg:hidden">
            <Logo tone="paper" compact />
          </span>
        </Link>
      </div>

      {brand}

      <nav
        aria-label={navLabel}
        className="thin-scrollbar flex min-h-0 flex-1 flex-col gap-1 overflow-y-auto px-2 lg:px-3"
      >
        {groups.map((group, gi) => (
          <Fragment key={group.key ?? gi}>
            {gi > 0 ? <div aria-hidden className="my-2 border-t border-paper/10" /> : null}
            {group.label ? (
              <p className="hidden px-3 pb-1 text-[0.6875rem] font-medium uppercase tracking-[0.14em] text-paper-subtle lg:block">
                {group.label}
              </p>
            ) : null}
            {group.items.map((item) =>
              item.children && item.children.length > 0 ? (
                // Med barn: en liten wrapper som håller posten och, när
                // sektionen är aktiv, den indragna undernavigeringen. Bara
                // poster med `children` tar den här vägen — se kommentaren på
                // `RailNavItem.children` för varför resten är opåverkade.
                <div key={item.href} className="flex flex-col gap-1">
                  <RailRad
                    href={item.href}
                    etikett={item.label}
                    Ikon={item.Icon}
                    aktiv={item.active}
                    onClick={item.onClick}
                  />
                  {item.active ? (
                    <div className="ml-4 flex flex-col gap-0.5 border-l border-paper/10 pl-2 lg:ml-5 lg:pl-3">
                      {item.children.map((child) => (
                        <RailRad
                          key={child.href}
                          href={child.href}
                          etikett={child.label}
                          aktiv={child.active}
                          compact
                        />
                      ))}
                    </div>
                  ) : null}
                </div>
              ) : (
                <RailRad
                  key={item.href}
                  href={item.href}
                  etikett={item.label}
                  Ikon={item.Icon}
                  aktiv={item.active}
                  onClick={item.onClick}
                />
              )
            )}
          </Fragment>
        ))}
      </nav>

      <div className="flex flex-col gap-1 border-t border-paper/10 px-2 py-3 lg:px-3">{footer}</div>
    </aside>
  );
}
