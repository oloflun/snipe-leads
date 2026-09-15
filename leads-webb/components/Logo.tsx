import Image from "next/image";
import { cn } from "@/lib/utils";

/**
 * Husets märke, samma varumärkesfiler som huvudappen (kopierade till public/).
 * Svart och vitt är två FILER, aldrig ett invert-filter — ett inverterat
 * mörkt märke är inte samma sak som det vita originalet.
 */
export function Logo({
  compact = false,
  tone = "ink",
  className
}: Readonly<{ compact?: boolean; tone?: "ink" | "paper"; className?: string }>) {
  const kulor = tone === "paper" ? "white" : "black";

  if (compact) {
    return (
      <Image
        src={`/snajp-symbol-${kulor}.svg`}
        alt="Snajp"
        width={200}
        height={158}
        className={cn("h-[26px] w-auto object-contain", className)}
        priority
      />
    );
  }

  return (
    <Image
      src={`/snajp-logo-v1-${kulor}.svg`}
      alt="Snajp"
      width={552}
      height={159}
      className={cn("h-[27px] w-auto object-contain", className)}
      priority
    />
  );
}
