"use client";

import { ChevronDown, Search } from "lucide-react";
import Link from "next/link";
import { useId, useMemo, useState } from "react";
import { FAQ, FAQ_KATEGORIER, type FaqPost } from "@/lib/faq";
import { useLocale } from "@/lib/i18n";
import { cn } from "@/lib/utils";

/**
 * Frågorna som ett dragspel, grupperade per kategori, med fritextsökning.
 *
 * ## En öppen i taget
 *
 * Att öppna en fråga stänger den förra. Skälet är inte estetik: med fjorton
 * frågor öppna samtidigt blir sidan en vägg igen, alltså precis det tillstånd
 * dragspelet skulle lösa. Undantaget är sökläget — där är träffarna redan få
 * och utvalda, och att då kräva ett klick till för att läsa svaret är att låta
 * mönstret gå före nyttan.
 *
 * ## Tillgänglighet
 *
 * Knapp och inte div: då kommer Enter, Space, fokusring och läsordning gratis
 * från plattformen i stället för att behöva byggas om för hand. `aria-expanded`
 * säger tillståndet, `aria-controls` binder ihop knappen med sitt svar, och
 * svaret får `role="region"` med `aria-labelledby` tillbaka till frågan så att
 * en skärmläsare vet vad regionen heter.
 *
 * Panelen tas ur DOM:en när den är stängd i stället för att döljas med CSS.
 * En `hidden`-panel är fortfarande sökbar med webbläsarens egen sidsökning och
 * dess länkar är fortfarande tabbbara — vilket ger en tangentbordsanvändare
 * fokus på något osynligt.
 *
 * ## Ankare
 *
 * Varje fråga bär sitt id, så `/faq#gdpr` går att skicka i ett mejl. Öppnas
 * sidan med ett ankare fälls den frågan ut direkt; annars är allt stängt.
 */

function träffar(post: FaqPost, fras: string, text: (v: { sv: string; en: string }) => string) {
  const n = fras.trim().toLowerCase();
  if (!n) return true;
  const hö = [text(post.fraga), ...post.svar.map(text)].join(" ").toLowerCase();
  // Varje ord måste finnas, men inte i ordning. "moms kvitto" hittar frågan
  // som nämner båda, och en sökning som krävt frasen hade gett noll träffar
  // på det vanligaste sättet folk söker.
  return n.split(/\s+/).every((ord) => hö.includes(ord));
}

export function FaqDragspel({ start }: Readonly<{ start?: string }>) {
  const { text } = useLocale();
  const [oppen, setOppen] = useState<string | null>(start ?? null);
  const [fras, setFras] = useState("");
  const sokId = useId();

  const soker = fras.trim().length > 0;
  const synliga = useMemo(() => FAQ.filter((p) => träffar(p, fras, text)), [fras, text]);

  return (
    <div className="mt-12">
      <div className="relative">
        <Search
          className="pointer-events-none absolute left-4 top-1/2 h-4 w-4 -translate-y-1/2 text-ink/40"
          aria-hidden
        />
        <label htmlFor={sokId} className="sr-only">
          {text({ sv: "Sök bland frågorna", en: "Search the questions" })}
        </label>
        <input
          id={sokId}
          type="search"
          value={fras}
          onChange={(e) => setFras(e.target.value)}
          placeholder={text({ sv: "Sök bland frågorna", en: "Search the questions" })}
          className="focus-ring min-h-12 w-full rounded-input bg-paper2 pl-11 pr-4 text-[1rem]"
        />
      </div>

      {/* Antalet träffar sägs i en live-region. Utan den vet den som söker med
          skärmläsare inte att listan under ändrat sig — fältet ger ingen
          återkoppling av sig självt. */}
      <p aria-live="polite" className="mt-3 text-[0.875rem] text-ink/50">
        {soker
          ? text({
              sv: `${synliga.length} träffar`,
              en: `${synliga.length} matches`
            })
          : ""}
      </p>

      {synliga.length === 0 ? (
        <p className="mt-8 text-[1rem] leading-[1.7] text-ink/70">
          {text({
            sv: "Ingen fråga matchar. Hör av dig, så svarar vi direkt.",
            en: "No question matches. Get in touch and we will answer directly."
          })}{" "}
          <Link href="/boka-demo" className="underline underline-offset-4 hover:text-ochre">
            {text({ sv: "Boka demo", en: "Book a demo" })}
          </Link>
        </p>
      ) : null}

      {FAQ_KATEGORIER.map((kategori) => {
        const poster = synliga.filter((p) => p.kategori === kategori.nyckel);
        if (!poster.length) return null;

        return (
          <section key={kategori.nyckel} className="mt-12 first:mt-8">
            <h2 className="kicker text-mineral">{text(kategori.etikett)}</h2>
            <div className="mt-4 border-t border-ink/12">
              {poster.map((post) => {
                // I sökläge är allt utfällt: träffarna är få och redan valda,
                // och ett klick till för att se svaret är ren friktion.
                const utfalld = soker || oppen === post.id;
                return (
                  <div key={post.id} id={post.id} className="scroll-mt-24 border-b border-ink/12">
                    <h3>
                      <button
                        type="button"
                        aria-expanded={utfalld}
                        aria-controls={`svar-${post.id}`}
                        id={`fraga-${post.id}`}
                        onClick={() => setOppen(utfalld && !soker ? null : post.id)}
                        className="focus-ring flex w-full items-start justify-between gap-4 py-5 text-left"
                      >
                        <span className="font-display text-[1.125rem] font-semibold leading-snug tracking-[-0.015em]">
                          {text(post.fraga)}
                        </span>
                        <ChevronDown
                          className={cn(
                            "mt-1 h-5 w-5 shrink-0 text-ink/45 transition-transform",
                            utfalld && "rotate-180"
                          )}
                          aria-hidden
                        />
                      </button>
                    </h3>

                    {utfalld ? (
                      <div
                        id={`svar-${post.id}`}
                        role="region"
                        aria-labelledby={`fraga-${post.id}`}
                        className="pb-6"
                      >
                        {post.svar.map((stycke) => (
                          <p
                            key={stycke.sv}
                            className="mt-0 max-w-[62ch] pt-1 text-[1rem] leading-[1.7] text-ink/72 [&+&]:mt-4"
                          >
                            {text(stycke)}
                          </p>
                        ))}
                        {post.lank ? (
                          <Link
                            href={post.lank.href}
                            className="focus-ring mt-4 inline-block text-[0.9375rem] font-medium underline underline-offset-4 hover:text-ochre"
                          >
                            {text(post.lank.etikett)}
                          </Link>
                        ) : null}
                      </div>
                    ) : null}
                  </div>
                );
              })}
            </div>
          </section>
        );
      })}
    </div>
  );
}
