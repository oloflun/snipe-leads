import { loadFont } from "@remotion/fonts";
import { linearTiming, TransitionSeries } from "@remotion/transitions";
import { fade } from "@remotion/transitions/fade";
import type { TransitionPresentation, TransitionPresentationComponentProps } from "@remotion/transitions";
import React from "react";
import { AbsoluteFill, Easing, Img, interpolate, OffthreadVideo, staticFile, useCurrentFrame } from "remotion";

// Click-through film of Snajp. Same engine as the WMS film (on Anton's machine: D:/wms-presentation/video/src/Film.tsx):
// one sharp frame per step, a camera that pushes in, a cursor that travels and clicks, one caption.
// The look is Snajp's own (DESIGN.md § Theme, § Typography): paper, ink, one ochre accent, Fraunces + Geist.
const T = { paper: "#f6f3ed", ink: "#10171e", ochre: "#ef911d", inkMuted: "#464e57", paperMuted: "#a7a49f" };
loadFont({ family: "Geist", url: staticFile("fonts/geist.woff2"), weight: "100 900" });
loadFont({ family: "Fraunces", url: staticFile("fonts/fraunces.woff2"), weight: "100 900" });

type Pt = { x: number; y: number };
export type Shot = {
  kind: "desktop";
  file: string;
  w: number;
  h: number;
  caption: string;
  cursor?: Pt | null;
  click?: boolean;
  /** Length in bars of the music bed. */
  bars: number;
  zoom?: number;
  /** Frame the middle of the page (a text page without the app's rail), following the target vertically. */
  center?: boolean;
  /** Land on the right edge: the lead drawer opens from the right. */
  anchor?: "right";
  /** A fixed point for the camera to settle on, in frame pixels, instead of following the target. */
  focus?: Pt;
};
export type Title = { kind: "title"; text: string; sub?: string; lines?: string[]; bars: number; invert?: boolean };
/** A finished film played whole (the Instagram reel), fitted to the frame's height so nothing is cropped. */
export type Clip = { kind: "clip"; file: string; frames: number; w: number; h: number };
export type Item = Shot | Title | Clip;

export const FADE = 20;
// The bed is 110 BPM, four beats to the bar, and its first beat falls 0.56 s in (brag-plan.md). The bed
// starts where the reel hands over, and from there the middle of every cross-fade sits on a downbeat.
const BAR = (60 / 110) * 4 * 30;
const BEAT0 = 17;
/** Where each item starts and how long it runs, in frames. Neighbours overlap by FADE. */
export function layout(items: Item[]) {
  const starts: number[] = [];
  let origin = 0; // where the bed starts
  let bars = 0;
  let t = 0;
  items.forEach((it) => {
    if (it.kind === "clip") {
      starts.push(t);
      t += it.frames - FADE;
      origin = t;
      bars = 0;
      return;
    }
    starts.push(bars === 0 ? origin : origin + Math.round(BEAT0 - FADE / 2 + bars * BAR));
    bars += it.bars;
    t = origin + Math.round(BEAT0 - FADE / 2 + bars * BAR);
  });
  const durs = items.map((it, i) => (i < items.length - 1 ? starts[i + 1] - starts[i] + FADE : it.kind === "clip" ? it.frames : t - starts[i] + FADE));
  return { starts, durs, origin, total: starts[items.length - 1] + durs[items.length - 1] };
}
export const filmDuration = (items: Item[]) => layout(items).total;

const ease = Easing.bezier(0.16, 1, 0.3, 1);
const glide = Easing.bezier(0.45, 0, 0.2, 1);
const clamp = { extrapolateLeft: "clamp", extrapolateRight: "clamp" } as const;
const SIDEBAR = 390; // the rail: 260 css px at 1.5x
const Z_DESK = 1.25; // the content area right of the rail just fills the frame
const PUSH = [20, 84];
const MOVE = [38, 84];
const CLICK = 92;

