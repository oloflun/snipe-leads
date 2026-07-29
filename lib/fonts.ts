import { Fraunces, Geist, JetBrains_Mono } from "next/font/google";

/**
 * Loaded through next/font rather than a <link> to fonts.googleapis.com: the link
 * tag blocks render and swaps late, which is most visible on the one element that
 * carries the brand, the Fraunces italic hero.
 *
 * Declared once here and consumed as CSS variables so no component instantiates a
 * font of its own.
 */

export const fraunces = Fraunces({
  subsets: ["latin"],
  // The hero is italic; without this the browser synthesises the slant.
  style: ["normal", "italic"],
  // globals.css sets `font-variation-settings: "opsz" 144, "SOFT" 30`, so both
  // axes have to come along or those declarations do nothing.
  axes: ["SOFT", "opsz"],
  variable: "--font-fraunces",
  display: "swap"
});

export const geist = Geist({
  subsets: ["latin"],
  variable: "--font-geist",
  display: "swap"
});

export const jetbrainsMono = JetBrains_Mono({
  subsets: ["latin"],
  variable: "--font-jetbrains",
  display: "swap"
});

export const fontVariables = `${geist.variable} ${fraunces.variable} ${jetbrainsMono.variable}`;
