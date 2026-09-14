import type { Metadata } from "next";
import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";
import { sql } from "@/lib/db";

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
 */

type Utfall = "avregistrerad" | "redan_avregistrerad" | "okand_token" | "fel";

const BESKED: Record<Utfall, { rubrik: string; text: string }> = {
  avregistrerad: {
    rubrik: "Klart. Du hör inte av oss igen.",
    text:
      "Din adress är borttagen från utskicken. Det gäller omedelbart och för " +
      "alla framtida utskick från avsändaren, inte bara den här kampanjen."
  },
  redan_avregistrerad: {
    rubrik: "Du var redan avregistrerad.",
    text:
      "Adressen fanns redan i spärrlistan. Får du ändå ett mejl från oss är " +
      "det ett fel vi vill veta om — svara på mejlet så tittar vi på det."
  },
  okand_token: {
    rubrik: "Länken går inte att känna igen.",
    text:
      "Den kan ha blivit avklippt när mejlet vidarebefordrades. Svara på " +
      "mejlet du fick och skriv att du vill bli avregistrerad, så gör vi det " +
      "för hand."
  },
  fel: {
    rubrik: "Något gick fel på vår sida.",
    text:
      "Din avregistrering blev inte sparad. Svara på mejlet du fick så gör " +
      "vi det för hand — du ska inte behöva försöka igen."
  }
};

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
  const besked = utfall && utfall in BESKED ? BESKED[utfall as Utfall] : null;

  return (
    <main className="mx-auto flex min-h-screen max-w-[64ch] flex-col justify-center px-6 py-16">
      {besked ? (
        <>
          <h1 className="font-display text-[clamp(1.75rem,4vw,2.5rem)] font-semibold leading-tight tracking-[-0.02em]">
            {besked.rubrik}
          </h1>
          <p className="mt-5 text-[1.0625rem] leading-[1.7] text-ink/75">{besked.text}</p>
        </>
      ) : (
        <>
          <h1 className="font-display text-[clamp(1.75rem,4vw,2.5rem)] font-semibold leading-tight tracking-[-0.02em]">
            Vill du sluta få de här mejlen?
          </h1>
          <p className="mt-5 text-[1.0625rem] leading-[1.7] text-ink/75">
            Tryck på knappen så tas din adress bort ur utskicken. Det gäller
            omedelbart och för alla framtida utskick från avsändaren.
          </p>
          <form action={avregistrera} className="mt-9">
            <input type="hidden" name="token" value={token} />
            <button
              type="submit"
              className="focus-ring inline-flex min-h-12 items-center rounded-input bg-ink px-7 text-[1rem] font-semibold text-paper transition-colors hover:bg-ink2"
            >
              Avregistrera mig
            </button>
          </form>
        </>
      )}
    </main>
  );
}