const Cursor: React.FC<{ from: Pt; to: Pt; click: boolean }> = ({ from, to, click }) => {
  const f = useCurrentFrame();
  const x = interpolate(f, MOVE, [from.x, to.x], { ...clamp, easing: ease });
  const y = interpolate(f, MOVE, [from.y, to.y], { ...clamp, easing: ease });
  const press = click ? interpolate(f, [CLICK - 5, CLICK, CLICK + 8], [1, 0.86, 1], clamp) : 1;
  const ring = interpolate(f, [CLICK - 2, CLICK + 28], [0, 1], { ...clamp, easing: ease });
  const show = interpolate(f, [MOVE[0] - 14, MOVE[0]], [0, 1], clamp);
  return (
    <>
      {click && (
        <div
          style={{
            position: "absolute",
            left: to.x - 44,
            top: to.y - 44,
            width: 88,
            height: 88,
            borderRadius: 44,
            border: `5px solid ${T.ochre}`,
            opacity: f < CLICK - 2 ? 0 : 0.9 * (1 - ring),
            scale: 0.35 + ring * 0.85,
          }}
        />
      )}
      <svg width={44} height={58} viewBox="0 0 22 29" style={{ position: "absolute", left: x - 3, top: y - 3, scale: press, transformOrigin: "3px 2px", opacity: show }}>
        <path d="M1.5 1.5 L1.5 22.5 L7 17.5 L10.8 26.5 L14.6 24.9 L10.9 16.2 L18.5 16.2 Z" fill={T.ink} stroke={T.paper} strokeWidth={1.6} strokeLinejoin="round" />
      </svg>
    </>
  );
};

// The caption floats free under the picture, with no plate (Anton 2026-11-25): the screenshot dissolves
// into the page's own paper colour at the bottom, and the text stands on that. It rises in softly, and
// leaves with the cross-fade of its scene, so one caption melts into the next.
const BAND = 168;
const FEATHER = 96;
const VIEW_H = 1080 - BAND;
const Caption: React.FC<{ text: string; dur: number }> = ({ text, dur }) => {
  const f = useCurrentFrame();
  // One caption at a time: the old one is gone before the scenes cross-fade, and the new one comes in
  // once the new picture is there. Two captions on top of each other were unreadable for half a second.
  const tIn = [FADE - 8, FADE + 14];
  const tOut = [dur - FADE - 13, dur - FADE];
  const o = Math.min(interpolate(f, tIn, [0, 1], { ...clamp, easing: ease }), interpolate(f, tOut, [1, 0], { ...clamp, easing: glide }));
  const dy = interpolate(f, tIn, [14, 0], { ...clamp, easing: ease }) + interpolate(f, tOut, [0, -10], { ...clamp, easing: glide });
  const blur = interpolate(f, tIn, [6, 0], clamp) + interpolate(f, tOut, [0, 4], clamp);
  return (
    <>
      <div style={{ position: "absolute", left: 0, right: 0, top: VIEW_H - FEATHER, height: FEATHER, background: "linear-gradient(to bottom, rgba(246, 243, 237, 0), rgba(246, 243, 237, 1))" }} />
      <div style={{ position: "absolute", left: 0, right: 0, bottom: 0, height: BAND, background: T.paper, display: "flex", alignItems: "center", padding: "0 72px 14px" }}>
        <p style={{ margin: 0, fontFamily: "Geist", fontSize: 60, fontWeight: 560, lineHeight: 1.1, letterSpacing: -1.3, color: T.ink, opacity: o, translate: `0px ${dy}px`, filter: blur > 0.05 ? `blur(${blur}px)` : undefined }}>{text}</p>
      </div>
    </>
  );
};

