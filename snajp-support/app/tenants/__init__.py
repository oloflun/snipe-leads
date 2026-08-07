"""Kundspecifika kunskapsbaser.

En kund = en modul med KB_ARTICLES. Systemprompten forkas medvetet inte per
kund — företagsfakta injiceras i kontexten i stället, annars hade varje ny kund
inneburit ännu en prompt att hålla i synk.
"""

from .livrustning_kb import KB_ARTICLES as LIVRUSTNING_KB

# Namnet måste stå här och inte härledas ur sluggen: create_tenant är en upsert
# som skriver om name, så ett gissat namn ("Livrustning") skulle tyst döpa om
# kunden i databasen.
TENANTS: dict[str, dict] = {
    "livrustning": {"name": "Livrustning AB", "articles": LIVRUSTNING_KB},
}


def kb_for_tenant(slug: str) -> list[dict] | None:
    tenant = TENANTS.get(slug)
    return tenant["articles"] if tenant else None


def name_for_tenant(slug: str) -> str | None:
    tenant = TENANTS.get(slug)
    return tenant["name"] if tenant else None
