import React from "react";
import { farg, sans } from "../tema";

/** Pappersvit panel med appens hörnradie och en mjuk, bred skugga mot bläcket. */
export const Panel: React.FC<{
  x: number;
  y: number;
  bredd: number;
  hojd: number;
  style?: React.CSSProperties;
  children?: React.ReactNode;
}> = ({ x, y, bredd, hojd, style, children }) => (
  <div
    style={{
      position: "absolute",
      left: x,
      top: y,
      width: bredd,
      height: hojd,
      background: farg.paper,
      borderRadius: 36,
      boxShadow: "0 40px 90px oklch(0.10 0.016 252 / 0.55), 0 2px 0 oklch(1 0 0 / 0.35) inset",
      color: farg.ink,
      fontFamily: sans,
      overflow: "hidden",
      ...style
    }}
  >
    {children}
  </div>
);

export const Knapp: React.FC<{
  x: number;
  y: number;
  bredd: number;
  hojd?: number;
  text: string;
  ton?: "ink" | "ochre" | "moss" | "paper";
  skala?: number;
  style?: React.CSSProperties;
}> = ({ x, y, bredd, hojd = 92, text, ton = "ink", skala = 1, style }) => {
  const bakgrund = { ink: farg.ink, ochre: farg.ochre, moss: farg.moss, paper: farg.paperDov }[ton];
  const fargText = ton === "ochre" || ton === "paper" ? farg.ink : farg.paper;
  return (
    <div
      style={{
        position: "absolute",
        left: x,
        top: y,
        width: bredd,
        height: hojd,
        borderRadius: 18,
        background: bakgrund,
        color: fargText,
        fontFamily: sans,
        fontWeight: 600,
        fontSize: Math.round(hojd * 0.4),
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        transform: `scale(${skala})`,
        ...style
      }}
    >
      {text}
    </div>
  );
};

export const Falt: React.FC<{
  x: number;
  y: number;
  bredd: number;
  etikett: string;
  varde: string;
  aktiv?: boolean;
  markor?: boolean;
  platshallare?: string;
}> = ({ x, y, bredd, etikett, varde, aktiv = false, markor = false, platshallare = "" }) => (
  <div style={{ position: "absolute", left: x, top: y, width: bredd }}>
    <div style={{ fontSize: 28, fontWeight: 500, color: farg.inkDov, marginBottom: 12 }}>{etikett}</div>
    <div
      style={{
        height: 92,
        borderRadius: 14,
        border: `2px solid ${aktiv ? farg.ochre : farg.linje}`,
        boxShadow: aktiv ? `0 0 0 5px ${farg.ochreSvag}` : "none",
        background: farg.vit,
        display: "flex",
        alignItems: "center",
        padding: "0 26px",
        fontSize: 36,
        fontWeight: 500,
        color: varde ? farg.ink : farg.inkSvag,
        whiteSpace: "pre"
      }}
    >
      {varde || platshallare}
      {markor ? <span style={{ width: 3, height: 44, background: farg.ink, marginLeft: 2 }} /> : null}
    </div>
  </div>
);
