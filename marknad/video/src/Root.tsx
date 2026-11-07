import React from "react";
import { Composition } from "remotion";
import { Film, FILM_LANGD } from "./Film";
import { FPS } from "./tema";

export const Root: React.FC = () => (
  <>
    <Composition id="Reel-9x16" component={Film} durationInFrames={FILM_LANGD} fps={FPS} width={1080} height={1920} defaultProps={{ hojd: 1920 }} />
    <Composition id="Flode-4x5" component={Film} durationInFrames={FILM_LANGD} fps={FPS} width={1080} height={1350} defaultProps={{ hojd: 1350 }} />
  </>
);
