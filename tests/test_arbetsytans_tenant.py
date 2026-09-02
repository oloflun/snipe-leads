"""Arbetsytan ska få en backend-tenant automatiskt — och växeln bara erbjuda
kunder som går att öppna.

Tre kopplingar som saknar kompilatorstöd och bara syns i drift när de brister.
Alla tre orsakade samma symptom i produktion 2026-09-02: `requireSnajpTenant()`
svarade 409, och det syntes som streckade siffror i översikten, "Kunde inte
hämta röstdokumentet" på `/settings/soul` och ett meddelande om databaskolumner
på `/settings/leads`.

1. **Slugmönstren.** `link_test_tenant` (migration 040) och
   `link_workspace_tenant` (migration 061) accepterar var sitt mönster.
   Genererar TypeScript-sidan en slug som inte matchar avvisas kopplingen TYST
   — funktionerna returnerar `false` utan att säga vilket mönster som gällde,
   med flit. Arbetsytan står då kvar utan slug och kunden möter 409.

2. **Kundlistan.** "Byt kund" listade backendens ALLA tenants, inklusive rader
   utan arbetsyta (`public-demo`, gamla testtenants). Att klicka på en sådan gav
   409 på varje yta i kundens profil.

3. **Demokontot.** `nordlys-handel` har ingen arbetsyta och ingen
   `SNAJP_KEY_*`-variabel — dess nyckel ÄR demonyckeln. Utan den grenen i
   kundbesöket är demokontot oöppningsbart från växeln.

Testerna läser filerna som text i stället för att köra TypeScript. Det räcker
för frågorna som ställs, och de kan köras i samma svit som resten.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TESTTENANT = ROOT / "lib" / "snajp" / "testtenant.ts"
TENANT = ROOT / "lib" / "snajp" / "tenant.ts"
BYTKUND = ROOT / "components" / "admin" / "BytKund.tsx"
MIGRATION_040 = ROOT / "supabase" / "migrations" / "040_testkund_egen_tenant.sql"
MIGRATION_061 = ROOT / "supabase" / "migrations" / "061_arbetsytans_egna_tenant.sql"

#: Ett workspace-id i den form appen får det. Sluggen härleds ur det.
WORKSPACE_ID = "a1aa612a-3f4d-4b7e-9c11-0d2e5f6a7b8c"


def _prefix_ur_ts(funktion: str) -> str:
    """Prefixet `tenantSlug("<prefix>", …)` anropas med i den namngivna funktionen."""
    kalla = TESTTENANT.read_text(encoding="utf-8")
    kropp = kalla.split(f"export function {funktion}")[1].split("}")[0]
    traff = re.search(r'tenantSlug\("([^"]+)"', kropp)
    assert traff, f"{funktion} anropar inte tenantSlug med ett literalt prefix längre."
    return traff.group(1)


def _monster_ur_sql(path: Path, funktion: str) -> str:
    kalla = path.read_text(encoding="utf-8")
    kropp = kalla.split(f"function public.{funktion}")[1]
    traff = re.search(r"!~ '(\^[^']+)'", kropp)
    assert traff, f"{funktion} kontrollerar inte längre sluggen mot ett mönster."
    return traff.group(1)


def _slug(prefix: str) -> str:
    """Spegel av `tenantSlug()` i lib/snajp/testtenant.ts."""
    rent = re.sub(r"[^a-z0-9]", "", WORKSPACE_ID.lower())
    return f"{prefix}{rent[:8]}"


def test_testarbetsytans_slug_godkanns_av_migration_040():
    monster = _monster_ur_sql(MIGRATION_040, "link_test_tenant")
    slug = _slug(_prefix_ur_ts("testtenantSlug"))
    assert re.match(monster, slug), (
        f"{slug!r} matchar inte {monster!r} i link_test_tenant. Kopplingen avvisas "
        "tyst och testarbetsytan står kvar utan slug."
    )


def test_kundens_slug_godkanns_av_migration_061():
    monster = _monster_ur_sql(MIGRATION_061, "link_workspace_tenant")
    slug = _slug(_prefix_ur_ts("kundtenantSlug"))
    assert re.match(monster, slug), (
        f"{slug!r} matchar inte {monster!r} i link_workspace_tenant. En ny kund "
        "får då ingen tenant och möter 409 på varje inloggad yta."
    )


def test_monstren_utesluter_varandra():
    """En kundslug får aldrig kunna kopplas som testarbetsyta, eller tvärtom.

    `link_test_tenant` sätter `is_demo = true`, vilket sänker löptaket och märker
    arbetsytan som en demo. En riktig kund som halkade in där hade fått en strypt
    körning utan att någon bestämt det."""
    test_monster = _monster_ur_sql(MIGRATION_040, "link_test_tenant")
    kund_monster = _monster_ur_sql(MIGRATION_061, "link_workspace_tenant")
    testslug = _slug(_prefix_ur_ts("testtenantSlug"))
    kundslug = _slug(_prefix_ur_ts("kundtenantSlug"))

    assert not re.match(kund_monster, testslug), (
        f"{testslug!r} godkänns av link_workspace_tenant — mönstren överlappar."
    )
    assert not re.match(test_monster, kundslug), (
        f"{kundslug!r} godkänns av link_test_tenant, som sätter is_demo. "
        "En riktig kund hade kopplats som demo."
    )


def test_byt_kund_listar_arbetsytor_inte_backendens_tenants():
    kalla = BYTKUND.read_text(encoding="utf-8")
    assert '"/api/admin/kunder"' in kalla, (
        "BytKund hämtar inte /api/admin/kunder. Listan måste komma från "
        "tenants_for_admin(), alltså arbetsytorna."
    )
    assert '"/api/admin/tenants"' not in kalla, (
        "BytKund hämtar backendens tenant-lista igen. Den innehåller rader utan "
        "arbetsyta (public-demo, gamla testtenants), och att klicka på en sådan "
        "ger 409 på varje yta i kundens profil."
    )


def test_kundbesok_hos_demokontot_anvander_demonyckeln():
    kalla = TENANT.read_text(encoding="utf-8")
    kund_gren = kalla.split('if (lage.vy === "kund")')[1].split('if (lage.vy === "demo")')[0]
    assert "DEMO_TENANT_SLUG" in kund_gren, (
        "Kundbesöket saknar demogrenen. `nordlys-handel` har varken en rad i "
        "workspace_tenant_keys eller en SNAJP_KEY_-variabel, så växeln in i "
        "demokontot svarar 409 utan den."
    )
    assert "SNAJP_DEMO_API_KEY" in kund_gren, (
        "Demogrenen i kundbesöket läser inte demonyckeln."
    )