function camera(s: Shot, focus: Pt, f: number, dur: number) {
  const push = interpolate(f, PUSH, [0, 1], { ...clamp, easing: glide });
  // The slow drift stops where the cross-fade begins, so nothing moves under a transition.
  const drift = interpolate(f, [PUSH[1], dur - FADE], [0, 1], { ...clamp, easing: Easing.out(Easing.quad) });
  const z = 1 + ((s.zoom ?? Z_DESK) - 1) * push + 0.025 * drift;
  const c = (v: number, lo: number) => Math.min(0, Math.max(lo, v));
  return { z, tx: c(960 - focus.x * z, 1920 - 1920 * z), ty: c(VIEW_H / 2 - focus.y * z, VIEW_H - 1080 * z) };
}

const ShotScene: React.FC<{ s: Shot; prev: Item | null; dur: number }> = ({ s, prev, dur }) => {
  const f = useCurrentFrame();
  const k = 1920 / s.w;
  const to = s.cursor ? { x: s.cursor.x * k, y: s.cursor.y * k } : null;
  const zEnd = s.zoom ?? Z_DESK;
  const focus = s.focus ?? {
    x: s.center ? 960 : s.anchor === "right" ? 1920 : to && to.x < SIDEBAR ? to.x : SIDEBAR + 960 / zEnd,
    // Top-anchored, so the page header is never cut, unless the target would end up low in the picture.
    y: s.center && to ? to.y : !to || to.y * zEnd <= VIEW_H - 170 ? 0 : (to.y + VIEW_H / 2) / 2,
  };
  const { z, tx, ty } = camera(s, focus, f, dur);
  const screen = (pt: Pt) => ({ x: tx + pt.x * z, y: ty + pt.y * z });
  // The cursor continues from where it was on the previous step.
  let from: Pt = { x: 1500, y: 1180 };
  if (prev && prev.kind === "desktop" && prev.cursor) from = screen({ x: prev.cursor.x * k, y: prev.cursor.y * k });
  return (
    <AbsoluteFill style={{ background: T.paper }}>
      <div style={{ position: "absolute", left: 0, top: 0, width: 1920, height: VIEW_H, overflow: "hidden" }}>
        <div style={{ position: "absolute", left: 0, top: 0, width: 1920, height: 1080, translate: `${tx}px ${ty}px`, scale: z, transformOrigin: "0px 0px" }}>
          <Img src={staticFile(`film/${s.file}`)} style={{ width: 1920, height: 1080 }} />
        </div>
        {to && <Cursor from={from} to={screen(to)} click={!!s.click} />}
      </div>
      <Caption text={s.caption} dur={dur} />
    </AbsoluteFill>
  );
};

const TitleScene: React.FC<{ t: Title }> = ({ t }) => {
  const f = useCurrentFrame();
  const o = interpolate(f, [8, 34], [0, 1], { ...clamp, easing: ease });
  const dy = interpolate(f, [8, 34], [18, 0], { ...clamp, easing: ease });
  const fg = t.invert ? T.paper : T.ink;
  const os = interpolate(f, [26, 52], [0, 1], { ...clamp, easing: ease });
  return (
    <AbsoluteFill style={{ background: t.invert ? T.ink : T.paper, justifyContent: "center", padding: "0 200px" }}>
      <p style={{ margin: 0, fontFamily: "Fraunces", fontSize: t.lines ? 76 : 100, fontWeight: 600, lineHeight: 1.06, letterSpacing: -2, color: fg, opacity: o, translate: `0px ${dy}px`, textWrap: "balance", maxWidth: 1400 }}>{t.text}</p>
      {t.sub && (
        <p style={{ margin: "34px 0 0", fontFamily: "Geist", fontSize: 50, fontWeight: 450, lineHeight: 1.2, letterSpacing: -0.6, color: t.invert ? T.ochre : T.inkMuted, opacity: os }}>{t.sub}</p>
      )}
      {t.lines && (
        <div style={{ marginTop: 60, display: "flex", flexDirection: "column", gap: 28 }}>
          {t.lines.map((l, i) => {
            const a = 34 + i * 26;
            return (
              <div key={l} style={{ display: "flex", alignItems: "baseline", gap: 26, opacity: interpolate(f, [a, a + 24], [0, 1], clamp), translate: `0px ${interpolate(f, [a, a + 24], [14, 0], { ...clamp, easing: ease })}px` }}>
                <span style={{ width: 14, height: 14, borderRadius: 7, background: T.ochre, flex: "none", translate: "0px -6px" }} />
                <span style={{ fontFamily: "Geist", fontSize: 46, fontWeight: 480, lineHeight: 1.2, letterSpacing: -0.4, color: fg, textWrap: "balance" }}>{l}</span>
              </div>
            );
          })}
        </div>
      )}
    </AbsoluteFill>
  );
};

