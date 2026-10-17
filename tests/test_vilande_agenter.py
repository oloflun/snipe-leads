"""Vilande agenter: syns mörklagda för kunden, går inte att öppna, admin passerar.

Sebbe 2026-10-17: Kvittohanteraren säljs inte just nu. Kunden ska se att det
står "Kvitton" i menyn men inte kunna klicka in, och plattformsadmin ska
använda den som vanligt. Fyra ställen måste säga samma sak — listan i
lib/routes.ts, kundens produkter i resolveDashboardState, railen i AppShell
och serverspärren i WorkspaceSection — plus demon, som är kundens skyltfönster.
Ett ställe som glöms är antingen en död menypost eller en öppen bakdörr.

Testet läser filerna som text, som test_bokforing_atkomst.py.
"""

from __future__ import annotations

import re
from pathlib import Path

ROT = Path(__file__).resolve().parents[1]


def _las(rel: str) -> str:
    return (ROT / rel).read_text(encoding="utf-8")


def test_kvitton_ar_vilande():
    routes = _las("lib/routes.ts")
    assert re.search(r'VILANDE_PRODUKTER:\s*readonly ProductKey\[\]\s*=\s*\["bookkeeping"\]', routes)
    # routesForProducts släpper bara igenom vilande poster för admin.
    assert "(!arVilande(route.product) || isAdmin)" in routes


def test_kundens_produkter_filtreras_men_inte_adminens():
    kod = _las("lib/data/dashboard.ts")
    assert "arAdmin ? products : products.filter((p) => !arVilande(p))" in kod
    assert "products: synliga" in kod
    assert "ALL_PRODUCTS.filter((p) => !arVilande(p))" in kod  # ANONYMOUS


def test_railen_ritar_vilande_utan_lank():
    rail = _las("components/shell/Rail.tsx")
    vilande_gren = rail[rail.index("if (vilande) {") : rail.index("<Link", rail.index("if (vilande) {"))]
    assert "<span" in vilande_gren and 'aria-disabled="true"' in vilande_gren
    assert "href" not in vilande_gren and "onClick" not in vilande_gren

    shell = _las("components/AppShell.tsx")
    assert "!arVilande(route.product)" in shell  # inte även som klickbar upsell
    assert "vilande: true" in shell


def test_serverspärren_skickar_kunden_till_oversikten():
    kod = _las("components/dashboard/WorkspaceSection.tsx")
    assert re.search(r"if \(arVilande\(product\) && !isPlatformAdmin\) \{\s*redirect\(base\);", kod)
    # Spärren står FÖRE entitlement-grenen, annars landar kunden i upsell-vyn.
    assert kod.index("arVilande(product)") < kod.index("if (!products.includes(product))")


def test_demon_visar_kvitton_morklagt():
    sektioner = _las("lib/demo/sektioner.ts")
    assert re.search(r'slug: "kvitton".*vilande: true', sektioner)
    sida = _las("app/demo/[[...slug]]/page.tsx")
    assert 'products: ["leads", "support"] as const' in sida
    assert "<KvittoDemoYta" not in sida
