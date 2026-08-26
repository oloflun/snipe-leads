"use server";

import { hasDatabase, sql } from "@/lib/db";

/**
 * Demobokningen — skrivvägen.
 *
 * ## `sql()` och inte `sqlAsUser()`
 *
 * Den som bokar en demo är per definition inte inloggad. Det finns ingen
 * användaridentitet att skopa på, och `sqlAsUser` hade krävt ett user_id som
 * inte existerar. Tabellens insert-policy är därför öppen med flit — se
 * migration 050 för varför det är säkert och vad som INTE är öppet.
 *
 * ## Varför den inte skickar något mejl
 *
 * Next-appen har ingen utskicksväg. Den skickar inte ens teaminbjudningar
 * (se lib/actions/team.ts, som säger det rakt ut i sitt svar till användaren).
 * Att låtsas här hade betytt en bekräftelsetext som lovar ett mejl som aldrig
 * kommer, vilket är sämre än att inte lova något: den som väntar på det hör
 * inte av sig igen.
 *
 * Bekräftelsen säger därför vad som FAKTISKT händer — förfrågan är sparad och
 * vi svarar från en människa. Vill man ha automatisk bekräftelse och
 * kalendersynk är Cal.com vägen dit; sätt NEXT_PUBLIC_CAL_LANK, så tar
 * bokningssidan den vägen i stället och det här formuläret visas inte alls.
 */

export type Bokningsresultat = { ok: boolean; fel?: string };

/** Så mycket text vi sparar per fält. Databasen har ingen längdgräns; den här
 *  finns för att en klistrad roman inte ska bli en rad på en megabyte. */
const TAK = { namn: 120, foretag: 160, epost: 254, onskad_tid: 200, meddelande: 2000 };

function putsa(varde: FormDataEntryValue | null, tak: number): string {
  return typeof varde === "string" ? varde.trim().slice(0, tak) : "";
}

/**
 * En e-postadress som duger att svara på.
 *
 * Medvetet tillåtande: den fångar uppenbara stavfel ("anna@" utan domän) och
 * inget mer. En strikt RFC-regex avvisar giltiga adresser, och priset för ett
 * falskt avslag här är en förlorad kund — priset för en felstavad adress som
 * släpps igenom är ett svarsmejl som studsar.
 */
function seUtSomEpost(varde: string): boolean {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(varde);
}

export async function bokaDemo(form: FormData): Promise<Bokningsresultat> {
  const namn = putsa(form.get("namn"), TAK.namn);
  const foretag = putsa(form.get("foretag"), TAK.foretag);
  const epost = putsa(form.get("epost"), TAK.epost);
  const onskadTid = putsa(form.get("onskad_tid"), TAK.onskad_tid);
  const meddelande = putsa(form.get("meddelande"), TAK.meddelande);
  const kalla = putsa(form.get("kalla"), 120) || "/boka-demo";

  // Honungsfällan: ett fält som är dolt för människor. Fylls det i är det en
  // robot, och vi svarar med ok utan att spara. Att svara med ett fel hade
  // lärt roboten vilket fält som avslöjade den.
  if (putsa(form.get("webbplats"), 200)) return { ok: true };

  if (!namn) return { ok: false, fel: "Fyll i ditt namn." };
  if (!epost) return { ok: false, fel: "Fyll i din e-postadress." };
  if (!seUtSomEpost(epost)) {
    return { ok: false, fel: "E-postadressen ser inte ut att stämma. Kontrollera den gärna." };
  }

  if (!hasDatabase()) {
    // Ärligt fel i stället för en tyst framgång. En bokning som inte sparades
    // och sa "tack" är den värsta varianten: kunden väntar, vi vet ingenting.
    return {
      ok: false,
      fel: "Vi kan inte ta emot bokningen just nu. Mejla oss så återkommer vi."
    };
  }

  try {
    // Inget `returning`. Tabellen har ingen select-policy för webbrollen med
    // flit, och RETURNING hade krävt en. Se migration 050.
    await sql(
      `insert into public.demo_requests (namn, foretag, epost, onskad_tid, meddelande, kalla)
       values ($1, $2, $3, $4, $5, $6)`,
      [namn, foretag || null, epost, onskadTid || null, meddelande || null, kalla]
    );
    return { ok: true };
  } catch (orsak) {
    // Orsaken loggas serverside; besökaren får inte se ett SQL-fel. Men de får
    // en väg vidare, för deras ärende är fortfarande giltigt.
    console.error("bokaDemo: kunde inte spara förfrågan", orsak);
    return {
      ok: false,
      fel: "Något gick fel när vi skulle spara förfrågan. Mejla oss så tar vi det den vägen."
    };
  }
}
