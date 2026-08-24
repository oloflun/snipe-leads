import Image from "next/image";
import { cn } from "@/lib/utils";

/**
 * Wordmark is set in Geist, not Fraunces: DESIGN.md limits the display serif to a
 * single hero per page, and a serif wordmark would compete with it.
 * The bordered tile and the "sales os" kicker were editorial cues and are gone.
 *
 * ## `stor` och `undertext`
 *
 * Headern hade tidigare två rader: logotypen på den ena, flikarna på den andra.
 * Logotypen blev då en liten detalj ovanför navigationen i stället för husets
 * märke. `stor` ger den höjden av båda raderna, och `undertext` lägger
 * arbetsytans namn UNDER ordmärket i stället för bredvid — så att kolumnen blir
 * lika hög som flikraden bredvid.
 *
 * Måtten är inte godtyckliga: 34px märke + 26px ordmärke + 13px undertext möter
 * flikradens 44px minsta träffyta utan att headern växer.
 *
 * ## `hjalte`
 *
 * Marknadssidornas hjältebild. Där är logotypen inte en navigationsdetalj utan
 * husets märke över en helskärmsbild, och 34px försvinner i den ytan.
 *
 * Måtten är `clamp()` och inte fasta pixlar: hjälten spänner över hela
 * skärmbredden, och ett märke som är rätt på 1600px är ett märke som täcker
 * halva mobilskärmen.
 *
 * Ordmärket följer märkets höjd med faktor ~0,84. Högre än så och ordet tar
 * över märket; lägre och de två läser som en bild bredvid ett ord i stället för
 * som en enhet.
 *
 * vw-faktorn är medvetet lägre än vad ytterlägena ensamma skulle kräva. Med en
 * brantare faktor slog clamp:en i taket redan vid ~1400px, och en 1280-skärm
 * fick nästan samma märke som en 1900 — mellanbredderna såg trängda ut.
 *
 * Undre gränsen var satt av MOBILEN: lockupen delar rad med EN, Logga in och
 * Meny, och 38px märke bröt "Logga in" till två rader på 390px. 28px höll
 * ihop raden — och 2026-08-25 skalades hela `hjalte`-lockupen ned 30 % (28→20,
 * 88→62, gap och textstorlek i samma proportion), vilket bara gör
 * mobilmarginalen större.
 */
export function Logo({
  compact = false,
  tone = "ink",
  stor = false,
  hjalte = false,
  undertext = null
}: Readonly<{
  compact?: boolean;
  tone?: "ink" | "paper";
  stor?: boolean;
  hjalte?: boolean;
  undertext?: string | null;
}>) {
  return (
    <span
      className={cn(
        "inline-flex items-center",
        hjalte ? "gap-[clamp(6px,0.84vw,14px)]" : stor ? "gap-3" : "gap-2.5"
      )}
    >
      <Image
        src={tone === "paper" ? "/snajp-symbol-white.svg" : "/snajp-symbol-black.svg"}
        alt=""
        width={200}
        height={158}
        className={cn(
          "w-auto object-contain",
          // 30% mindre än tidigare (var clamp(28px,5.2vw,88px)) — hjälten är
          // det enda stället `hjalte` används (startsidans header).
          hjalte ? "h-[clamp(20px,3.6vw,62px)]" : stor ? "h-[34px]" : "h-[18px]"
        )}
        priority
      />
      {!compact ? (
        <span className="flex flex-col justify-center">
          <span
            className={cn(
              "font-semibold leading-none tracking-[-0.02em]",
              hjalte
                ? "text-[clamp(14px,3.1vw,52px)]"
                : stor
                  ? "text-[26px]"
                  : "text-[19px]"
            )}
          >
            Snajp
          </span>
          {/* Undertexten renderas bara i stort läge. I kompakt läge finns ingen
              höjd att lägga den på, och en rad som ibland finns och ibland inte
              flyttar allt annat i headern när den dyker upp. */}
          {stor && undertext ? (
            <span className="mt-1 hidden text-[13px] leading-none text-ink/45 sm:block">
              {undertext}
            </span>
          ) : null}
        </span>
      ) : null}
    </span>
  );
}