// Into and out of a title card: dip through the paper colour with a solid overlay whose colour carries the
// alpha. CSS opacity on a whole scene made Chrome redraw text a little bolder on some frames of the fade.
const DipPresentation: React.FC<TransitionPresentationComponentProps<Record<string, never>>> = ({ children, presentationDirection, presentationProgress: p }) => {
  const entering = presentationDirection === "entering";
  const alpha = entering ? Math.min(1, Math.max(0, 2 - 2 * p)) : Math.min(1, 2 * p);
  return (
    <AbsoluteFill style={{ visibility: entering && p < 0.5 ? "hidden" : "visible" }}>
      {children}
      <AbsoluteFill style={{ background: `rgba(246, 243, 237, ${alpha})` }} />
    </AbsoluteFill>
  );
};
const dip = (): TransitionPresentation<Record<string, never>> => ({ component: DipPresentation, props: {} });

// The reel is 4:5 and the film 16:9: it plays at the frame's full height, in the middle, on the same paper
// colour as its own ground, so the whole picture shows. Its sound is laid on afterwards with ffmpeg.
// The sides continue the reel's own ground: the outermost columns of the picture are stretched out to the
// frame's edges, so a dark scene has dark sides and the paper end card has paper sides, with the reel's
// own vertical light. (A blurred enlargement behind it pulled panels and the logo into the sides.)
const ClipScene: React.FC<{ c: Clip }> = ({ c }) => {
  const w = (c.w * 1080) / c.h;
  const side = (1920 - w) / 2;
  const stretch = (side + 2) / 6; // six columns of the picture cover one side
  const edge = (at: "left" | "right") => (
    <div style={{ position: "absolute", top: 0, [at]: 0, width: side + 2, height: 1080, overflow: "hidden" }}>
      <OffthreadVideo src={staticFile(c.file)} muted style={{ position: "absolute", top: 0, [at]: 0, height: 1080, width: w, scale: `${stretch} 1`, transformOrigin: `${at} center` }} />
    </div>
  );
  return (
    <AbsoluteFill style={{ background: T.ink }}>
      {edge("left")}
      {edge("right")}
      <OffthreadVideo src={staticFile(c.file)} muted style={{ position: "absolute", top: 0, left: side, height: 1080, width: w }} />
    </AbsoluteFill>
  );
};

export const Film: React.FC<{ items: Item[] }> = ({ items }) => {
  const { durs } = layout(items);
  return (
    <AbsoluteFill style={{ background: T.paper }}>
      <TransitionSeries>
        {items.flatMap((it, i) => {
          const d = durs[i];
          const seq = (
            <TransitionSeries.Sequence key={`s-${i}`} durationInFrames={d}>
              {it.kind === "clip" ? <ClipScene c={it} /> : it.kind === "title" ? <TitleScene t={it} /> : <ShotScene s={it} prev={items[i - 1] ?? null} dur={d} />}
            </TransitionSeries.Sequence>
          );
          const hard = it.kind !== "desktop" || items[i - 1]?.kind !== "desktop";
          const timing = linearTiming({ durationInFrames: FADE });
          const cut = hard ? <TransitionSeries.Transition key={`t-${i}`} presentation={dip()} timing={timing} /> : <TransitionSeries.Transition key={`t-${i}`} presentation={fade()} timing={timing} />;
          return i === 0 ? [seq] : [cut, seq];
        })}
      </TransitionSeries>
    </AbsoluteFill>
  );
};
