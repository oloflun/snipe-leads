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
 */
export function Logo({
  compact = false,
  tone = "ink",
  stor = false,
  undertext = null
}: Readonly<{
  compact?: boolean;
  tone?: "ink" | "paper";
  stor?: boolean;
  undertext?: string | null;
}>) {
  return (
    <span className={cn("inline-flex items-center", stor ? "gap-3" : "gap-2.5")}>
      <Image
        src="/snipe_logo.svg"
        alt=""
        width={30}
        height={19}
        className={cn(
          "w-auto object-contain",
          stor ? "h-[34px]" : "h-[18px]",
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
              stor ? "text-[26px]" : "text-[19px]"
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
