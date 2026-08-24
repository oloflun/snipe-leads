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
 * ihop raden — och 2026-08-25 skalades hela `hjalte`-lockupen ned 50 % mot
 * originalet (28→14, 88→44, gap och ordmärke i samma proportion), vilket
 * bara gör mobilmarginalen större.
 *
 * Ordmärket är sedan samma datum den riktiga varumärkesfilen
 * (`snajp-wordmark-v1-*.svg`), inte längre livrenderad text — samma svart/
 * vit-par som märket, faktor ~0,84 mot märkets höjd oförändrad.
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
        // 50% mindre än originalet (var clamp(8px,1.2vw,20px)) — hjälten är
        // det enda stället `hjalte` används (startsidans header).
        hjalte ? "gap-[clamp(4px,0.6vw,10px)]" : stor ? "gap-3" : "gap-2.5"
      )}
    >
      <Image
        src={tone === "paper" ? "/snajp-symbol-white.svg" : "/snajp-symbol-black.svg"}
        alt=""
        width={200}
        height={158}
        className={cn(
          "w-auto object-contain",
          // 50% mindre än originalet (var clamp(28px,5.2vw,88px)).
          hjalte ? "h-[clamp(14px,2.6vw,44px)]" : stor ? "h-[34px]" : "h-[18px]"
        )}
        priority
      />
      {!compact ? (
        <span className="flex flex-col justify-center">
          {/* Ordmärket, inte livrenderad text — se filhuvudets kommentar. */}
          <Image
            src={tone === "paper" ? "/snajp-wordmark-v1-white.svg" : "/snajp-wordmark-v1-black.svg"}
            alt="Snajp"
            width={325}
            height={122}
            className={cn(
              "w-auto object-contain",
              // Faktor ~0,84 mot märkets höjd (se filhuvudet).
              hjalte ? "h-[clamp(12px,2.2vw,37px)]" : stor ? "h-[29px]" : "h-[15px]"
            )}
            priority
          />
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
