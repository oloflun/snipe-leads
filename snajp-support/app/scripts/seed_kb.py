"""Seedar kunskapsbasen (+ demo-API-nyckel) i Postgres.

Körs bara i Postgres-läget (kräver DATABASE_URL). Embeddings beräknas endast
om en riktig OpenAI-nyckel finns; annars lämnas kolumnen NULL och tjänsten
använder svensk fulltextsökning tills embeddings fyllts på.

Kör:  python -m app.scripts.seed_kb

`ensure_default_kb` anropas dessutom automatiskt vid uppstart (app/main.py) så
en färsk databas aldrig står med tom kunskapsbas — utan artiklar tvingar
grundningsregeln eskalering av varje ärende.
"""

import asyncio
import logging

from ..config import DEFAULT_TENANT_ID, DEFAULT_TENANT_NAME, get_settings
from ..kb_articles import KB_ARTICLES

logger = logging.getLogger("snajp-support.seed")


async def ensure_default_kb(storage, *, embeddings: list[list[float] | None] | None = None) -> int:
    """Seedar default-tenantens KB om den är tom. Returnerar antal nya artiklar.

    Utan `embeddings` seedas ren text (snabbt — lämpligt vid uppstart). Vektorerna
    kan fyllas på i efterhand genom att köra modulen som skript med en giltig
    EMBEDDING_API_KEY.
    """
    existing = await storage.list_kb(DEFAULT_TENANT_ID)
    if existing:
        return 0
    vectors = embeddings or [None] * len(KB_ARTICLES)
    for article, embedding in zip(KB_ARTICLES, vectors):
        await storage.add_kb_article(
            DEFAULT_TENANT_ID,
            title=article["title"],
            content=article["content"],
            category=article["category"],
            embedding=embedding,
        )
    return len(KB_ARTICLES)


async def seed_tenant(storage, tenant_slug: str, *, embeddings=None) -> int:
    """Seedar en kunds kunskapsbas. Returnerar antal nya artiklar.

    Idempotent: en tenant som redan har artiklar lämnas orörd, så skriptet kan
    köras om utan att dubblera kunskapsbasen.
    """
    from ..tenants import kb_for_tenant, name_for_tenant

    articles = kb_for_tenant(tenant_slug)
    if articles is None:
        raise SystemExit(f"Okänd tenant: {tenant_slug}")

    # create_tenant är en upsert (on conflict do update ... returning *), så den
    # både hämtar en befintlig tenant och skapar en som saknas. Ingen extra
    # lagringsmetod behövs.
    tenant = await storage.create_tenant(
        slug=tenant_slug, name=name_for_tenant(tenant_slug) or tenant_slug
    )

    if await storage.list_kb(tenant["id"]):
        return 0

    vectors = embeddings or [None] * len(articles)
    for article, embedding in zip(articles, vectors):
        await storage.add_kb_article(
            tenant["id"],
            title=article["title"],
            content=article["content"],
            category=article["category"],
            embedding=embedding,
        )
    return len(articles)


async def main() -> None:
    import sys

    settings = get_settings()
    if not settings.database_url:
        print("DATABASE_URL saknas — in-memory-läget seedar sig självt. Inget att göra.")
        return

    from ..storage.postgres import PostgresStorage

    # Utan argument seedas demo-tenanten som förut; med argument seedas en kund.
    tenant_slug = sys.argv[1] if len(sys.argv) > 1 else None

    storage = await PostgresStorage.connect(settings.database_url)
    try:
        if tenant_slug:
            added = await seed_tenant(storage, tenant_slug)
            print(
                f"Seedade {added} artiklar till {tenant_slug}."
                if added
                else f"{tenant_slug} har redan en kunskapsbas — hoppar över."
            )
            return

        embeddings: list[list[float] | None] | None = None
        if not settings.is_simulation():
            from ..agent.embeddings import embed_text

            print("Beräknar embeddings ...")
            embeddings = [await embed_text(f"{a['title']}\n{a['content']}") for a in KB_ARTICLES]
            if embeddings and embeddings[0] is None:
                print("Ingen EMBEDDING_API_KEY — seedar utan vektorer (fulltextsökning används).")

        added = await ensure_default_kb(storage, embeddings=embeddings)
        if added:
            print(f"Seedade {added} artiklar till default-tenanten.")
        else:
            print("Default-tenantens kunskapsbas är redan seedad — hoppar över.")

        await storage.create_api_key(
            DEFAULT_TENANT_ID, tenant_name=DEFAULT_TENANT_NAME, raw_key=settings.snajp_demo_api_key
        )
        print("Demo-API-nyckel registrerad.")
    finally:
        await storage.close()


if __name__ == "__main__":
    asyncio.run(main())
