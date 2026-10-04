import type { Metadata } from "next";
import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";
import { sql } from "@/lib/db";
import { Avregistrering, type Utfall } from "./Avregistrering";

export const metadata: Metadata = {
  title: "Avregistrera dig från utskick",
  // Länken ligger i ett mejl till en namngiven person. Den ska inte hamna i
  // ett sökindex, och en sökmotor som följer den hade dessutom kunnat råka
  // utlösa avregistreringen om den varit ett GET-anrop — se nedan.
  robots: { index: false, follow: false }
};

/**
 * Vägen ut ur ett utskick. Den enda.
 *
 * ## Varför en knapp och inte ett rent klick
 *
 * Ett GET som skriver hade varit ett klick färre för mottagaren — och en
 * avregistrering varje gång ett e-postskydd förhandsgranskar länken. Länkar i
 * inkommande mejl klickas rutinmässigt av säkerhetsprodukter innan mottagaren
 * ser dem, och en person som INTE bad om att bli avregistrerad ska inte
 * försvinna ur listan för att hens arbetsgivare kör länkskanning.
 *
 * Bekräftelseknappen kostar ett klick och gör skrivningen avsiktlig.
 *
 * ## Varför ingen inloggning och ingen adress i URL:en
 *
 * Mottagaren har inget konto hos oss och ska inte behöva skaffa ett för att
 * slippa våra mejl. Token är ogenomskinlig — se
 * supabase/migrations/046_avregistreringslankar.sql för varför adressen inte
 * ligger i länken.
 *
 * ## Varför inlösen sker i en SQL-funktion
 *
 * `avregistrera_via_token` är security definer och den enda dörr en
 * oautentiserad besökare har in i `suppressions`. Alternativet hade varit att
 * öppna tabellen för en anonym roll, alltså riva spärren för att komma åt en
 * dörr. Se migrationen.
 *
 * Texten besökaren läser (sv + en) bor i Avregistrering.tsx: språkvalet finns
 * bara i klienten.
 */

async function avregistrera(formData: FormData): Promise<void> {
  "use server";

  const token = String(formData.get("token") ?? "");
  let utfall: Utfall = "fel";

  try {
    const rader = await sql<{ avregistrera_via_token: string }>(
      "select public.avregistrera_via_token($1) as avregistrera_via_token",
      [token]
    );
    const svar = rader[0]?.avregistrera_via_token;
    if (svar === "avregistrerad" || svar === "redan_avregistrerad" || svar === "okand_token") {
      utfall = svar;
    }
  } catch {
    // Utfallet är redan "fel". Felet loggas av pg-lagret; besökaren ska få ett
    // besked som går att agera på, inte ett stackspår.
    utfall = "fel";
  }

  revalidatePath(`/avregistrera/${token}`);
  redirect(`/avregistrera/${token}?utfall=${utfall}`);
}

export default async function Page({
  params,
  searchParams
}: Readonly<{
  params: Promise<{ token: string }>;
  searchParams: Promise<{ utfall?: string }>;
}>) {
  const { token } = await params;
  const { utfall } = await searchParams;
  return <Avregistrering utfall={utfall} token={token} action={avregistrera} />;
}
