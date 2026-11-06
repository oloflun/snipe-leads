import { Easing, interpolate, spring } from "remotion";
import { loadFont as laddaGeist } from "@remotion/google-fonts/Geist";
import { loadFont as laddaFraunces } from "@remotion/google-fonts/Fraunces";

/**
 * Snajps formspråk ur DESIGN.md och app/globals.css: varmt papper, kall
 * bläckton, en enda ockraaccent, hårlinjer som struktur, Fraunces som
 * displaytypsnitt och Geist som brödtext. Samma OKLCH-värden som appen.
 */
export const farg = {
  ink: "oklch(0.20 0.018 252)",
  inkDjup: "oklch(0.15 0.016 252)",
  inkDov: "oklch(0.42 0.018 252)",
  inkSvag: "oklch(0.48 0.018 252)",
  paper: "oklch(0.965 0.008 88)",
  paperDov: "oklch(0.935 0.010 88)",
  ochre: "oklch(0.74 0.16 64)",
  ochreSvag: "oklch(0.74 0.16 64 / 0.22)",
  moss: "oklch(0.42 0.071 142)",
  mossLjus: "oklch(0.90 0.05 142)",
  bla: "oklch(0.48 0.12 252)",
  blaLjus: "oklch(0.90 0.04 252)",
  linje: "oklch(0.20 0.018 252 / 0.14)",
  linjeSvag: "oklch(0.20 0.018 252 / 0.08)",
  vit: "oklch(0.985 0.005 88)"
};

export const FPS = 30;
export const BREDD = 1080;
/** Scenytan: det som ryms mellan Reels övre och nedre knappfält. */
export const YTA_HOJD = 1330;

const geist = laddaGeist("normal", { weights: ["400", "500", "600", "700"], subsets: ["latin"] });
const frauncesRak = laddaFraunces("normal", { weights: ["400", "500", "600"], subsets: ["latin"] });
laddaFraunces("italic", { weights: ["400", "500"], subsets: ["latin"] });

export const sans = `${geist.fontFamily}, ui-sans-serif, system-ui, sans-serif`;
export const serif = `${frauncesRak.fontFamily}, ui-serif, Georgia, serif`;

/** Appens --ease-out: snabb start, lång mjuk landning. */
export const ut = Easing.bezier(0.16, 1, 0.3, 1);
export const inUt = Easing.bezier(0.65, 0, 0.35, 1);
export const inn = Easing.bezier(0.5, 0, 0.9, 0.4);

/** Klampad interpolation med appens easing som standard. */
export function mellan(
  frame: number,
  fran: [number, number],
  till: [number, number],
  easing: (t: number) => number = ut
): number {
  return interpolate(frame, fran, till, {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing
  });
}

/** Fjäder som landar snabbt, med liten översläng: UI-element som "poppar". */
export function pop(frame: number, fordrojning = 0, fps = FPS): number {
  return spring({
    frame: frame - fordrojning,
    fps,
    config: { damping: 14, stiffness: 170, mass: 0.7 }
  });
}

/** Fjäder utan översläng: paneler och kameror. */
export function glid(frame: number, fordrojning = 0, fps = FPS): number {
  return spring({
    frame: frame - fordrojning,
    fps,
    config: { damping: 22, stiffness: 120, mass: 0.9 }
  });
}

/**
 * Kameran: skala kring en fokuspunkt, uttryckt som en transform på scenytan.
 * Fokuspunkten står stilla när skalan ändras, så ett zoomklipp mot en knapp
 * håller knappen på plats.
 */
export type Kamerabild = { frame: number; skala: number; fokus: [number, number] };

export function kamera(frame: number, bilder: Kamerabild[]): string {
  const mitt: [number, number] = [BREDD / 2, YTA_HOJD / 2];
  const tillTrippel = (b: Kamerabild) => ({
    s: b.skala,
    tx: -(b.fokus[0] - mitt[0]) * (b.skala - 1),
    ty: -(b.fokus[1] - mitt[1]) * (b.skala - 1)
  });
  let fore = bilder[0];
  let efter = bilder[bilder.length - 1];
  for (let i = 0; i < bilder.length - 1; i += 1) {
    if (frame >= bilder[i].frame && frame <= bilder[i + 1].frame) {
      fore = bilder[i];
      efter = bilder[i + 1];
      break;
    }
  }
  if (frame < bilder[0].frame) efter = bilder[0];
  if (frame > bilder[bilder.length - 1].frame) fore = bilder[bilder.length - 1];
  const a = tillTrippel(fore);
  const b = tillTrippel(efter);
  const t = fore.frame === efter.frame ? 1 : mellan(frame, [fore.frame, efter.frame], [0, 1], inUt);
  const s = a.s + (b.s - a.s) * t;
  const tx = a.tx + (b.tx - a.tx) * t;
  const ty = a.ty + (b.ty - a.ty) * t;
  return `translate(${tx}px, ${ty}px) scale(${s})`;
}
