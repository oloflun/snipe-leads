import Image from "next/image";

/**
 * Wordmark is set in Geist, not Fraunces: DESIGN.md limits the display serif to a
 * single hero per page, and a serif wordmark would compete with it.
 * The bordered tile and the "sales os" kicker were editorial cues and are gone.
 */
export function Logo({ compact = false }: Readonly<{ compact?: boolean }>) {
  return (
    <span className="inline-flex items-center gap-2.5">
      <Image
        src="/snipe_logo.svg"
        alt=""
        width={30}
        height={19}
        className="h-[18px] w-auto object-contain"
        priority
      />
      {!compact ? (
        <span className="text-[19px] font-semibold leading-none tracking-[-0.02em]">Snajp</span>
      ) : null}
    </span>
  );
}
