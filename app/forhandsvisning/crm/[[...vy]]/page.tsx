import { cookies } from "next/headers";
import { CrmForhandsvisning } from "../Forhandsvisning";
import type { CrmVy } from "@/components/crm/app/CrmRam";
import { TEMA_COOKIE, parseTema } from "@/lib/tema";
import "@/lib/fonts-rubrik";

/**
 * Förhandsvisning (2026-11-25): Snajp CRM med påhittade bolag, ingen databas
 * och ingen inloggning. /forhandsvisning/crm/oversikt (start), /bolag,
 * /personer, /synk och /utvecklare. Temat följer samma cookie som resten av appen.
 */
const VYER: CrmVy[] = ["oversikt", "bolag", "personer", "synk", "utvecklare"];

export default async function Page({ params }: Readonly<{ params: Promise<{ vy?: string[] }> }>) {
  const forst = (await params).vy?.[0];
  const vy = VYER.find((v) => v === forst) ?? "oversikt";
  const tema = parseTema((await cookies()).get(TEMA_COOKIE)?.value);
  return <CrmForhandsvisning tema={tema} vy={vy} />;
}
