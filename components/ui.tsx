import { ArrowUpRight, CheckCircle2, Loader2 } from "lucide-react";
import type { Localized } from "@/lib/i18n";
import { cn } from "@/lib/utils";

/**
 * One button vocabulary for every product surface. Six variants had drifted apart
 * (different padding, weight, size, and one hovering to moss green), and a save
 * button that looks different in two places means one of them is wrong.
 *
 * Exported as class strings rather than a component so existing call sites adopt
 * them with a one-line change and keep their own element and handlers.
 */
export const btnBase =
  "focus-ring inline-flex min-h-11 items-center justify-center gap-2 rounded-input px-5 text-[0.9375rem] font-semibold transition-colors active:translate-y-px disabled:cursor-not-allowed disabled:opacity-40";

export const btnPrimary = `${btnBase} bg-ink text-paper hover:bg-ink2`;

export const btnSecondary = `${btnBase} bg-paper2 text-ink hover:bg-paper2/70`;

/**
 * STORLEK, inte en sjunde variant. Läggs ovanpå btnPrimary/btnSecondary med
 * `cn()` och rör bara höjd, luft och grad — färg, vikt och fokusring är
 * fortfarande vokabulärets.
 *
 * Finns för att bokföringens knappar står i rubrikrader vid sidan av
 * datumfälten och ska ha samma höjd som dem. Skrivet en gång här i stället för
 * som lösa klasser på anropsstället, av exakt det skäl som står ovan: sex
 * varianter hade redan glidit isär, och en storlek som bor på fyra ställen
 * glider isär på samma sätt.
 *
 * VARJE KLASS BÄR `!`, och det är inte slarv. `cn()` här i huset är ett rent
 * `join(" ")` utan tailwind-merge, så ordningen i class-attributet betyder
 * ingenting — det är ordningen i den GENERERADE css-filen som avgör, och där
 * kommer `min-h-11` efter `min-h-0`. Uppmätt i webbläsaren: utan `!` blev
 * knapparna 44 px medan datumfälten var 36, alltså precis den skillnad
 * modifieraren finns för att ta bort.
 */
export const btnLiten = "!min-h-0 !h-9 !gap-1.5 !px-3 !text-[0.875rem]";

export function Badge({ children, tone = "neutral" }: Readonly<{ children: React.ReactNode; tone?: "neutral" | "good" | "warn" | "danger" }>) {
  const tones = {
    neutral: "border-ink/10 bg-ink/[0.035] text-ink/70",
    good: "border-moss/20 bg-moss/10 text-moss",
    warn: "border-copper/25 bg-copper/10 text-ink",
    // text-ink, inte text-danger. Uppmätt på den KOMPOSITERADE ytan (badgens
    // egen 10-procentiga platta över pappret, inte token-värdet rakt av):
    // danger på den grunden ger 3,82:1 mot golvet 4,5:1 för brödtextgrad.
    // Allvaret bärs av kanten och plattan i stället, precis som tone="warn"
    // redan gör. Att mäta mot pappret ensamt hade sagt att den klarade sig.
    danger: "border-danger/40 bg-danger/10 text-ink"
  };
  return (
    <span className={cn("inline-flex items-center gap-1 rounded-[6px] border px-2.5 py-1 text-xs font-medium", tones[tone])}>
      {children}
    </span>
  );
}

export function ButtonLink({
  href,
  children,
  variant = "primary"
}: Readonly<{ href: string; children: React.ReactNode; variant?: "primary" | "secondary" | "ghost" }>) {
  const variants = {
    primary: "bg-ink text-paper hover:bg-copper hover:text-ink",
    secondary: "bg-paper text-ink shadow-hairline hover:bg-linen",
    ghost: "text-ink/70 hover:text-ink"
  };
  return (
    <a
      href={href}
      className={cn(
        "focus-ring inline-flex min-h-11 items-center gap-2 rounded-[7px] px-4 py-2.5 text-sm font-semibold transition",
        variants[variant]
      )}
    >
      {children}
      {variant !== "ghost" ? <ArrowUpRight className="h-4 w-4" /> : null}
    </a>
  );
}

export function MetricCard({
  label,
  value,
  detail,
  tone = "neutral"
}: Readonly<{ label: string; value: string; detail: string; tone?: "neutral" | "good" | "warn" }>) {
  return (
    <div className="rounded-[8px] bg-paper/72 p-4 shadow-hairline backdrop-blur">
      <div className="flex items-center justify-between gap-4">
        <p className="text-xs font-semibold uppercase tracking-[0.12em] text-ink/45">{label}</p>
        <span className={cn("h-2 w-2 rounded-full", tone === "good" ? "bg-moss" : tone === "warn" ? "bg-copper" : "bg-steel")} />
      </div>
      <p className="mt-4 font-display text-4xl leading-none">{value}</p>
      <p className="mt-2 text-sm text-ink/62">{detail}</p>
    </div>
  );
}

export function EmptyState({ title, body }: Readonly<{ title: string; body: string }>) {
  return (
    <div className="rounded-[8px] border border-dashed border-ink/15 bg-paper/45 p-8 text-center">
      <CheckCircle2 className="mx-auto h-6 w-6 text-moss" />
      <h3 className="mt-4 font-semibold">{title}</h3>
      <p className="mx-auto mt-2 max-w-md text-sm leading-6 text-ink/62">{body}</p>
    </div>
  );
}

export function SkeletonRows() {
  return (
    <div className="space-y-3">
      {Array.from({ length: 4 }).map((_, index) => (
        <div key={index} className="h-12 animate-pulse rounded-[7px] bg-ink/[0.055]" />
      ))}
    </div>
  );
}

export function LoadingToast({ label }: Readonly<{ label: string }>) {
  return (
    <div className="fixed bottom-5 right-5 z-40 inline-flex items-center gap-2 rounded-[8px] bg-ink px-4 py-3 text-sm text-paper shadow-lift">
      <Loader2 className="h-4 w-4 animate-spin" />
      {label}
    </div>
  );
}

export function localizedList(items: Localized[], text: (value: Localized) => string) {
  return items.map((item) => text(item));
}
