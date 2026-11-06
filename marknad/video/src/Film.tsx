import React from "react";
import { AbsoluteFill, Audio, Series, staticFile } from "remotion";
import { Bakgrund } from "./delar/Bakgrund";
import { YtaKontext } from "./delar/Yta";
import { Krok, KROK_LANGD } from "./scener/Krok";
import { Korning, KORNING_LANGD } from "./scener/Korning";
import { Pang, PANG_LANGD } from "./scener/Pang";
import { Utkast, UTKAST_LANGD } from "./scener/Utkast";
import { Svar, SVAR_LANGD } from "./scener/Svar";
import { Slut, SLUT_LANGD } from "./scener/Slut";

export const SCENER = [
  { namn: "krok", langd: KROK_LANGD },
  { namn: "korning", langd: KORNING_LANGD },
  { namn: "pang", langd: PANG_LANGD },
  { namn: "utkast", langd: UTKAST_LANGD },
  { namn: "svar", langd: SVAR_LANGD },
  { namn: "slut", langd: SLUT_LANGD }
] as const;

export const FILM_LANGD = SCENER.reduce((s, x) => s + x.langd, 0);

/** Var varje scen börjar, i bildrutor. Ljudskriptet läser samma tal. */
export const SCENSTART = SCENER.reduce<Record<string, number>>((acc, s, i) => {
  acc[s.namn] = SCENER.slice(0, i).reduce((t, x) => t + x.langd, 0);
  return acc;
}, {});

export const Film: React.FC<{ hojd: number; ljud?: boolean }> = ({ hojd, ljud = true }) => {
  const topp = hojd >= 1900 ? 250 : 10;
  return (
    <YtaKontext.Provider value={{ topp, hojd }}>
      <AbsoluteFill>
        <Bakgrund />
        <Series>
          <Series.Sequence durationInFrames={KROK_LANGD}>
            <Krok />
          </Series.Sequence>
          <Series.Sequence durationInFrames={KORNING_LANGD}>
            <Korning />
          </Series.Sequence>
          <Series.Sequence durationInFrames={PANG_LANGD}>
            <Pang />
          </Series.Sequence>
          <Series.Sequence durationInFrames={UTKAST_LANGD}>
            <Utkast />
          </Series.Sequence>
          <Series.Sequence durationInFrames={SVAR_LANGD}>
            <Svar />
          </Series.Sequence>
          <Series.Sequence durationInFrames={SLUT_LANGD}>
            <Slut />
          </Series.Sequence>
        </Series>
        {ljud ? <Audio src={staticFile("ljud.wav")} /> : null}
      </AbsoluteFill>
    </YtaKontext.Provider>
  );
};
