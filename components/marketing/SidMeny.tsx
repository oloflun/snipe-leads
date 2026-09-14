"use client";

import { ChevronDown } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
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
 * ## Ankare eller egen sida, post för post
 *
 * Den ursprungliga regeln var "allt innehåll finns redan på sidan, alltså
 * ankare". Den gäller fortfarande för PRISER: prissektionen är en del av
 * säljargumentet där den står, och en egen prissida hade betytt en URL som
 * upprepar det man just skrollat förbi.
 *
 * De fyra andra pekar numera på egna sidor, och skälet är detsamma som gjorde
 * integritetspolicyn till ett undantag från början: det här är saker man
 * länkar till, bokmärker och skickar vidare. En bokning har ett eget
 * tillstånd (ifylld, skickad, bekräftad) som ett ankare mitt i en säljsida
 * inte kan bära. En FAQ med sökruta vill äga sin adress, så `/faq#gdpr` går
 * att klistra in i ett svarsmejl. Och en teampresentation är det man skickar
 * till någon som frågat vilka ni är.
 *
 * Ankaret behåller sammanhang; sidan behåller adressen. Valet står mellan de
 * två, och avgörs av om innehållet ska gå att peka på.
 *
 * ## Tangentbord och fokus
 *
 * Escape stänger, klick utanför stänger. Utan det första sitter en tangentbords-
 * användare fast i menyn; utan det andra ligger den kvar över innehållet man
 * försökte läsa.
 */

type Post = { etikett: string; href: string };

/**
 * Om posten pekar på den sida man redan står på.
 *
 * Bara för postar med en egen route. Ett ankare ("#priser") är aldrig
 * "aktivt": man står på sidan det pekar på oavsett om man skrollat dit, och
 * att markera det hade gjort markeringen till brus i stället för till besked.
 */
function arAktiv(href: string, sokvag: string | null): boolean {
  return href.startsWith("/") && sokvag === href;
}

export function SidMeny({ tone = "paper" }: Readonly<{ tone?: "paper" | "ink" }>) {
  const { text } = useLocale();
  const sokvag = usePathname();
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
    { etikett: text(shared.menyBokaDemo), href: "/boka-demo" },
    // Kvar som ankare. Se resonemanget överst: prissektionen hör hemma i
    // säljflödet den står i.
    { etikett: text(shared.menyPriser), href: "#priser" },
    { etikett: text(shared.menyFaq), href: "/faq" },
    { etikett: text(shared.menyTeam), href: "/vart-team" },
    // #dataskydd-avsnittet i sidfoten är en sammanfattning på fyra rader; den
    // som klickar "Dataskydd" vill läsa hela behandlingen, och ett ankare till
    // en sammanfattning svarar inte på den frågan. Sammanfattningen har i
    // stället en egen länk hit.
    { etikett: text(shared.menyDataskydd), href: "/integritetspolicy" }
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
          {poster.map((post) => {
            const aktiv = arAktiv(post.href, sokvag);
            const klass = cn(
              "focus-ring block px-4 py-3 text-[0.9375rem] transition-colors hover:bg-paper2 hover:text-ink",
              aktiv ? "bg-paper2 font-semibold text-ink" : "text-ink/75"
            );
            // aria-current och inte bara en fetare vikt: markeringen ska nå
            // den som inte ser den. Utan attributet är en aktiv post
            // oskiljbar från de andra i en skärmläsare.
            const gemensamt = {
              role: "menuitem" as const,
              onClick: () => setOppen(false),
              className: klass,
              ...(aktiv ? { "aria-current": "page" as const } : {})
            };

            // Ankaret måste vara ett <a>. next/link gör en klientnavigering av
            // "#priser", och den scrollar inte — hela poängen med ankaret.
            return post.href.startsWith("/") ? (
              <Link key={post.href} href={post.href} {...gemensamt}>
                {post.etikett}
              </Link>
            ) : (
              <a key={post.href} href={post.href} {...gemensamt}>
                {post.etikett}
              </a>
            );
          })}
        </div>
      ) : null}
    </div>
  );
}
