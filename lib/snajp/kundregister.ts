import "server-only";

import { proxyWithApiKey } from "@/app/api/snajp-support/_lib";
import { readJsonBody } from "@/lib/http/json";

/**
 * Onboardingens skrivning till kundregistret (ss_customer_details +
 * ss_customer_contacts) — så att orgnr och kontaktperson landar där vi
 * faktiskt letar när vi ska nå kunden: Admin → Kunder → Data.
 *
 * ## Varför master-nyckeln, och varför det är okej just här
 *
 * Kundregistret är admin-ytans manuella lager och nås bara bakom
 * `require_master_key` (migration 053) — det finns ingen tenant-scopad
 * skrivväg, med flit. Det här är den ENDA icke-adminplats som använder
 * nyckeln, och den skriver uteslutande till DEN tenant som just skapades åt
 * den inloggade i samma serveranrop (sluggen kommer ur provisioneringen,
 * aldrig ur klienten). Lanseringshandoffen 2026-09-20 beställer exakt detta:
 * "För kundtenants: fyll kundregistret vid onboarding."
 *
 * ## Fail-soft
 *
 * Varje fel loggas och sväljs. Kunden har just fyllt i sitt bolag; att
 * skicka tillbaka dem till formuläret för att en CRM-rad inte gick att
 * skriva vore att straffa dem för fel sak. En saknad rad syns i admin och
 * går att fylla för hand — en avbruten onboarding syns som en tappad kund.
 */
export async function registreraKunduppgifter(
  slug: string,
  uppgifter: {
    orgnr?: string | null;
    kontakt?: {
      namn: string;
      roll?: string | null;
      mejl?: string | null;
      telefon?: string | null;
    } | null;
  }
): Promise<void> {
  const masterKey = process.env.SNAJP_MASTER_API_KEY;
  if (!masterKey || (!uppgifter.orgnr && !uppgifter.kontakt)) {
    return;
  }

  try {
    const listSvar = await proxyWithApiKey("/api/admin/tenants", { method: "GET" }, masterKey);
    if (!listSvar.ok) {
      throw new Error(`GET /api/admin/tenants svarade ${listSvar.status}`);
    }
    const kropp = await readJsonBody<{ tenants?: { id: string; slug: string | null }[] }>(listSvar);
    const tenant = kropp?.tenants?.find((rad) => rad.slug === slug);
    if (!tenant) {
      throw new Error(`tenanten "${slug}" fanns inte i adminlistan ännu`);
    }

    if (uppgifter.orgnr) {
      const svar = await proxyWithApiKey(
        `/api/admin/tenants/${tenant.id}/kunddata`,
        { method: "PUT", body: JSON.stringify({ orgnr: uppgifter.orgnr }) },
        masterKey
      );
      if (!svar.ok) {
        console.error(`[onboarding] kunddata för ${slug}: backenden svarade ${svar.status}`);
      }
    }

    if (uppgifter.kontakt?.namn) {
      const svar = await proxyWithApiKey(
        `/api/admin/tenants/${tenant.id}/kontakter`,
        {
          method: "POST",
          body: JSON.stringify({
            namn: uppgifter.kontakt.namn,
            roll: uppgifter.kontakt.roll || null,
            mejl: uppgifter.kontakt.mejl || null,
            telefon: uppgifter.kontakt.telefon || null
          })
        },
        masterKey
      );
      if (!svar.ok) {
        console.error(`[onboarding] kontaktperson för ${slug}: backenden svarade ${svar.status}`);
      }
    }
  } catch (fel) {
    console.error("[onboarding] kundregistret kunde inte fyllas:", fel);
  }
}
