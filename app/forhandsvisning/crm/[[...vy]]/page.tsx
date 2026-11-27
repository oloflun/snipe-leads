import { cookies } from "next/headers";
import { CrmForhandsvisning } from "../Forhandsvisning";
import type { CrmVy } from "@/components/crm/app/CrmRam";
import { TEMA_COOKIE, parseTema } from "@/lib/tema";
import "@/lib/fonts-rubrik";

/**
 * Förhandsvisning (2026-11-25): Snajp CRM med påhittade bolag, ingen databas
 * och ingen inloggning. /forhandsvisning/crm/oversikt (start), /bolag,
 * /personer, /affarer, /synk, /sparrar och /utvecklare. Temat följer samma cookie som resten av appen.
 */
const VYER: CrmVy[] = ["oversikt", "bolag", "personer", "affarer", "synk", "sparrar", "utvecklare"];

export default async function Page({
  params,
  searchParams
}: Readonly<{ params: Promise<{ vy?: string[] }>; searchParams: Promise<Record<string, string | string[] | undefined>> }>) {
  const forst = (await params).vy?.[0];
  const vy = VYER.find((v) => v === forst) ?? "oversikt";
  const tema = parseTema((await cookies()).get(TEMA_COOKIE)?.value);
  // ?vy=kund: kundens nivå (annars plattformsadmin). ?tillagg=saknas: arbetsytan saknar tillägget.
  const fraga = await searchParams;
  return <CrmForhandsvisning tema={tema} vy={vy} kund={fraga.vy === "kund"} utanTillagg={fraga.tillagg === "saknas"} />;
}
