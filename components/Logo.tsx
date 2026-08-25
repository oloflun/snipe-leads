import Image from "next/image";
import { cn } from "@/lib/utils";

/**
 * Husets märke. Sedan 2026-08-25 ritas ingenting av komponenten — varken
 * symbolen eller ordet. Båda kommer ur varumärkesfilerna i `public/`.
 *
 * ## En fil, inte tre mått
 *
 * `compact` ger symbolen ensam (`snajp-symbol-*.svg`). Allt annat ger den
 * färdiga lockupen (`snajp-logo-v1-*.svg`), där symbol, mellanrum och ordmärke
 * redan står i rätt förhållande:
 *
 *     ordmärkets höjd  = 0,775 × symbolens
 *     mellanrummet     = 0,165 × symbolens
 *     lockupens höjd   = 0,991 × symbolens
 *
 * Komponenten satte tidigare de tre måtten var för sig, med en handskriven
 * faktor ärvd från när ordet var livrenderad text. Den gissningen behövs inte
 * när filen bär förhållandet: ETT h-värde räcker, och delarna kan inte glida
 * isär.
 *
 * Ett försök att skala ordmärket separat (två bilder, `items-end`) prövades
 * och förkastades samma dag — förhållandet i filen är designerns, och att
 * dra isär det gjorde lockupen sämre även när den lodräta relationen räknades
 * fram exakt. Rör inte delarna var för sig; ändra höjden nedan i stället.
 *
 * ## Svart och vitt är två FILER
 *
 * Inte ett `invert`-filter. Ett inverterat mörkt märke är inte samma sak som
 * det vita originalet.
 *
 * ## Lägena och måtten
 *
 * `hjalte` — marknadssidornas hjältebild, där logotypen inte är en
 * navigationsdetalj utan husets märke över en helskärmsbild. `clamp()` och
 * inte fasta pixlar: hjälten spänner över hela skärmbredden, och ett märke som
 * är rätt på 1600px täcker halva mobilskärmen. vw-faktorn är medvetet lägre än
 * ytterlägena ensamma skulle kräva — med en brantare faktor slog clamp:en i
 * taket redan vid ~1400px och mellanbredderna såg trängda ut.
 *
 * `stor` — arbetsytans header, med `undertext` för arbetsytans namn under
 * lockupen. `compact` — symbolen ensam, för ytor utan bredd att ge.
 *
 * Höjderna hänger ihop och ska ändras tillsammans: 55 och 29 ligger nära
 * hjältens 58 på vanliga skärmbredder. De stod på 34 och 18 medan logotypen
 * var symbol + livrenderad text, och en 34px lockup bredvid hjältens läste som
 * ett annat, blekare märke. EN logotyp, samma tyngd överallt.
 *
 * Måttkedjan för `hjalte`, för den som undrar var talen kommer ifrån:
 * originalet 28/5,2vw/88 → halverat → +30 % → +20 % = 21,8/4,06vw/68,6.
 */
function hojd(hjalte: boolean, stor: boolean): string {
  if (hjalte) return "h-[clamp(21.84px,4.06vw,68.64px)]";
  return stor ? "h-[55px]" : "h-[29px]";
}

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
  const kulor = tone === "paper" ? "white" : "black";

  const bild = compact ? (
    <Image
      src={`/snajp-symbol-${kulor}.svg`}
      alt="Snajp"
      width={200}
      height={158}
      className={cn("w-auto object-contain", hojd(hjalte, stor))}
      priority
    />
  ) : (
    <Image
      src={`/snajp-logo-v1-${kulor}.svg`}
      alt="Snajp"
      width={552}
      height={159}
      className={cn("w-auto object-contain", hojd(hjalte, stor))}
      priority
    />
  );

  // Utan undertext är lockupen hela logotypen — ingen wrapper behövs.
  if (!stor || !undertext) return bild;

  return (
    <span className="inline-flex flex-col justify-center">
      {bild}
      {/* Undertexten renderas bara i stort läge. I kompakt läge finns ingen
          höjd att lägga den på, och en rad som ibland finns och ibland inte
          flyttar allt annat i headern när den dyker upp. */}
      <span className="mt-1 hidden text-[13px] leading-none text-ink/45 sm:block">
        {undertext}
      </span>
    </span>
  );
}
