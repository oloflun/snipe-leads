import { cookies } from "next/headers";
import { CrmForhandsvisning } from "../Forhandsvisning";
import { TEMA_COOKIE, parseTema } from "@/lib/tema";
import "@/lib/fonts-rubrik";

/**
 * Förhandsvisning (2026-11-25): Snajp CRM med påhittade bolag, ingen databas
 * och ingen inloggning. /forhandsvisning/crm/oversikt (start), /bolag,
 * /personer, /affarer, /uppgifter, /synk, /sparrar och /utvecklare. Vägar i flera
 * led (`iris/leads`) går vidare hela, så att vyer under en grupp går att visa.
 * Temat följer samma cookie som resten av appen.
 *
 * Lägen i adressen: `?vy=kund` (kundens nivå), `?besok=1` (kundbesök),
 * `?roll=lasare` (läsroll), `?demo=1` (adminens demovy), `?demo=yta`
 * (demoarbetsyta), `?produkter=support` (arbetsytans produkter) och
 * `?tillagg=saknas` (arbetsytan saknar tillägget).
 */
export default async function Page({
  params,
  searchParams
}: Readonly<{ params: Promise<{ vy?: string[] }>; searchParams: Promise<Record<string, string | string[] | undefined>> }>) {
  const vy = ((await params).vy ?? []).map((d) => decodeURIComponent(d)).join("/") || "oversikt";
  const tema = parseTema((await cookies()).get(TEMA_COOKIE)?.value);
  const fraga = await searchParams;
  const ett = (nyckel: string) => {
    const v = fraga[nyckel];
    return Array.isArray(v) ? v[0] : v;
  };
  const produkter = ett("produkter");
  return (
    <CrmForhandsvisning
      tema={tema}
      vy={vy}
      utanTillagg={ett("tillagg") === "saknas"}
      lagen={{
        kund: ett("vy") === "kund",
        besok: ett("besok") === "1",
        lasare: ett("roll") === "lasare",
        demo: ett("demo") === "1" ? "vy" : ett("demo") === "yta" ? "yta" : null,
        produkter: produkter != null ? produkter.split(",").filter(Boolean) : null
      }}
    />
  );
}
