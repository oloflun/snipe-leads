"use client";

import {
  BookOpen,
  Headset,
  Inbox,
  LayoutDashboard,
  Mail,
  MessagesSquare,
  Plug,
  Settings
} from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Logo } from "@/components/Logo";
import { cn } from "@/lib/utils";

/**
 * Vänsterrailen — sajtens EN tonala inversion. Alltid synlig; smala skärmar
 * får ikonrail. Ordningen är arbetsordningen: läget (Översikt), arbetet
 * (Inkorg, och Chattar som agenten lämnat över), kunskapen (Kunskapsbas),
 * provet (Testchatt), och sist ramen.
 */

type Flik = {
  href: string;
  etikett: string;
  Ikon: typeof LayoutDashboard;
};

const FLIKAR: Flik[] = [
  { href: "/", etikett: "Översikt", Ikon: LayoutDashboard },
  { href: "/inkorg", etikett: "Inkorg", Ikon: Inbox },
  { href: "/chattar", etikett: "Chattar", Ikon: Headset },
  { href: "/kunskapsbas", etikett: "Kunskapsbas", Ikon: BookOpen },
  { href: "/testchatt", etikett: "Testchatt", Ikon: MessagesSquare }
];

const BOTTENFLIKAR: Flik[] = [
  { href: "/integrationer", etikett: "Integrationer", Ikon: Plug },
  { href: "/installningar", etikett: "Inställningar", Ikon: Settings },
  { href: "/kontakt", etikett: "Kontakt", Ikon: Mail }
];

function Flikrad({ flik, aktiv }: Readonly<{ flik: Flik; aktiv: boolean }>) {
  const { href, etikett, Ikon } = flik;
  return (
    <Link
      href={href}
      aria-current={aktiv ? "page" : undefined}
      title={etikett}
      className={cn(
        "relative flex h-11 items-center gap-3 rounded-[8px] px-3 text-[0.9375rem] transition-colors",
        "justify-center lg:justify-start",
        aktiv
          ? "bg-paper/10 font-semibold text-paper"
          : "text-paper/60 hover:bg-paper/5 hover:text-paper"
      )}
    >
      <span
        aria-hidden
        className={cn(
          "absolute left-0 top-2 bottom-2 w-[2px] rounded-full bg-ochre transition-opacity",
          aktiv ? "opacity-100" : "opacity-0"
        )}
      />
      <Ikon className={cn("h-[18px] w-[18px] shrink-0", aktiv && "text-ochre")} aria-hidden />
      <span className="hidden lg:inline">{etikett}</span>
    </Link>
  );
}

export function Sidebar({ kundnamn = null }: Readonly<{ kundnamn?: string | null }>) {
  const pathname = usePathname();
  const arAktiv = (href: string) =>
    href === "/" ? pathname === "/" : pathname.startsWith(href);

  return (
    <aside className="rail sticky top-0 flex h-dvh w-[64px] shrink-0 flex-col bg-ink text-paper lg:w-[260px]">
      <div className="flex items-center gap-3 px-3 pb-5 pt-6 lg:px-5">
        <Link href="/" className="focus-ring rounded-[6px]" aria-label="Snajp Support — till översikten">
          <span className="hidden lg:block">
            <Logo tone="paper" />
          </span>
          <span className="lg:hidden">
            <Logo tone="paper" compact />
          </span>
        </Link>
      </div>
      <p className="hidden px-5 pb-4 text-[0.75rem] font-medium uppercase tracking-[0.14em] text-paper/40 lg:block">
        Support
      </p>

      <nav aria-label="Huvudmeny" className="flex min-h-0 flex-1 flex-col gap-1 overflow-y-auto px-2 lg:px-3">
        {FLIKAR.map((flik) => (
          <Flikrad key={flik.href} flik={flik} aktiv={arAktiv(flik.href)} />
        ))}
      </nav>

      <div className="border-t border-paper/10 px-2 py-3 lg:px-3">
        {BOTTENFLIKAR.map((flik) => (
          <Flikrad key={flik.href} flik={flik} aktiv={arAktiv(flik.href)} />
        ))}
        <div className="hidden px-3 pb-1 pt-4 lg:block">
          {kundnamn ? (
            <p className="truncate text-[0.8125rem] leading-5 text-paper/60" title={kundnamn}>
              {kundnamn}
            </p>
          ) : null}
          <div className="flex items-baseline gap-2 text-[0.75rem] leading-5 text-paper/35">
            <span>En tjänst från Snajp</span>
            <form method="post" action="/api/logga-ut">
              <button
                type="submit"
                className="focus-ring rounded-[4px] text-paper/45 underline decoration-paper/25 underline-offset-4 transition-colors hover:text-paper"
              >
                Logga ut
              </button>
            </form>
          </div>
        </div>
      </div>
    </aside>
  );
}
