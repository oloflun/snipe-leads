"use server";

import { hasDatabase, sqlAsUser } from "@/lib/db";
import { NEKAT_TESTKORT, TESTKORT, type Betalsatt, type Kortuppgifter } from "@/lib/betalning";
import { aktivVy } from "@/lib/vy";
import { getWorkspaceContext } from "@/lib/workspace";

/**
 * Betalsättet — metadata om ett kort, aldrig kortet.
 *
 * ## Vad som kommer hit, och vad som aldrig gör det
 *
 * Klienten skickar märke, fyra sista och giltighetstid. Kortnumret och CVC
 * lämnar aldrig webbläsaren; de valideras där mot listan av kända testkort och
 * kastas sedan. Se lib/betalning.ts för varför det är formen och inte en
 * genväg.
 *
 * Servern litar ändå inte på klienten: `last4` måste tillhöra ett av testkorten
 * i listan. En anropare som skickar fyra egna siffror avvisas — annars vore
 * klientvalideringen den enda spärren, och klientkod går att kringgå.
 *
 * ## Varför "simulerad" står i provider-kolumnen
 *
 * Det finns ingen betalväxel inkopplad. Raden är alltså ett SPARAT VAL, inte
 * ett betalningsmedel: ingenting kan debiteras, och `is_test` är sant. Den
 * dagen skarpa nycklar finns byts den här funktionens innanmäte mot ett anrop
 * till växeln — signaturen och tabellen håller redan.
 */

export type BetalsattResultat = { success: boolean; error?: string; betalsatt?: Betalsatt };

type Rad = {
  brand: string;
  last4: string;
  exp_month: number;
  exp_year: number;
  is_test: boolean;
  provider: string;
};

export async function hamtaBetalsatt(): Promise<Betalsatt | null> {
  if (!hasDatabase()) return null;

  const context = await getWorkspaceContext();
  if (!context) return null;

  // Demo OCH kundbesök läser arbetsytan bakom vyn — alltså VÅR, inte den
  // besökta kundens (`business_contexts` hade samma fälla, se lib/actions/
  // affarskontext.ts, hittad i produktion 2026-09-02). Ett kort där hör inte
  // hemma i en vy vi visar för utomstående eller i ett kundbesök.
  if ((await aktivVy()).vy !== "admin") return null;

  const rader = await sqlAsUser<Rad>(
    context.user.id,
    `select brand, last4, exp_month, exp_year, is_test, provider
       from public.billing_payment_methods
      where workspace_id = $1`,
    [context.workspace.id]
  );

  return rader[0] ?? null;
}

export async function sparaBetalsatt(input: Kortuppgifter): Promise<BetalsattResultat> {
  const context = await getWorkspaceContext();
  if (!context) {
    return { success: false, error: "Du måste vara inloggad." };
  }

  if ((await aktivVy()).vy !== "admin") {
    return {
      success: false,
      error:
        "Betalsätt går inte att spara i demo- eller kundvy — arbetsytan bakom vyn är vår egen, inte kundens."
    };
  }

  // Serversidans spärr. Klienten kontrollerar redan, men klientkod går att
  // kringgå och den här raden är den som skyddar: bara testkortens fyra sista
  // accepteras, alltså kan ingen riktig kortsvans hamna i tabellen.
  const kort = TESTKORT.find(
    (k) => k.nummer.slice(-4) === input.last4 && k.marke === input.brand
  );
  if (!kort) {
    return {
      success: false,
      error: "Bara testkort tas emot. Riktiga kortuppgifter ska inte skrivas in här."
    };
  }

  // Det nekade testkortet finns för att felvägen ska gå att prova. Utan det är
  // den enda vägen genom flödet den som lyckas, och en betalningsvy som aldrig
  // visat sitt felläge är en vy vars felläge ingen sett.
  if (input.simuleraNekat || kort.nummer === NEKAT_TESTKORT) {
    return {
      success: false,
      error: "Kortet nekades av banken (simulerat). Prova ett annat kort eller hör av er till er bank."
    };
  }

  if (
    !Number.isInteger(input.exp_month) ||
    input.exp_month < 1 ||
    input.exp_month > 12 ||
    !Number.isInteger(input.exp_year) ||
    input.exp_year < 2020 ||
    input.exp_year > 2100
  ) {
    return { success: false, error: "Giltighetstiden ser inte rätt ut." };
  }

  const rad: Betalsatt = {
    brand: kort.marke,
    last4: kort.nummer.slice(-4),
    exp_month: input.exp_month,
    exp_year: input.exp_year,
    // Hårdkodat, inte inskickat. Det här ÄR ett testkort och raden får aldrig
    // kunna påstå något annat om sig själv.
    is_test: true,
    provider: "simulerad"
  };

  try {
    await sqlAsUser(
      context.user.id,
      `insert into public.billing_payment_methods
              (workspace_id, provider, brand, last4, exp_month, exp_year, is_test)
       values ($1, $2, $3, $4, $5, $6, true)
       on conflict (workspace_id)
       do update set provider   = excluded.provider,
                     brand      = excluded.brand,
                     last4      = excluded.last4,
                     exp_month  = excluded.exp_month,
                     exp_year   = excluded.exp_year,
                     is_test    = true,
                     created_at = now()`,
      [context.workspace.id, rad.provider, rad.brand, rad.last4, rad.exp_month, rad.exp_year]
    );
  } catch (error) {
    return { success: false, error: (error as Error).message };
  }

  return { success: true, betalsatt: rad };
}

export async function taBortBetalsatt(): Promise<BetalsattResultat> {
  const context = await getWorkspaceContext();
  if (!context) {
    return { success: false, error: "Du måste vara inloggad." };
  }

  if ((await aktivVy()).vy !== "admin") {
    return { success: false, error: "Går inte att ändra i demo- eller kundvy." };
  }

  try {
    await sqlAsUser(
      context.user.id,
      "delete from public.billing_payment_methods where workspace_id = $1",
      [context.workspace.id]
    );
  } catch (error) {
    return { success: false, error: (error as Error).message };
  }

  return { success: true };
}
