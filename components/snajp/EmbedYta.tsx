"use client";

import Image from "next/image";
import { X } from "lucide-react";
import { useEffect, useState } from "react";
import { SupportChat } from "@/components/snajp/SupportChat";
import type { TenantLogo } from "@/lib/tenants";

/**
 * Widgetens innehåll — det som renderas INUTI iframen på kundens sajt.
 *
 * Klientkomponent av två skäl: sessionsidentiteten bor i sessionStorage
 * (samma mönster som demoSessionId i SupportChat, egen nyckel per kund så
 * två kunders widgetar i samma webbläsare aldrig delar samtal), och
 * stängknappen talar med föräldrasidan via postMessage — widget.js lyssnar
 * och fäller ihop panelen.
 *
 * Meddelandena till föräldern bär ingen kunddata: en färg och en typ. Därför
 * targetOrigin "*" — kundens sajt-origin är inte känd härifrån, och det enda
 * en tjuvlyssnare kan läsa är accentfärgen vi ändå visar öppet.
 */
export type EmbedYtaProps = {
  slug: string;
  namn: string;
  logo: TenantLogo;
  /** Accentfärgen som CSS-värde, t.ex. "oklch(0.48 0.105 215)" — till knappen på kundens sida. */
  farg: string;
  /** Pratbubblan som frågar först, om kunden har en (lib/tenants/types.ts). */
  inbjudan?: { rubrik: string; text: string };
};

function embedSessionId(slug: string): string {
  const KEY = `snajp.embed.session.${slug}`;
  let id = window.sessionStorage.getItem(KEY);
  if (!id) {
    id = crypto.randomUUID();
    window.sessionStorage.setItem(KEY, id);
  }
  return id;
}

function tillForaldern(data: Record<string, string>) {
  if (window.parent !== window) {
    window.parent.postMessage(data, "*");
  }
}

export function EmbedYta({ slug, namn, logo, farg, inbjudan }: EmbedYtaProps) {
  // Sessionen skapas först på klienten — servern känner ingen identitet, och
  // utan vakten hade SSR och klient renderat olika props (hydreringskrock).
  const [session, setSession] = useState<string | null>(null);
  useEffect(() => {
    setSession(embedSessionId(slug));
    // Inbjudans text följer med hit: widget.js är gemensam för alla kunder
    // och ska inte bära en enda kunds mening. Fälten utelämnas när kunden
    // saknar inbjudan, och då ritar skriptet ingen bubbla.
    tillForaldern({
      typ: "snajp:redo",
      farg,
      ...(inbjudan
        ? { inbjudanRubrik: inbjudan.rubrik, inbjudanText: inbjudan.text }
        : {})
    });
  }, [slug, farg, inbjudan]);

  const morkt = logo.background === "dark";

  return (
    <div className="flex h-dvh min-h-0 flex-col bg-paper">
      <header className={morkt ? "bg-ink" : "border-b border-ink/10 bg-paper"}>
        <div className="flex items-center justify-between gap-3 px-4 py-3">
          <Image
            src={logo.src}
            alt={logo.alt}
            width={logo.width}
            height={logo.height}
            priority
            className="h-7 w-auto"
          />
          <div className="flex items-center gap-3">
            <span className={morkt ? "kicker text-paper-subtle" : "kicker text-mineral"}>
              Powered by Snajp
            </span>
            <button
              type="button"
              onClick={() => tillForaldern({ typ: "snajp:stang" })}
              className={
                "focus-ring rounded-full p-1.5 transition-colors " +
                (morkt
                  ? "text-paper-subtle hover:bg-paper/10 hover:text-paper"
                  : "text-mineral hover:bg-ink/5 hover:text-ink")
              }
              aria-label={`Stäng chatten med ${namn}`}
            >
              <X className="h-4 w-4" />
            </button>
          </div>
        </div>
      </header>

      <div className="min-h-0 flex-1">
        {session ? <SupportChat tenant={slug} session={session} layout="fyll" /> : null}
      </div>
    </div>
  );
}
