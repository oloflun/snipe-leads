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
 * halva mobilskärmen. Nedre gränsen (56px) är fortfarande större än `stor`,
 * övre (120px) är måttet ur utkastet.
 *
 * Ordmärket följer märkets höjd med faktor ~0,84. Högre än så och ordet tar
 * över märket; lägre och de två läser som en bild bredvid ett ord i stället för
 * som en enhet.
 *
 * vw-faktorn är medvetet lägre än vad ytterlägena ensamma skulle kräva. Med en
 * brantare faktor slog clamp:en i taket redan vid ~1400px, och en 1280-skärm
 * fick nästan samma märke som en 1900 — mellanbredderna såg trängda ut.
 *
 * Undre gränsen är satt av MOBILEN och inget annat: lockupen delar rad med
 * EN, Logga in och Meny. Med 38px märke tog den så mycket bredd på 390px att
 * "Logga in" bröts till två rader. 28px är den största storlek där raden
 * fortfarande håller ihop.
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
        hjalte ? "gap-[clamp(8px,1.2vw,20px)]" : stor ? "gap-3" : "gap-2.5"
      )}
    >
      <Image
        src="/snipe_logo.svg"
        alt=""
        width={30}
        height={19}
        className={cn(
          "w-auto object-contain",
          hjalte ? "h-[clamp(28px,5.2vw,88px)]" : stor ? "h-[34px]" : "h-[18px]",
          // Märket är mörkt. På ett mörkt underlag försvinner det helt utan
          // inverteringen — se DESIGN.md om tenant-logotypernas background.
          tone === "paper" && "invert"
        )}
        priority
      />
      {!compact ? (
        <span className="flex flex-col justify-center">
          <span
            className={cn(
              "font-semibold leading-none tracking-[-0.02em]",
              hjalte
                ? "text-[clamp(20px,4.4vw,74px)]"
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
