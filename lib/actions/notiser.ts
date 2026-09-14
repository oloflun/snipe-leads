"use server";

import { hasDatabase, sqlAsUser } from "@/lib/db";
import { STANDARD, tillHandelser, type Notisinstallningar } from "@/lib/notiser";
import { getWorkspaceContext } from "@/lib/workspace";

/**
 * Mejlnotiser — skrivvägen.
 *
 * Raden bor i `notification_preferences` (migration 043), en rad per
 * ANVÄNDARE. Motivet står i migrationen: ett notismejl går till en person, och
 * en inställning per arbetsyta hade låtit den ena kollegan tysta den andra.
 *
 * Typerna och standardvärdena ligger i lib/notiser.ts och inte här. Skälet är
 * mekaniskt och står i den filen: en `"use server"`-modul får bara exportera
 * asynkrona funktioner.
 */

export type NotisResultat = { success: boolean; error?: string };

type Rad = { email_enabled: boolean; events: string[] };

/**
 * Kundens rad, eller standarden om hen aldrig svarat.
 *
 * `null` betyder något helt annat än "inga notiser": ingen session eller ingen
 * databas. Anroparen måste skilja på de två — se NotisSettings.
 */
export async function hamtaNotiser(): Promise<Notisinstallningar | null> {
  if (!hasDatabase()) return null;

  const context = await getWorkspaceContext();
  if (!context) return null;

  const rader = await sqlAsUser<Rad>(
    context.user.id,
    "select email_enabled, events from public.notification_preferences where user_id = $1",
    [context.user.id]
  );

  const rad = rader[0];
  // Ingen rad = aldrig svarat. Då gäller standarden, och den är PÅ — samma
  // värde databasen skulle ge om raden skapades just nu.
  if (!rad) return { ...STANDARD, handelser: [...STANDARD.handelser] };

  return { epost: rad.email_enabled, handelser: tillHandelser(rad.events) };
}

export async function sparaNotiser(input: Notisinstallningar): Promise<NotisResultat> {
  const context = await getWorkspaceContext();
  if (!context) {
    return { success: false, error: "Du måste vara inloggad." };
  }

  const handelser = tillHandelser(input.handelser);

  // Ett medvetet "på men inget valt" finns inte. Slår kunden av båda rutorna
  // är svaret på huvudfrågan nej, och att spara `epost: true` med en tom lista
  // hade gett en växel som står på PÅ medan ingenting någonsin skickas.
  const epost = input.epost && handelser.length > 0;

  try {
    await sqlAsUser(
      context.user.id,
      `insert into public.notification_preferences (user_id, email_enabled, events, updated_at)
            values ($1, $2, $3::text[], now())
       on conflict (user_id)
       do update set email_enabled = excluded.email_enabled,
                     events        = excluded.events,
                     updated_at    = now()`,
      [context.user.id, epost, handelser]
    );
  } catch (error) {
    return { success: false, error: (error as Error).message };
  }

  return { success: true };
}

/**
 * Svaret från rutan i onboardingen.
 *
 * Egen funktion och inte `sparaNotiser`, av ett skäl som syns i signaturen:
 * här finns bara ett ja eller nej, inte ett urval. Ett nej skriver en rad med
 * `email_enabled = false` men BEHÅLLER händelselistan, så att den som ångrar
 * sig i inställningarna får tillbaka båda notistyperna i stället för att mötas
 * av en påslagen växel som inte skickar något.
 *
 * Utan rad gäller standarden, alltså notiser PÅ. Det är därför bara ett NEJ som
 * verkligen måste nå fram — ett ja som faller ger samma utfall som ett ja som
 * sparas. Anroparen loggar felet i stället för att fälla onboardingen, samma
 * regel som kontextdokumentet i actions/affarskontext.ts.
 */
export async function sparaNotissvarViaOnboarding(godkant: boolean): Promise<NotisResultat> {
  return sparaNotiser({ epost: godkant, handelser: [...STANDARD.handelser] });
}
