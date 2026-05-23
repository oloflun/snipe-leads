import Image from "next/image";

export function Logo({ compact = false }: Readonly<{ compact?: boolean }>) {
  return (
    <span className="inline-flex items-center gap-3">
      <span className="grid h-11 w-11 place-items-center overflow-hidden border border-ink/15 bg-paper2">
        <Image src="/snipe_logo.svg" alt="" width={34} height={22} className="object-contain" />
      </span>
      {!compact ? (
        <span className="flex flex-col leading-none">
          <span className="font-display text-xl font-semibold tracking-normal">Snipra</span>
          <span className="kicker mt-2 text-mineral">sales os</span>
        </span>
      ) : null}
    </span>
  );
}
