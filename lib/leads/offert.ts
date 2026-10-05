import { lasOffertForUtkast } from "@/lib/actions/affarskontext";

/**
 * Erbjudandetexten för ett utkast, eller ett fel med läsbart meddelande på
 * gränssnittets språk. Server actionen kastar aldrig (se affarskontext.ts):
 * ett kastat fel blev i produktion Next.js generiska "Server Components
 * render"-text i Mejlutkast-fliken.
 */
export async function offertForUtkast(): Promise<string> {
  const svar = await lasOffertForUtkast();
  if (svar.ok) return svar.text;
  const engelska = typeof document !== "undefined" && document.documentElement.lang === "en";
  throw new Error(engelska ? svar.fel.en : svar.fel.sv);
}
