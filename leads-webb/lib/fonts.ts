import { Fraunces, Geist, JetBrains_Mono } from "next/font/google";

/**
 * Samma tre snitt som huvudappen, laddade via next/font så att inget
 * <link> mot fonts.googleapis.com blockerar renderingen.
 */

export const fraunces = Fraunces({
  subsets: ["latin"],
  style: ["normal", "italic"],
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
