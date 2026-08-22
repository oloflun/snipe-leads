"""Kundspecifika kunskapsbaser.

En kund = en modul med KB_ARTICLES. Systemprompten forkas medvetet inte per
kund — företagsfakta injiceras i kontexten i stället, annars hade varje ny kund
inneburit ännu en prompt att hålla i synk.
"""

from ..kb_articles import KB_ARTICLES as NORDLYS_KB
from .livrustning_kb import KB_ARTICLES as LIVRUSTNING_KB
from .snajp_kb import KB_ARTICLES as SNAJP_KB

# Namnet måste stå här och inte härledas ur sluggen: create_tenant är en upsert
# som skriver om name, så ett gissat namn ("Livrustning") skulle tyst döpa om
# kunden i databasen.
TENANTS: dict[str, dict] = {
    "livrustning": {"name": "Livrustning AB", "articles": LIVRUSTNING_KB},
    # Vår egen arbetsyta. Namnet måste matcha ss_tenants.name exakt — se
    # kommentaren ovan om att create_tenant är en upsert som skriver om name.
    "snajp": {"name": "Snajp", "articles": SNAJP_KB},
    # Demokontot. Egen fil vore en tredje kopia av samma lista: artiklarna bor
    # redan i app/kb_articles.py, där `ensure_default_kb` läser dem vid start.
    # Raden här gör bara demokontot nåbart för `python -m app.scripts.seed_kb
    # nordlys-handel` som vilken kund som helst — namnet MÅSTE stämma med
    # ss_tenants.name (migration 003), eftersom create_tenant är en upsert.
    "nordlys-handel": {"name": "Nordlys Handel", "articles": NORDLYS_KB},
}


def kb_for_tenant(slug: str) -> list[dict] | None:
    tenant = TENANTS.get(slug)
    return tenant["articles"] if tenant else None


def name_for_tenant(slug: str) -> str | None:
    tenant = TENANTS.get(slug)
    return tenant["name"] if tenant else None
