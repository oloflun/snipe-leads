import { NextResponse } from "next/server";
import { getPlatformAdmin } from "@/lib/auth/admin";
import { sqlAsUser } from "@/lib/db";
import { DEMO_ARBETSYTA, DEMO_TENANT_SLUG } from "@/lib/vy";

/**
 * Kunderna "Byt kund" får erbjuda — de som faktiskt GÅR att öppna.
 *
 * ## Varför den här routen och inte /api/admin/tenants
 *
 * Växeln listade tidigare backendens alla tenants. Den listan innehåller rader
 * som inte har någon arbetsyta i Next-appens databas: `public-demo`, gamla
 * testtenants, och demokontot. Klickade man på en av dem svarade
 * `requireSnajpTenant()` 409 — "Ingen backend-nyckel för …" — på varje yta i
 * kundens profil. Uppmätt i drift, och det är felet den här filen stänger.
 *
 * `tenants_for_admin()` (migration 042) svarar i stället med de arbetsytor som
 * bär en slug, alltså exakt de kunder som har en tenant att öppna. Funktionen
 * gör om `platform_admins`-kontrollen i databasen — samma villkor som
 * `tenant_api_key_for_admin()`, med flit: en admin som kan hämta nyckeln men
 * inte se listan hade fått den ur den andra listan ändå, och två grindar med
 * olika villkor är i praktiken den svagaste av dem.
 *
 * Demokontot läggs till som en egen rad. Det HAR ingen arbetsyta och kan därför
 * inte komma ur funktionen, men det går att öppna: nyckeln är demonyckeln, och
 * `requireSnajpTenant()` tar den grenen först av alla.
 */

export const runtime = "nodejs";

const NOT_FOUND = NextResponse.json({ error: "Hittades inte." }, { status: 404 });

type Rad = { slug: string | null; name: string | null };

export async function GET() {
  const admin = await getPlatformAdmin();
  if (!admin) {
    // 404 och inte 403, av samma skäl som app/api/admin/[...path]: ett 403
    // bekräftar att ytan finns och vem den är till för.
    return NOT_FOUND;
  }

  let rader: Rad[] = [];
  try {
    rader = await sqlAsUser<Rad>(
      admin.userId,
      "select slug, name from public.tenants_for_admin()"
    );
  } catch (error) {
    console.error("[admin/kunder] tenants_for_admin:", (error as Error).message);
    return NextResponse.json(
      { error: "Kundlistan gick inte att hämta." },
      { status: 503 }
    );
  }

  const tenants = rader
    .filter((rad): rad is { slug: string; name: string } => Boolean(rad.slug && rad.name))
    .map((rad) => ({ slug: rad.slug, name: rad.name }));

  return NextResponse.json({
    tenants: [...tenants, { slug: DEMO_TENANT_SLUG, name: DEMO_ARBETSYTA }]
  });
}
