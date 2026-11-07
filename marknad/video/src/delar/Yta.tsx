import React, { createContext, useContext } from "react";
import { BREDD, YTA_HOJD } from "../tema";

/**
 * Scenytan: 1080×1330 som ligger innanför Instagrams knappfält. I 9:16
 * börjar den 250 px ner (Reels övre fält), i 4:5 nästan i kant. Allt som
 * ska läsas ritas i ytan; bara bakgrund och ljuseffekter får gå utanför.
 */
export const YtaKontext = createContext<{ topp: number; hojd: number }>({ topp: 250, hojd: 1920 });

export const Yta: React.FC<{ children: React.ReactNode; style?: React.CSSProperties }> = ({ children, style }) => {
  const { topp } = useContext(YtaKontext);
  return (
    <div
      style={{
        position: "absolute",
        left: 0,
        top: topp,
        width: BREDD,
        height: YTA_HOJD,
        overflow: "visible",
        ...style
      }}
    >
      {children}
    </div>
  );
};

export function useYta() {
  return useContext(YtaKontext);
}
