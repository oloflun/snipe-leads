"use client";

import { ChevronDown } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { shared } from "@/components/marketing/copy";
import { useLocale } from "@/lib/i18n";
import { cn } from "@/lib/utils";

/**
 * Menyn i marknadssidans högra hörn.
 *
 * ## Varför en meny och inte fyra länkar
 *
 * Sidhuvudet bär redan språkval, inloggning och den primära uppmaningen. Fyra
 * länkar till hade gjort raden till en lista där ingenting sticker ut — och det
 * som ska sticka ut är "Skriv till oss". Menyn samlar det som är BRA att kunna
 * hitta men som ingen kom till sidan för att göra.
 *
 * ## Varför ankarlänkar och inte egna sidor
 *
 * Allt innehåll finns redan på sidan: frågorna, kontaktuppgifterna,
 * dataskyddet och avsnittet om oss. Egna sidor hade betytt fyra nya URL:er som
 * upprepar det man just skrollat förbi, och en besökare som klickar tillbaka
 * tappar sin plats. Ankaret behåller sammanhanget.
 *
 * UNDANTAGET är GDPR-posten. Integritetspolicyn är ett dokument och inte ett
 * avsnitt: den ska gå att länka till, bokmärka och skicka till en inköpares
 * jurist, och inget av det fungerar med ett ankare mitt i en säljsida.
 *
 * ## Tangentbord och fokus
 *
 * Escape stänger, klick utanför stänger. Utan det första sitter en tangentbords-
 * användare fast i menyn; utan det andra ligger den kvar över innehållet man
 * försökte läsa.
 */

type Post = { etikett: string; href: string };

export function SidMeny({ tone = "paper" }: Readonly<{ tone?: "paper" | "ink" }>) {
  const { text } = useLocale();
  const [oppen, setOppen] = useState(false);
  const rot = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (!oppen) return;

    function vidKlick(handelse: MouseEvent) {
      if (rot.current && !rot.current.contains(handelse.target as Node)) {
        setOppen(false);
      }
    }
    function vidTangent(handelse: KeyboardEvent) {
      if (handelse.key === "Escape") setOppen(false);
    }

    document.addEventListener("mousedown", vidKlick);
    document.addEventListener("keydown", vidTangent);
    return () => {
      document.removeEventListener("mousedown", vidKlick);
      document.removeEventListener("keydown", vidTangent);
    };
  }, [oppen]);

  const poster: Post[] = [
    { etikett: text(shared.menyKontakt), href: "#kontakt" },
    { etikett: text(shared.menyPriser), href: "#priser" },
    { etikett: text(shared.menyFragor), href: "#fragor" },
    { etikett: text(shared.menyVilka), href: "#vilka-ar-vi" },
    // Den enda posten som lämnar sidan. #dataskydd-avsnittet i sidfoten är
    // en sammanfattning på fyra rader; den som klickar "GDPR och data" vill
    // läsa hela behandlingen, och ett ankare till en sammanfattning svarar
    // inte på den frågan. Sammanfattningen har i stället en egen länk hit.
    { etikett: text(shared.menyGdpr), href: "/integritetspolicy" }
  ];

  const ljus = tone === "paper";

  return (
    <div ref={rot} className="relative">
      <button
        type="button"
        onClick={() => setOppen((v) => !v)}
        aria-expanded={oppen}
        aria-haspopup="true"
        className={cn(
          "focus-ring inline-flex min-h-11 items-center gap-1.5 rounded-input px-3 text-sm font-medium transition-colors",
          ljus ? "text-paper/70 hover:text-paper" : "text-ink/60 hover:text-ink"
        )}
      >
        {text(shared.menyEtikett)}
        <ChevronDown
          className={cn("h-4 w-4 transition-transform", oppen && "rotate-180")}
          aria-hidden
        />
      </button>

      {oppen ? (
        <div
          className="absolute right-0 top-full z-40 mt-1 w-56 overflow-hidden rounded-card border border-ink/10 bg-paper shadow-lift"
          role="menu"
        >
          {poster.map((post) => (
            <a
              key={post.href}
              href={post.href}
              role="menuitem"
              onClick={() => setOppen(false)}
              className="focus-ring block px-4 py-3 text-[0.9375rem] text-ink/75 transition-colors hover:bg-paper2 hover:text-ink"
            >
              {post.etikett}
            </a>
          ))}
        </div>
      ) : null}
    </div>
  );
}
